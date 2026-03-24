/**
 * EPCAL - E-Paper Calendar
 *
 * Battery-powered IoT calendar display using:
 * - ESP32 microcontroller
 * - Waveshare 12.48" tri-color e-paper display
 * - WiFiManager for easy WiFi setup
 * - Server-rendered calendar bitmap with ETag caching
 */

#include <WiFiManager.h>
#include <time.h>
#include <esp_task_wdt.h>
#include "config.h"
#include "http_client.h"
#include "display.h"

// Watchdog timeout in seconds - if the ESP32 hangs longer than this, it reboots
#define WDT_TIMEOUT 120

// Waveshare display version (1 or 2, depending on hardware revision)
int Version = 1;

// Deep sleep duration in microseconds
#define uS_TO_S_FACTOR 1000000ULL

// Default server URL (change this to your server's IP)
#define DEFAULT_SERVER_URL "http://192.168.1.244:4000"

// Setup button GPIO - hold during boot to enter configuration mode
// GPIO0 is the BOOT button on most ESP32 dev boards
#define SETUP_BUTTON_PIN 0
#define BUTTON_HOLD_TIME_MS 2000  // Hold for 2 seconds to enter setup

// WiFiManager custom parameters
WiFiManagerParameter custom_server_url("server", "Calendar Server URL", DEFAULT_SERVER_URL, 128);
char refresh_interval_str[8] = "15";  // Default 15 minutes
WiFiManagerParameter custom_refresh_interval("refresh", "Refresh Interval (minutes)", refresh_interval_str, 8);

// Global state
Config config;
CacheState cache;
uint8_t* chunk_buffer = NULL;

// Boot count for debugging
RTC_DATA_ATTR int bootCount = 0;

// Forward declarations
void saveParamsCallback();
void handleConnectionFailure();
void updateCalendar();
void enterDeepSleep(uint32_t seconds);
bool isSetupButtonHeld();

void setup() {
  Serial.begin(115200);
  delay(100);

  // Reconfigure the existing watchdog timer (Arduino framework already inits it)
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };
  esp_task_wdt_reconfigure(&wdt_config);
  esp_task_wdt_add(NULL);

  bootCount++;
  Serial.printf("\n\n=== EPCAL Boot #%d ===\n", bootCount);

  // Initialize setup button pin
  pinMode(SETUP_BUTTON_PIN, INPUT_PULLUP);

  // Initialize config system
  config_init();

  // Load saved configuration
  bool hasConfig = config_load(&config);
  cache_load(&cache);

  Serial.printf("Config loaded: %s\n", hasConfig ? "yes" : "no");
  if (hasConfig) {
    Serial.printf("Server URL: %s\n", config.server_url);
    Serial.printf("Refresh interval: %d seconds\n", config.refresh_interval);
  }
  Serial.printf("Cached ETag: %s\n", cache.etag[0] ? cache.etag : "(none)");

  // Check if setup button is held - force config portal
  bool forceSetup = isSetupButtonHeld();
  if (forceSetup) {
    Serial.println("Setup button held - forcing configuration mode");
  }

  // Initialize WiFiManager
  WiFiManager wm;

  // Set timeout for config portal (5 minutes, 0 = no timeout)
  wm.setConfigPortalTimeout(300);

  // Captive portal improvements
  wm.setCaptivePortalEnable(true);       // Enable captive portal redirection
  wm.setShowInfoUpdate(false);           // Hide update button (not needed)
  wm.setShowInfoErase(true);             // Show erase button for factory reset
  wm.setConfigPortalBlocking(true);      // Block until configured
  wm.setConnectRetries(5);               // Retry connection 5 times
  wm.setConnectTimeout(10);              // 10 second timeout per attempt

  // Set static IP for AP mode - helps with captive portal detection
  IPAddress apIP(192, 168, 4, 1);
  IPAddress apGateway(192, 168, 4, 1);
  IPAddress apSubnet(255, 255, 255, 0);
  wm.setAPStaticIPConfig(apIP, apGateway, apSubnet);

  // WiFiManager class "invert" can help with some captive portal issues
  wm.setClass("invert");

  // Pre-populate custom parameters with current values
  if (hasConfig && strlen(config.server_url) > 0) {
    custom_server_url.setValue(config.server_url, 128);
  }
  // Convert refresh interval from seconds to minutes for display
  uint32_t refresh_minutes = hasConfig ? (config.refresh_interval / 60) : 15;
  snprintf(refresh_interval_str, sizeof(refresh_interval_str), "%lu", (unsigned long)refresh_minutes);
  custom_refresh_interval.setValue(refresh_interval_str, 8);

  // Add custom parameters
  wm.addParameter(&custom_server_url);
  wm.addParameter(&custom_refresh_interval);

  // Set callback for when config is saved
  wm.setSaveParamsCallback(saveParamsCallback);

  // AP name and config URL for QR codes
  const char* apName = "EPCAL-Setup";
  const char* configUrl = "http://192.168.4.1";

  // Suspend watchdog during WiFi connect (can block for minutes)
  esp_task_wdt_delete(NULL);

  // Try to connect, or start config portal
  bool connected = false;
  if (forceSetup) {
    // User requested setup mode - show QR codes for easy setup
    display_show_setup_screen(apName, configUrl);
    connected = wm.startConfigPortal(apName);
  } else if (hasConfig || wm.getWiFiIsSaved()) {
    // We have saved WiFi, try to auto-connect
    Serial.println("Attempting WiFi connection...");
    wm.setEnableConfigPortal(false);  // Don't auto-start portal on failure
    connected = wm.autoConnect(apName);
    if (!connected) {
      // WiFi failed - show setup screen and start portal for reconfiguration
      Serial.println("WiFi connection failed, starting setup portal...");
      display_show_setup_screen(apName, configUrl);
      connected = wm.startConfigPortal(apName);
      if (connected) {
        // Clear ETag so we force a display refresh after reconfiguration
        cache_clear();
        Serial.println("Cache cleared after WiFi reconfiguration");
      }
    }
  } else {
    // No config, show QR codes on display and start portal
    Serial.println("No config found, starting setup portal...");
    display_show_setup_screen(apName, configUrl);
    connected = wm.startConfigPortal(apName);
  }

  // Re-enable watchdog now that WiFi is done
  esp_task_wdt_add(NULL);

  if (!connected) {
    Serial.println("WiFi connection failed!");
    handleConnectionFailure();
    return;
  }

  esp_task_wdt_reset();
  Serial.println("WiFi connected!");
  Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());

  // Sync time via NTP (needed for cache timestamps and clock display)
  // Timezone: Eastern Time (Montreal/Toronto) - adjust as needed
  // Format: "STD offset DST, start, end"
  configTzTime("EST5EDT,M3.2.0,M11.1.0", "pool.ntp.org", "time.nist.gov");

  // Wait for time to sync
  Serial.print("Waiting for NTP time sync");
  time_t now = time(NULL);
  int retries = 0;
  while (now < 1000000000 && retries < 20) {
    delay(500);
    Serial.print(".");
    now = time(NULL);
    retries++;
  }
  Serial.println();

  struct tm* timeinfo = localtime(&now);
  Serial.printf("Current time: %02d:%02d:%02d\n", timeinfo->tm_hour, timeinfo->tm_min, timeinfo->tm_sec);

  // Use default server URL if none configured
  if (strlen(config.server_url) == 0) {
    Serial.println("No server URL configured, using default...");
    strncpy(config.server_url, DEFAULT_SERVER_URL, sizeof(config.server_url) - 1);
  }

  // Check for calendar updates
  updateCalendar();

  // Disconnect WiFi to save power
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);

  // Enter deep sleep
  enterDeepSleep(config.refresh_interval);
}

void loop() {
  // Never reached - we use deep sleep
}

/**
 * Callback when WiFiManager saves parameters
 */
void saveParamsCallback() {
  Serial.println("WiFiManager params saved");

  // Get server URL from custom parameter
  const char* url = custom_server_url.getValue();
  if (url && strlen(url) > 0) {
    strncpy(config.server_url, url, sizeof(config.server_url) - 1);
    config.server_url[sizeof(config.server_url) - 1] = '\0';
    Serial.printf("Server URL: %s\n", config.server_url);
  } else {
    // Use default if empty
    strncpy(config.server_url, DEFAULT_SERVER_URL, sizeof(config.server_url) - 1);
    Serial.printf("Using default server URL: %s\n", DEFAULT_SERVER_URL);
  }

  // Get refresh interval from custom parameter (in minutes, convert to seconds)
  const char* refresh_str = custom_refresh_interval.getValue();
  if (refresh_str && strlen(refresh_str) > 0) {
    int minutes = atoi(refresh_str);
    if (minutes >= 1 && minutes <= 1440) {  // 1 minute to 24 hours
      config.refresh_interval = minutes * 60;
      Serial.printf("Refresh interval: %d minutes (%d seconds)\n", minutes, config.refresh_interval);
    } else {
      config.refresh_interval = DEFAULT_REFRESH_INTERVAL;
      Serial.printf("Invalid refresh interval, using default: %d seconds\n", DEFAULT_REFRESH_INTERVAL);
    }
  } else {
    config.refresh_interval = DEFAULT_REFRESH_INTERVAL;
  }

  config.configured = true;

  // Save to NVS
  config_save(&config);

  // Clear cached ETag so we refresh on next check
  cache_clear();
  Serial.println("Cache cleared - will refresh display on next check");
}

/**
 * Handle WiFi connection failure
 */
void handleConnectionFailure() {
  display_show_error("WiFi connection failed");
  display_sleep();

  // Sleep for 5 minutes and retry
  enterDeepSleep(300);
}

/**
 * Check server for updates and refresh display if needed
 */
void updateCalendar() {
  Serial.println("Checking for calendar updates...");
  Serial.printf("Server: %s\n", config.server_url);

  // Check if calendar has changed using ETag
  FetchResponse checkResponse = http_check_calendar(config.server_url, cache.etag);

  if (checkResponse.result == FETCH_NOT_MODIFIED) {
    Serial.println("Calendar unchanged (304), skipping display refresh");
    cache.last_check_epoch = time(NULL);
    cache_save(&cache);
    return;
  }

  if (checkResponse.result == FETCH_ERROR) {
    Serial.printf("Check failed with HTTP %d\n", checkResponse.http_code);
    char errMsg[64];
    snprintf(errMsg, sizeof(errMsg), "Server error (HTTP %d)", checkResponse.http_code);
    display_show_error(errMsg);
    display_sleep();
    return;
  }

  esp_task_wdt_reset();  // Pet watchdog after successful check

  // Calendar has changed, download all chunks
  Serial.println("Calendar changed, downloading...");

  // Allocate buffer for chunks
  chunk_buffer = (uint8_t*)malloc(CHUNK_BUFFER_SIZE);
  if (!chunk_buffer) {
    Serial.println("Failed to allocate chunk buffer!");
    display_show_error("Memory allocation failed");
    display_sleep();
    return;
  }

  // Initialize display
  display_init();

  bool success = true;
  const char* failedEndpoint = NULL;

  // Download and send black layer chunk 1
  if (success) {
    FetchResponse resp = http_fetch_chunk(config.server_url, ENDPOINT_BLACK1, "", chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_black1(chunk_buffer);
      // Store the new ETag
      if (resp.new_etag[0] != '\0') {
        strncpy(cache.etag, resp.new_etag, sizeof(cache.etag) - 1);
      }
    } else {
      success = false;
      failedEndpoint = ENDPOINT_BLACK1;
    }
  }

  esp_task_wdt_reset();  // Pet watchdog between downloads

  // Download and send black layer chunk 2
  if (success) {
    FetchResponse resp = http_fetch_chunk(config.server_url, ENDPOINT_BLACK2, "", chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_black2(chunk_buffer);
    } else {
      success = false;
      failedEndpoint = ENDPOINT_BLACK2;
    }
  }

  esp_task_wdt_reset();

  // Download and send red layer chunk 1
  if (success) {
    FetchResponse resp = http_fetch_chunk(config.server_url, ENDPOINT_RED1, "", chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_red1(chunk_buffer);
    } else {
      success = false;
      failedEndpoint = ENDPOINT_RED1;
    }
  }

  esp_task_wdt_reset();

  // Download and send red layer chunk 2
  if (success) {
    FetchResponse resp = http_fetch_chunk(config.server_url, ENDPOINT_RED2, "", chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_red2(chunk_buffer);
    } else {
      success = false;
      failedEndpoint = ENDPOINT_RED2;
    }
  }

  // Free buffer
  free(chunk_buffer);
  chunk_buffer = NULL;

  if (success) {
    // Refresh the display
    Serial.println("Refreshing display...");
    display_refresh();

    // Update cache
    cache.display_valid = true;
    cache.last_check_epoch = time(NULL);
    cache_save(&cache);

    Serial.println("Display updated successfully!");
  } else {
    Serial.printf("Download failed for %s\n", failedEndpoint);
    char errMsg[64];
    snprintf(errMsg, sizeof(errMsg), "Download failed: %s", failedEndpoint);
    display_show_error(errMsg);
  }

  // Put display to sleep
  display_sleep();
}

/**
 * Enter deep sleep for specified duration
 */
void enterDeepSleep(uint32_t seconds) {
  Serial.printf("Entering deep sleep for %d seconds...\n", seconds);
  Serial.flush();

  // Disable watchdog before sleep
  esp_task_wdt_delete(NULL);

  esp_sleep_enable_timer_wakeup(seconds * uS_TO_S_FACTOR);
  esp_deep_sleep_start();
}

/**
 * Check if setup button is being held
 * Returns true if button is held LOW for BUTTON_HOLD_TIME_MS
 */
bool isSetupButtonHeld() {
  // Button uses internal pull-up, so pressed = LOW
  if (digitalRead(SETUP_BUTTON_PIN) == HIGH) {
    return false;  // Not pressed at all
  }

  Serial.println("Setup button pressed, checking hold duration...");

  // Wait to see if button is held
  unsigned long startTime = millis();
  while (millis() - startTime < BUTTON_HOLD_TIME_MS) {
    if (digitalRead(SETUP_BUTTON_PIN) == HIGH) {
      Serial.println("Button released early");
      return false;  // Released before hold time
    }
    delay(50);  // Check every 50ms
  }

  Serial.println("Button held - entering setup mode");
  return true;
}
