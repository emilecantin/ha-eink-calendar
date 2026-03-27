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
#include <WebServer.h>
#include <ESPmDNS.h>
#include <esp_task_wdt.h>
#include <SPIFFS.h>
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

// Device info — FIRMWARE_VERSION is injected by PlatformIO from firmware.version
#define DEVICE_NAME_PREFIX "EinkCal"

// WiFiManager custom parameters (shown on the advanced "Setup" page)
char ha_url_override[128] = "";
WiFiManagerParameter custom_ha_url("ha_url", "Home Assistant URL (leave blank for auto-detection)", "", 128);
char refresh_interval_str[8] = "15";
WiFiManagerParameter custom_refresh_interval("refresh", "Refresh interval (minutes)", refresh_interval_str, 8);

// Global state
Config config;
CacheState cache;
BitmapEndpoints endpoints;
uint8_t* chunk_buffer = NULL;

// Boot count for debugging
RTC_DATA_ATTR int bootCount = 0;

// OTA crash guard — survives deep sleep but resets on power cycle
RTC_DATA_ATTR int otaFailCount = 0;
#define OTA_MAX_RETRIES 3

// TCP listener on port 443 — prevents Android 12+ "connection refused" on HTTPS probes
WiFiServer httpsRedirectServer(443);

// Forward declarations
void saveParamsCallback();
void handleConnectionFailure();
bool updateCalendar();
void enterDeepSleep(uint32_t seconds);
bool isSetupButtonHeld();
bool tryAnnounce(const char* ha_url);
bool discoverAndAnnounce();
bool promptForHaUrl();
void startHttpsRedirect();
void stopHttpsRedirect();
void handleHttpsRedirectClients();
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

  // Set timeout for config portal (10 minutes for first-time setup)
  wm.setConfigPortalTimeout(600);

  // Portal behavior
  wm.setCaptivePortalEnable(true);
  wm.setConfigPortalBlocking(true);
  wm.setConnectRetries(5);
  wm.setConnectTimeout(10);

  // Clean UI: hide info/update/erase, just show WiFi setup
  wm.setShowInfoUpdate(false);
  wm.setShowInfoErase(false);
  const char* menuItems[] = {"wifi", "param", "exit"};
  wm.setMenu(menuItems, 3);

  // Move advanced params (HA URL, refresh) to a separate "Setup" page
  wm.setParamsPage(true);

  // Start HTTPS redirect server when AP comes up (must wait for AP to be active)
  wm.setAPCallback([](WiFiManager* wm) {
    startHttpsRedirect();
  });

  // Friendly title and styling
  wm.setTitle("E-Ink Calendar");
  wm.setDarkMode(false);
  wm.setCustomHeadElement(
    "<style>"
    "body{font-family:-apple-system,sans-serif}"
    ".msg{padding:12px;background:#e8f5e9;border-radius:8px;margin:10px 0}"
    "h1{font-size:1.4em}"
    "button{border-radius:8px}"
    "</style>"
  );

  // Set static IP for AP mode
  IPAddress apIP(192, 168, 4, 1);
  IPAddress apGateway(192, 168, 4, 1);
  IPAddress apSubnet(255, 255, 255, 0);
  wm.setAPStaticIPConfig(apIP, apGateway, apSubnet);

  // Android captive portal fix: register handlers for probe URLs so Android
  // detects the portal properly (Android 10+ sends probes to these URLs)
  wm.setWebServerCallback([&wm]() {
    auto redirect = [&wm]() {
      wm.server->sendHeader("Location", "http://192.168.4.1/", true);
      wm.server->send(302, "text/plain", "");
    };
    // Android probes
    wm.server->on("/generate_204", HTTP_GET, redirect);
    wm.server->on("/gen_204", HTTP_GET, redirect);
    // Google connectivity check
    wm.server->on("/connecttest.txt", HTTP_GET, redirect);
    // Apple captive portal detection
    wm.server->on("/hotspot-detect.html", HTTP_GET, redirect);
    // Microsoft NCSI
    wm.server->on("/ncsi.txt", HTTP_GET, redirect);
    wm.server->on("/connecttest.txt", HTTP_GET, redirect);
    // Firefox captive portal detection
    wm.server->on("/canonical.html", HTTP_GET, redirect);
    wm.server->on("/success.txt", HTTP_GET, redirect);
  });

  // Pre-populate custom parameters with current values
  if (hasConfig && strlen(config.ha_url) > 0) {
    custom_ha_url.setValue(config.ha_url, 128);
  }
  uint32_t refresh_minutes = hasConfig ? (config.refresh_interval / 60) : 15;
  snprintf(refresh_interval_str, sizeof(refresh_interval_str), "%lu", (unsigned long)refresh_minutes);
  custom_refresh_interval.setValue(refresh_interval_str, 8);

  // Add advanced parameters (shown on separate "Setup" page)
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
  // Note: HTTPS redirect on port 443 starts automatically via setAPCallback
  // when the AP comes up, to fix Android 12+ captive portal detection.
  bool connected = false;
  if (forceSetup) {
    display_show_setup_screen(apName, configUrl);
    connected = wm.startConfigPortal(apName);
    stopHttpsRedirect();
  } else if (hasConfig || wm.getWiFiIsSaved()) {
    Serial.println("Attempting WiFi connection...");
    wm.setEnableConfigPortal(false);
    connected = wm.autoConnect(apName);
    if (!connected) {
      Serial.println("WiFi connection failed, starting setup portal...");
      display_show_setup_screen(apName, configUrl);
      connected = wm.startConfigPortal(apName);
      stopHttpsRedirect();
      if (connected) {
        cache_clear();
        Serial.println("Cache cleared after WiFi reconfiguration");
      }
    }
  } else {
    Serial.println("No config found, starting setup portal...");
    display_show_setup_screen(apName, configUrl);
    connected = wm.startConfigPortal(apName);
    stopHttpsRedirect();
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

  // Start mDNS and advertise our service so HA's zeroconf can discover us
  String hostname = "eink-cal-" + getDeviceMac().substring(getDeviceMac().length() - 5);
  if (MDNS.begin(hostname.c_str())) {
    String mac = getDeviceMac();
    MDNS.addService("eink-calendar", "tcp", 80);
    MDNS.addServiceTxt("eink-calendar", "tcp", "mac", mac.c_str());
    MDNS.addServiceTxt("eink-calendar", "tcp", "fw", FIRMWARE_VERSION);
    Serial.println("mDNS started, advertising _eink-calendar._tcp");
  } else {
    Serial.println("mDNS failed to start");
  }

  // Step 1: Discover HA and announce (or use saved config)
  if (!config.discovered || !hasEndpoints) {
    if (!discoverAndAnnounce()) {
      if (config.ha_url[0] != '\0') {
        // We found HA but aren't configured yet (pending or not installed) — poll
        display_sleep();
        enterDeepSleep(30);
        return;
      }

      // No HA found — show config screen and serve a form on our WiFi IP
      if (!promptForHaUrl()) {
        display_sleep();
        enterDeepSleep(300);
        return;
      }

      // User entered a URL — try announcing to it
      if (!discoverAndAnnounce()) {
        display_sleep();
        enterDeepSleep(config.ha_url[0] != '\0' ? 30 : 300);
        return;
      }
    }
  }

  // Step 2: Check for calendar updates and refresh display
  if (!updateCalendar()) {
    // Download failed — retry in 60 seconds instead of full interval
    Serial.println("Calendar update failed, retrying in 60s");
    enterDeepSleep(60);
    return;
  }

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
 * Try announcing to a single HA instance.
 * Returns true if device is fully configured, false otherwise.
 * Sets config.discovered = true and saves on pending (so we retry the same URL).
 */
bool tryAnnounce(const char* ha_url) {
  String mac = getDeviceMac();
  String name = getDeviceName();

  Serial.printf("Announcing to %s...\n", ha_url);

  AnnounceResponse resp = http_announce(ha_url, mac.c_str(),
                                         name.c_str(), FIRMWARE_VERSION);

  if (resp.status == ANNOUNCE_CONFIGURED) {
    strncpy(config.ha_url, ha_url, sizeof(config.ha_url) - 1);
    strncpy(config.entry_id, resp.entry_id, sizeof(config.entry_id) - 1);
    config.refresh_interval = resp.refresh_interval * 60;  // Convert to seconds
    config.discovered = true;
    config.configured = true;
    config_save(&config);

    endpoints = resp.endpoints;
    endpoints_save(&endpoints);

    if (resp.ota.available) {
      Serial.printf("OTA update available: v%s (%u bytes) at %s\n",
                    resp.ota.version, resp.ota.size, resp.ota.url);
    }

    Serial.println("Device configured in Home Assistant!");
    return true;
  }

  if (resp.status == ANNOUNCE_PENDING) {
    // Save this URL so we keep polling the same instance
    strncpy(config.ha_url, ha_url, sizeof(config.ha_url) - 1);
    config.configured = true;
    config_save(&config);

    display_show_message("Waiting for Home Assistant", "Configure in Settings > Devices");
    Serial.println("Waiting for user to configure device in HA...");
    return false;
  }

  if (resp.status == ANNOUNCE_NOT_INSTALLED) {
    // HA is there but the integration isn't installed yet — save URL, ask user to install
    strncpy(config.ha_url, ha_url, sizeof(config.ha_url) - 1);
    config.configured = true;
    config_save(&config);

    display_show_install_screen("https://github.com/emilecantin/ha-eink-calendar");
    Serial.println("HA found but integration not installed");
    return false;
  }

  // Error — don't save, try next instance
  Serial.printf("Announce failed (HTTP %d)\n", resp.http_code);
  return false;
}

/**
 * Discover Home Assistant via mDNS and announce to each instance.
 * If ha_url is already set (override or previous discovery), announce to that directly.
 * Returns true if device is fully configured.
 */
bool discoverAndAnnounce() {
  // If we already have a URL (override or previously discovered), try it directly
  if (strlen(config.ha_url) > 0) {
    return tryAnnounce(config.ha_url);
  }

  Serial.println("Discovering Home Assistant via mDNS...");

  int n = MDNS.queryService("home-assistant", "tcp");
  if (n == 0) {
    Serial.println("No Home Assistant found via mDNS");

    return false;
  }

  Serial.printf("Found %d Home Assistant instance(s)\n", n);

  // Try announcing to each discovered instance
  for (int i = 0; i < n; i++) {
    char url[128];

    // Prefer base_url from TXT record (respects user's configured hostname/HTTPS)
    String baseUrl = MDNS.txt(i, "base_url");
    if (baseUrl.length() == 0) {
      baseUrl = MDNS.txt(i, "internal_url");
    }

    if (baseUrl.length() > 0) {
      // Remove trailing slash if present
      if (baseUrl.endsWith("/")) baseUrl.remove(baseUrl.length() - 1);
      strncpy(url, baseUrl.c_str(), sizeof(url) - 1);
      url[sizeof(url) - 1] = '\0';
    } else {
      // Fallback to IP + port
      snprintf(url, sizeof(url), "http://%s:%d",
               MDNS.address(i).toString().c_str(), MDNS.port(i));
    }

    Serial.printf("Trying instance %d: %s\n", i + 1, url);

    if (tryAnnounce(url)) {
  
      return true;
    }

    // If announce returned pending, we've already saved this URL and shown
    // the waiting message — stop trying others
    if (strlen(config.ha_url) > 0) {
  
      return false;
    }
  }

  // mDNS stays running so HA can discover us
  return false;
}

/**
 * Serve a web form on the current WiFi IP so the user can enter the HA URL.
 * Displays a QR code pointing to the form. Blocks until submission or timeout.
 * Returns true if user submitted a URL (saved to config), false on timeout.
 */
bool promptForHaUrl() {
  String ip = WiFi.localIP().toString();
  String formUrl = "http://" + ip;

  Serial.printf("Starting HA URL config server at %s\n", formUrl.c_str());

  // Show QR code on display pointing to our IP
  display_show_ha_config_screen(formUrl.c_str());

  WebServer server(80);
  volatile bool submitted = false;

  // Serve the config form
  server.on("/", HTTP_GET, [&server]() {
    server.send(200, "text/html",
      "<!DOCTYPE html><html><head>"
      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
      "<title>E-Ink Calendar</title>"
      "<style>"
      "body{font-family:sans-serif;max-width:480px;margin:40px auto;padding:0 20px}"
      "h1{font-size:1.4em}input[type=text]{width:100%;padding:12px;font-size:1em;"
      "box-sizing:border-box;margin:8px 0}button{background:#03a9f4;color:#fff;"
      "border:none;padding:14px 24px;font-size:1em;cursor:pointer;width:100%}"
      "</style></head><body>"
      "<h1>E-Ink Calendar Setup</h1>"
      "<p>Home Assistant was not found automatically on your network.</p>"
      "<p>Enter your Home Assistant URL below:</p>"
      "<form method='POST' action='/save'>"
      "<input type='text' name='ha_url' placeholder='http://homeassistant.local:8123' "
      "required autofocus>"
      "<br><button type='submit'>Save</button>"
      "</form></body></html>"
    );
  });

  server.on("/save", HTTP_POST, [&server, &submitted]() {
    String url = server.arg("ha_url");
    if (url.length() > 0) {
      // Remove trailing slash
      if (url.endsWith("/")) url.remove(url.length() - 1);

      strncpy(config.ha_url, url.c_str(), sizeof(config.ha_url) - 1);
      config.ha_url[sizeof(config.ha_url) - 1] = '\0';
      config.configured = true;
      config.discovered = false;
      config_save(&config);
      cache_clear();

      Serial.printf("HA URL saved: %s\n", config.ha_url);

      server.send(200, "text/html",
        "<!DOCTYPE html><html><head>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<style>body{font-family:sans-serif;max-width:480px;margin:40px auto;padding:0 20px}</style>"
        "</head><body>"
        "<h1>Saved!</h1>"
        "<p>The display will now connect to Home Assistant.</p>"
        "</body></html>"
      );

      submitted = true;
    } else {
      server.send(400, "text/html", "<h1>URL is required</h1>");
    }
  });

  server.begin();
  Serial.println("Config server started, waiting for user input...");

  // Disable watchdog — we're waiting for user interaction
  esp_task_wdt_delete(NULL);

  // Wait for submission or timeout (5 minutes)
  unsigned long start = millis();
  while (!submitted && (millis() - start < 300000)) {
    server.handleClient();
    delay(10);
  }

  server.stop();
  esp_task_wdt_add(NULL);

  if (submitted) {
    Serial.println("User submitted HA URL");
    return true;
  }

  Serial.println("Config server timed out");
  return false;
}

// Handle for the HTTPS redirect background task
static TaskHandle_t httpsTaskHandle = NULL;
static volatile bool httpsTaskRunning = false;

/**
 * Background task that accepts TCP connections on port 443 and sends HTTP 302
 * redirects. Runs on core 0 so it works while WiFiManager blocks on core 1.
 */
static void httpsRedirectTask(void* param) {
  while (httpsTaskRunning) {
    WiFiClient client = httpsRedirectServer.accept();
    if (client) {
      // Wait briefly for data (Android sends a TLS ClientHello, we ignore it)
      unsigned long start = millis();
      while (client.connected() && !client.available() && millis() - start < 200) {
        delay(1);
      }
      // Drain any incoming data
      while (client.available()) client.read();

      // Send HTTP 302 redirect — this isn't valid TLS, but Android's captive
      // portal detector accepts it and triggers the portal popup
      client.print(
        "HTTP/1.1 302 Found\r\n"
        "Location: http://192.168.4.1/\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n\r\n"
      );
      client.stop();
    }
    vTaskDelay(pdMS_TO_TICKS(50));
  }
  vTaskDelete(NULL);
}

/**
 * Start TCP listener on port 443 for Android 12+ captive portal detection.
 * Android sends HTTPS probes; without a listener, the connection is refused
 * and Android shows "no internet" instead of the captive portal prompt.
 * Runs as a background task on core 0 since WiFiManager blocks the main loop.
 */
void startHttpsRedirect() {
  httpsRedirectServer.begin();
  httpsTaskRunning = true;
  xTaskCreatePinnedToCore(httpsRedirectTask, "https443", 4096, NULL, 1, &httpsTaskHandle, 0);
  Serial.println("HTTPS redirect listener started on port 443");
}

void stopHttpsRedirect() {
  httpsTaskRunning = false;
  if (httpsTaskHandle) {
    vTaskDelay(pdMS_TO_TICKS(100));  // Let the task exit cleanly
    httpsTaskHandle = NULL;
  }
  httpsRedirectServer.stop();
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
 * Check server for updates and refresh display if needed.
 * Returns true on success (or no change), false on failure.
 */
bool updateCalendar() {
  Serial.println("Checking for calendar updates...");
  Serial.printf("HA URL: %s\n", config.ha_url);

  String mac = getDeviceMac();

  // Sync state with HA — sends ETag + firmware version, gets back what changed
  FetchResponse checkResponse = http_check_calendar(
    config.ha_url, endpoints.check, cache.etag, mac.c_str(), FIRMWARE_VERSION);

  // Update refresh interval if HA sent a new one
  if (checkResponse.refresh_interval > 0) {
    uint32_t new_interval = checkResponse.refresh_interval * 60;
    if (new_interval != config.refresh_interval) {
      Serial.printf("Refresh interval updated: %d -> %d minutes\n",
                    config.refresh_interval / 60, checkResponse.refresh_interval);
      config.refresh_interval = new_interval;
      config_save(&config);
    }
  }

  if (checkResponse.result == FETCH_ERROR) {
    Serial.printf("Check failed with HTTP %d\n", checkResponse.http_code);
    return false;
  }

  // Apply OTA firmware update if available (before bitmap download)
  if (checkResponse.ota.available) {
    if (otaFailCount >= OTA_MAX_RETRIES) {
      Serial.printf("OTA: skipping — %d consecutive failures, waiting for new version\n",
                    otaFailCount);
    } else {
      Serial.println("Applying OTA firmware update...");
      otaFailCount++;  // Increment BEFORE attempt — if we crash, this persists
      if (!http_ota_update(config.ha_url, checkResponse.ota.url,
                           mac.c_str(), checkResponse.ota.size)) {
        Serial.printf("OTA update failed (attempt %d/%d), continuing with calendar update\n",
                      otaFailCount, OTA_MAX_RETRIES);
      }
      // If OTA succeeded, ESP.restart() was called and we never reach here
    }
  } else {
    // No OTA available — reset failure counter (new firmware version may fix things)
    otaFailCount = 0;
  }

  if (checkResponse.result == FETCH_NOT_MODIFIED) {
    Serial.println("Calendar unchanged, skipping display refresh");
    return true;
  }

  esp_task_wdt_reset();

  // Calendar has changed, download all chunks
  Serial.println("Calendar changed, downloading...");

  // Allocate single buffer for download+send
  chunk_buffer = (uint8_t*)malloc(CHUNK_BUFFER_SIZE);
  if (!chunk_buffer) {
    Serial.println("Failed to allocate chunk buffer!");
    display_show_error("Memory allocation failed");
    display_sleep();
    return false;
  }

  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS mount failed!");
    free(chunk_buffer);
    return false;
  }

  bool success = true;
  const char* failedEndpoint = NULL;

  const char* chunk_endpoints[] = {
    endpoints.black_top, endpoints.black_bottom,
    endpoints.red_top,   endpoints.red_bottom,
  };
  const char* chunk_files[] = {
    "/bk1.bin", "/bk2.bin", "/rd1.bin", "/rd2.bin",
  };

  // --- Phase 1: Download all chunks to SPIFFS ---

  for (int i = 0; i < 4 && success; i++) {
    FetchResponse resp = http_fetch_chunk(config.ha_url, chunk_endpoints[i],
                                          "", mac.c_str(), chunk_buffer, CHUNK_BUFFER_SIZE);
    if (resp.result != FETCH_OK) {
      success = false;
      failedEndpoint = chunk_endpoints[i];
      break;
    }
    if (i == 0 && resp.new_etag[0] != '\0') {
      strncpy(cache.etag, resp.new_etag, sizeof(cache.etag) - 1);
    }
    File f = SPIFFS.open(chunk_files[i], FILE_WRITE);
    if (!f || f.write(chunk_buffer, CHUNK_BUFFER_SIZE) != CHUNK_BUFFER_SIZE) {
      Serial.printf("SPIFFS write failed: %s\n", chunk_files[i]);
      if (f) f.close();
      success = false;
      failedEndpoint = chunk_endpoints[i];
      break;
    }
    f.close();
    esp_task_wdt_reset();
  }

  if (!success) {
    Serial.printf("Download failed for %s\n", failedEndpoint);
    free(chunk_buffer);
    SPIFFS.end();
    display_show_message("Download failed", "Retrying in 60 seconds...");
    display_sleep();
    return false;
  }

  // --- Phase 2: Init display, read chunks from SPIFFS, send ---

  display_init();

  typedef void (*SendFunc)(const uint8_t*);
  SendFunc send_funcs[] = {
    display_send_black1, display_send_black2,
    display_send_red1,   display_send_red2,
  };

  for (int i = 0; i < 4 && success; i++) {
    File f = SPIFFS.open(chunk_files[i], FILE_READ);
    if (!f || f.read(chunk_buffer, CHUNK_BUFFER_SIZE) != CHUNK_BUFFER_SIZE) {
      Serial.printf("SPIFFS read failed: %s\n", chunk_files[i]);
      if (f) f.close();
      success = false;
      break;
    }
    f.close();
    send_funcs[i](chunk_buffer);
    esp_task_wdt_reset();
  }

  free(chunk_buffer);
  chunk_buffer = NULL;
  SPIFFS.end();

  if (success) {
    Serial.println("Refreshing display...");
    display_refresh();

    cache.display_valid = true;
    cache_save(&cache);

    Serial.println("Display updated successfully!");
  } else {
    Serial.println("SPIFFS read failed during display update");
  }

  display_sleep();
  return success;
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
