/**
 * E-Ink Calendar
 *
 * Battery-powered IoT calendar display using:
 * - ESP32 microcontroller
 * - Waveshare 12.48" tri-color e-paper display
 * - WiFiManager for easy WiFi setup
 * - Home Assistant native discovery via announce API
 * - Server-rendered calendar bitmap with ETag caching
 */

#include <WiFiManager.h>
#include <ESPmDNS.h>
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

// Setup button GPIO - hold during boot to enter configuration mode
// GPIO0 is the BOOT button on most ESP32 dev boards
#define SETUP_BUTTON_PIN 0
#define BUTTON_HOLD_TIME_MS 2000  // Hold for 2 seconds to enter setup

// Announce polling interval when waiting for HA configuration (ms)
#define ANNOUNCE_POLL_INTERVAL 30000

// Device info
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_NAME_PREFIX "EinkCal"

// WiFiManager custom parameters
char ha_url_override[128] = "";  // Optional manual HA URL override
WiFiManagerParameter custom_ha_url("ha_url", "HA URL Override (optional)", "", 128);
char refresh_interval_str[8] = "15";  // Default 15 minutes
WiFiManagerParameter custom_refresh_interval("refresh", "Refresh Interval (minutes)", refresh_interval_str, 8);

// Global state
Config config;
CacheState cache;
BitmapEndpoints endpoints;
uint8_t* chunk_buffer = NULL;

// Boot count for debugging
RTC_DATA_ATTR int bootCount = 0;

// Forward declarations
void saveParamsCallback();
void handleConnectionFailure();
void updateCalendar();
void enterDeepSleep(uint32_t seconds);
bool isSetupButtonHeld();
bool discoverHomeAssistant();
bool announceAndConfigure();
String getDeviceMac();
String getDeviceName();

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
  Serial.printf("\n\n=== E-Ink Calendar Boot #%d ===\n", bootCount);
  Serial.printf("MAC: %s\n", getDeviceMac().c_str());

  // Initialize setup button pin
  pinMode(SETUP_BUTTON_PIN, INPUT_PULLUP);

  // Initialize config system
  config_init();

  // Load saved configuration
  bool hasConfig = config_load(&config);
  cache_load(&cache);
  bool hasEndpoints = endpoints_load(&endpoints);

  Serial.printf("Config loaded: %s\n", hasConfig ? "yes" : "no");
  if (hasConfig) {
    Serial.printf("HA URL: %s\n", config.ha_url);
    Serial.printf("Entry ID: %s\n", config.entry_id);
    Serial.printf("Refresh interval: %d seconds\n", config.refresh_interval);
    Serial.printf("Discovered: %s\n", config.discovered ? "yes" : "no");
  }

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
  wm.setCaptivePortalEnable(true);
  wm.setShowInfoUpdate(false);
  wm.setShowInfoErase(true);
  wm.setConfigPortalBlocking(true);
  wm.setConnectRetries(5);
  wm.setConnectTimeout(10);

  // Set static IP for AP mode
  IPAddress apIP(192, 168, 4, 1);
  IPAddress apGateway(192, 168, 4, 1);
  IPAddress apSubnet(255, 255, 255, 0);
  wm.setAPStaticIPConfig(apIP, apGateway, apSubnet);

  wm.setClass("invert");

  // Pre-populate custom parameters with current values
  if (hasConfig && strlen(config.ha_url) > 0) {
    custom_ha_url.setValue(config.ha_url, 128);
  }
  uint32_t refresh_minutes = hasConfig ? (config.refresh_interval / 60) : 15;
  snprintf(refresh_interval_str, sizeof(refresh_interval_str), "%lu", (unsigned long)refresh_minutes);
  custom_refresh_interval.setValue(refresh_interval_str, 8);

  // Add custom parameters
  wm.addParameter(&custom_ha_url);
  wm.addParameter(&custom_refresh_interval);

  // Set callback for when config is saved
  wm.setSaveParamsCallback(saveParamsCallback);

  // AP name and config URL for QR codes
  const char* apName = "EinkCal-Setup";
  const char* configUrl = "http://192.168.4.1";

  // Suspend watchdog during WiFi connect (can block for minutes)
  esp_task_wdt_delete(NULL);

  // Try to connect, or start config portal
  bool connected = false;
  if (forceSetup) {
    display_show_setup_screen(apName, configUrl);
    connected = wm.startConfigPortal(apName);
  } else if (hasConfig || wm.getWiFiIsSaved()) {
    Serial.println("Attempting WiFi connection...");
    wm.setEnableConfigPortal(false);
    connected = wm.autoConnect(apName);
    if (!connected) {
      Serial.println("WiFi connection failed, starting setup portal...");
      display_show_setup_screen(apName, configUrl);
      connected = wm.startConfigPortal(apName);
      if (connected) {
        cache_clear();
        Serial.println("Cache cleared after WiFi reconfiguration");
      }
    }
  } else {
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

  // Sync time via NTP
  configTzTime("EST5EDT,M3.2.0,M11.1.0", "pool.ntp.org", "time.nist.gov");
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

  // Step 1: Find Home Assistant (mDNS or override URL)
  if (strlen(config.ha_url) == 0) {
    Serial.println("No HA URL configured, trying mDNS discovery...");
    if (!discoverHomeAssistant()) {
      display_show_error("Home Assistant not found");
      display_sleep();
      enterDeepSleep(300);  // Retry in 5 minutes
      return;
    }
  }

  // Step 2: Announce to HA and get endpoints (or poll if pending)
  if (!config.discovered || !hasEndpoints) {
    if (!announceAndConfigure()) {
      // announceAndConfigure handles display messages
      display_sleep();
      enterDeepSleep(30);  // Retry in 30 seconds
      return;
    }
  }

  // Step 3: Check for calendar updates and refresh display
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
 * Get device MAC address as a string (AA:BB:CC:DD:EE:FF)
 */
String getDeviceMac() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(macStr);
}

/**
 * Get device display name
 */
String getDeviceName() {
  String mac = getDeviceMac();
  return String(DEVICE_NAME_PREFIX) + "-" + mac.substring(mac.length() - 5);
  // e.g., "EinkCal-EE:FF"
}

/**
 * Discover Home Assistant via mDNS
 */
bool discoverHomeAssistant() {
  Serial.println("Starting mDNS discovery...");

  if (!MDNS.begin(("eink-cal-" + getDeviceMac().substring(getDeviceMac().length() - 5)).c_str())) {
    Serial.println("mDNS failed to start");
    return false;
  }

  // Query for Home Assistant's _home-assistant._tcp service
  int n = MDNS.queryService("home-assistant", "tcp");
  if (n == 0) {
    Serial.println("No Home Assistant found via mDNS");
    MDNS.end();
    return false;
  }

  // Use the first result
  IPAddress haIP = MDNS.IP(0);
  uint16_t haPort = MDNS.port(0);

  snprintf(config.ha_url, sizeof(config.ha_url), "http://%s:%d",
           haIP.toString().c_str(), haPort);

  Serial.printf("Discovered Home Assistant at: %s\n", config.ha_url);

  MDNS.end();

  // Save the discovered URL
  config.configured = true;
  config_save(&config);

  return true;
}

/**
 * Announce to Home Assistant and wait for configuration
 * Returns true if device is configured, false if still pending or error
 */
bool announceAndConfigure() {
  String mac = getDeviceMac();
  String name = getDeviceName();

  Serial.printf("Announcing to %s...\n", config.ha_url);

  AnnounceResponse resp = http_announce(config.ha_url, mac.c_str(),
                                         name.c_str(), FIRMWARE_VERSION);

  if (resp.status == ANNOUNCE_CONFIGURED) {
    // Store entry_id and endpoints
    strncpy(config.entry_id, resp.entry_id, sizeof(config.entry_id) - 1);
    config.refresh_interval = resp.refresh_interval * 60;  // Convert to seconds
    config.discovered = true;
    config_save(&config);

    // Save endpoints
    endpoints = resp.endpoints;
    endpoints_save(&endpoints);

    Serial.println("Device configured in Home Assistant!");
    return true;
  }

  if (resp.status == ANNOUNCE_PENDING) {
    display_show_message("Waiting for Home Assistant", "Configure in Settings > Devices");
    Serial.println("Waiting for user to configure device in HA...");
    return false;
  }

  // Error
  char errMsg[64];
  snprintf(errMsg, sizeof(errMsg), "Announce failed (HTTP %d)", resp.http_code);
  display_show_error(errMsg);
  return false;
}

/**
 * Callback when WiFiManager saves parameters
 */
void saveParamsCallback() {
  Serial.println("WiFiManager params saved");

  // Get HA URL override from custom parameter
  const char* url = custom_ha_url.getValue();
  if (url && strlen(url) > 0) {
    strncpy(config.ha_url, url, sizeof(config.ha_url) - 1);
    config.ha_url[sizeof(config.ha_url) - 1] = '\0';
    Serial.printf("HA URL override: %s\n", config.ha_url);
  }

  // Get refresh interval from custom parameter (in minutes, convert to seconds)
  const char* refresh_str = custom_refresh_interval.getValue();
  if (refresh_str && strlen(refresh_str) > 0) {
    int minutes = atoi(refresh_str);
    if (minutes >= 1 && minutes <= 1440) {
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
  // Reset discovery state so we re-announce
  config.discovered = false;

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
  enterDeepSleep(300);
}

/**
 * Check server for updates and refresh display if needed
 */
void updateCalendar() {
  Serial.println("Checking for calendar updates...");
  Serial.printf("HA URL: %s\n", config.ha_url);

  String mac = getDeviceMac();

  // Check if calendar has changed using ETag
  FetchResponse checkResponse = http_check_calendar(
    config.ha_url, endpoints.check, cache.etag, mac.c_str());

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

  esp_task_wdt_reset();

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
    FetchResponse resp = http_fetch_chunk(config.ha_url, endpoints.black_top,
                                          "", mac.c_str(), chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_black1(chunk_buffer);
      if (resp.new_etag[0] != '\0') {
        strncpy(cache.etag, resp.new_etag, sizeof(cache.etag) - 1);
      }
    } else {
      success = false;
      failedEndpoint = endpoints.black_top;
    }
  }

  esp_task_wdt_reset();

  // Download and send black layer chunk 2
  if (success) {
    FetchResponse resp = http_fetch_chunk(config.ha_url, endpoints.black_bottom,
                                          "", mac.c_str(), chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_black2(chunk_buffer);
    } else {
      success = false;
      failedEndpoint = endpoints.black_bottom;
    }
  }

  esp_task_wdt_reset();

  // Download and send red layer chunk 1
  if (success) {
    FetchResponse resp = http_fetch_chunk(config.ha_url, endpoints.red_top,
                                          "", mac.c_str(), chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_red1(chunk_buffer);
    } else {
      success = false;
      failedEndpoint = endpoints.red_top;
    }
  }

  esp_task_wdt_reset();

  // Download and send red layer chunk 2
  if (success) {
    FetchResponse resp = http_fetch_chunk(config.ha_url, endpoints.red_bottom,
                                          "", mac.c_str(), chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result == FETCH_OK) {
      display_send_red2(chunk_buffer);
    } else {
      success = false;
      failedEndpoint = endpoints.red_bottom;
    }
  }

  // Free buffer
  free(chunk_buffer);
  chunk_buffer = NULL;

  if (success) {
    Serial.println("Refreshing display...");
    display_refresh();

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
  if (digitalRead(SETUP_BUTTON_PIN) == HIGH) {
    return false;
  }

  Serial.println("Setup button pressed, checking hold duration...");

  unsigned long startTime = millis();
  while (millis() - startTime < BUTTON_HOLD_TIME_MS) {
    if (digitalRead(SETUP_BUTTON_PIN) == HIGH) {
      Serial.println("Button released early");
      return false;
    }
    delay(50);
  }

  Serial.println("Button held - entering setup mode");
  return true;
}
