#include "http_client.h"
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Update.h>
#include <esp_task_wdt.h>

// Timeout for HTTP operations (ms)
#define HTTP_TIMEOUT 15000
// Timeout for download stalls - if no new data received for this long, abort (ms)
#define DOWNLOAD_STALL_TIMEOUT 10000

// Reusable secure client for HTTPS connections (skip cert verification for LAN use)
static WiFiClientSecure secureClient;
static WiFiClient plainClient;

/**
 * Begin an HTTP request, handling both http:// and https:// URLs.
 * For HTTPS, uses WiFiClientSecure with certificate verification disabled
 * (acceptable for LAN-only device communication).
 */
static void httpBegin(HTTPClient& http, const String& url) {
  // Stop any previous connection to reset TLS state — the static clients are
  // reused across calls and stale state can cause handshake failures.
  secureClient.stop();
  plainClient.stop();

  if (url.startsWith("https://")) {
    secureClient.setInsecure();
    http.begin(secureClient, url);
  } else {
    http.begin(plainClient, url);
  }
  http.setTimeout(HTTP_TIMEOUT);
}

AnnounceResponse http_announce(const char* ha_url, const char* mac,
                               const char* name, const char* fw_version) {
  AnnounceResponse response = {};
  response.status = ANNOUNCE_ERROR;
  response.refresh_interval = 15;

  HTTPClient http;
  String url = String(ha_url) + "/api/eink_calendar/announce";

  httpBegin(http, url);
  http.addHeader("Content-Type", "application/json");

  // Build JSON payload
  JsonDocument doc;
  doc["mac"] = mac;
  doc["name"] = name;
  doc["firmware_version"] = fw_version;
  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);
  response.http_code = httpCode;

  if (httpCode == 404) {
    Serial.println("Announce endpoint not found (integration not installed?)");
    response.status = ANNOUNCE_NOT_INSTALLED;
    http.end();
    return response;
  }

  if (httpCode != 200) {
    Serial.printf("Announce failed, HTTP %d\n", httpCode);
    http.end();
    return response;
  }

  // Parse JSON response
  String body = http.getString();
  http.end();

  JsonDocument resp_doc;
  DeserializationError err = deserializeJson(resp_doc, body);
  if (err) {
    Serial.printf("JSON parse error: %s\n", err.c_str());
    return response;
  }

  const char* status = resp_doc["status"];
  if (!status) {
    Serial.println("No status in response");
    return response;
  }

  if (strcmp(status, "configured") == 0) {
    response.status = ANNOUNCE_CONFIGURED;

    const char* eid = resp_doc["entry_id"];
    if (eid) {
      strncpy(response.entry_id, eid, sizeof(response.entry_id) - 1);
      response.entry_id[sizeof(response.entry_id) - 1] = '\0';
    }

    response.refresh_interval = resp_doc["refresh_interval"] | 15;

    // Parse endpoints
    JsonObject endpoints = resp_doc["endpoints"];
    if (endpoints) {
      const char* bt = endpoints["black_top"];
      const char* bb = endpoints["black_bottom"];
      const char* rt = endpoints["red_top"];
      const char* rb = endpoints["red_bottom"];
      const char* ck = endpoints["check"];

      if (bt) { strncpy(response.endpoints.black_top, bt, sizeof(response.endpoints.black_top) - 1); response.endpoints.black_top[sizeof(response.endpoints.black_top) - 1] = '\0'; }
      if (bb) { strncpy(response.endpoints.black_bottom, bb, sizeof(response.endpoints.black_bottom) - 1); response.endpoints.black_bottom[sizeof(response.endpoints.black_bottom) - 1] = '\0'; }
      if (rt) { strncpy(response.endpoints.red_top, rt, sizeof(response.endpoints.red_top) - 1); response.endpoints.red_top[sizeof(response.endpoints.red_top) - 1] = '\0'; }
      if (rb) { strncpy(response.endpoints.red_bottom, rb, sizeof(response.endpoints.red_bottom) - 1); response.endpoints.red_bottom[sizeof(response.endpoints.red_bottom) - 1] = '\0'; }
      if (ck) { strncpy(response.endpoints.check, ck, sizeof(response.endpoints.check) - 1); response.endpoints.check[sizeof(response.endpoints.check) - 1] = '\0'; }
      const char* er = endpoints["error"];
      if (er) { strncpy(response.endpoints.error, er, sizeof(response.endpoints.error) - 1); response.endpoints.error[sizeof(response.endpoints.error) - 1] = '\0'; }
    }

    // Parse OTA firmware update info if present
    JsonObject fw_update = resp_doc["firmware_update"];
    if (fw_update) {
      response.ota.available = true;
      const char* fwVer = fw_update["version"];
      const char* fwUrl = fw_update["url"];
      if (fwVer) { strncpy(response.ota.version, fwVer, sizeof(response.ota.version) - 1); response.ota.version[sizeof(response.ota.version) - 1] = '\0'; }
      if (fwUrl) { strncpy(response.ota.url, fwUrl, sizeof(response.ota.url) - 1); response.ota.url[sizeof(response.ota.url) - 1] = '\0'; }
      response.ota.size = fw_update["size"] | 0;
    }

    Serial.printf("Announced: configured (entry_id: %s, refresh: %d min)\n",
                  response.entry_id, response.refresh_interval);
  } else if (strcmp(status, "pending") == 0) {
    response.status = ANNOUNCE_PENDING;
    Serial.println("Announced: pending (waiting for HA configuration)");
  } else {
    Serial.printf("Announced: unknown status '%s'\n", status);
  }

  return response;
}

FetchResponse http_check_calendar(const char* ha_url, const char* check_path,
                                  const char* current_etag, const char* mac,
                                  const char* fw_version) {
  FetchResponse response = {};
  response.result = FETCH_ERROR;
  response.refresh_interval = -1;

  HTTPClient http;
  String url = String(ha_url) + check_path;

  httpBegin(http, url);

  // Send device state
  http.addHeader("X-MAC", mac);
  http.addHeader("X-Firmware-Version", fw_version);
  if (current_etag && current_etag[0] != '\0') {
    http.addHeader("If-None-Match", current_etag);
  }

  // Must collect headers before request (for 304 response)
  const char* headerKeys[] = {"X-Refresh-Interval"};
  http.collectHeaders(headerKeys, 1);

  int httpCode = http.GET();
  response.http_code = httpCode;

  if (httpCode == 304) {
    // Nothing to do — read refresh interval from header
    response.result = FETCH_NOT_MODIFIED;
    if (http.hasHeader("X-Refresh-Interval")) {
      response.refresh_interval = http.header("X-Refresh-Interval").toInt();
    }
    http.end();
    return response;
  }

  if (httpCode != 200) {
    Serial.printf("HTTP check failed, code: %d\n", httpCode);
    http.end();
    return response;
  }

  // 200 — something changed, parse JSON body
  String body = http.getString();
  http.end();

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, body);
  if (err) {
    Serial.printf("Check JSON parse error: %s\n", err.c_str());
    return response;
  }

  // ETag present = image changed
  const char* etag = doc["etag"];
  if (etag) {
    response.result = FETCH_OK;
    strncpy(response.new_etag, etag, sizeof(response.new_etag) - 1);
    response.new_etag[sizeof(response.new_etag) - 1] = '\0';
    Serial.printf("Received ETag: %s\n", response.new_etag);
  } else {
    response.result = FETCH_NOT_MODIFIED;
  }

  // Refresh interval
  response.refresh_interval = doc["refresh_interval"] | -1;

  // Firmware update
  JsonObject fw_update = doc["firmware_update"];
  if (fw_update) {
    response.ota.available = true;
    const char* fwVer = fw_update["version"];
    const char* fwUrl = fw_update["url"];
    if (fwVer) { strncpy(response.ota.version, fwVer, sizeof(response.ota.version) - 1); response.ota.version[sizeof(response.ota.version) - 1] = '\0'; }
    if (fwUrl) { strncpy(response.ota.url, fwUrl, sizeof(response.ota.url) - 1); response.ota.url[sizeof(response.ota.url) - 1] = '\0'; }
    response.ota.size = fw_update["size"] | 0;
    Serial.printf("Firmware update available: v%s (%u bytes)\n",
                  response.ota.version, response.ota.size);
  }

  return response;
}

FetchResponse http_fetch_chunk(
  const char* ha_url,
  const char* endpoint,
  const char* current_etag,
  const char* mac,
  uint8_t* buffer,
  size_t buffer_size
) {
  FetchResponse response = {};
  response.result = FETCH_ERROR;

  HTTPClient http;
  String url = String(ha_url) + endpoint;

  httpBegin(http, url);

  // Must collect ETag header before request
  const char* headerKeys[] = {"ETag"};
  http.collectHeaders(headerKeys, 1);

  // Add MAC header for authentication
  http.addHeader("X-MAC", mac);

  // Send If-None-Match header if we have an etag
  if (current_etag && current_etag[0] != '\0') {
    http.addHeader("If-None-Match", current_etag);
  }

  int httpCode = http.GET();
  response.http_code = httpCode;

  if (httpCode == 304) {
    response.result = FETCH_NOT_MODIFIED;
    http.end();
    return response;
  }

  if (httpCode != 200) {
    Serial.printf("HTTP fetch failed for %s, code: %d\n", endpoint, httpCode);
    http.end();
    return response;
  }

  // Extract ETag from response
  String etag = http.header("ETag");
  if (etag.length() > 0 && etag.length() < 33) {
    strncpy(response.new_etag, etag.c_str(), 32);
    response.new_etag[32] = '\0';
  }

  // Get content length
  int contentLength = http.getSize();
  if (contentLength <= 0) {
    Serial.println("Invalid content length");
    http.end();
    return response;
  }

  if ((size_t)contentLength > buffer_size) {
    Serial.printf("Content too large: %d > %zu\n", contentLength, buffer_size);
    http.end();
    return response;
  }

  // Read content into buffer
  WiFiClient* stream = http.getStreamPtr();
  size_t bytesRead = 0;
  unsigned long lastDataTime = millis();

  while (http.connected() && bytesRead < (size_t)contentLength) {
    size_t available = stream->available();
    if (available > 0) {
      size_t toRead = min(available, (size_t)contentLength - bytesRead);
      size_t read = stream->readBytes(buffer + bytesRead, toRead);
      bytesRead += read;
      lastDataTime = millis();  // Reset stall timer
    } else if (millis() - lastDataTime > DOWNLOAD_STALL_TIMEOUT) {
      Serial.printf("Download stalled for %s after %zu / %d bytes\n", endpoint, bytesRead, contentLength);
      break;
    }
    yield();  // Allow background tasks
  }

  if (bytesRead == (size_t)contentLength) {
    response.result = FETCH_OK;
    response.bytes_read = bytesRead;
    Serial.printf("Downloaded %s: %zu bytes\n", endpoint, bytesRead);
  } else {
    Serial.printf("Incomplete download: %zu / %d bytes\n", bytesRead, contentLength);
  }

  http.end();
  return response;
}

void http_report_error(const char* ha_url, const char* error_path,
                       const char* mac, const char* error,
                       const char* details) {
  if (!error_path || error_path[0] == '\0') {
    return;  // No error endpoint configured
  }

  HTTPClient http;
  String url = String(ha_url) + error_path;

  httpBegin(http, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-MAC", mac);

  // Build JSON payload
  JsonDocument doc;
  doc["error"] = error;
  if (details && details[0] != '\0') {
    doc["details"] = details;
  }
  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);
  if (httpCode == 200) {
    Serial.printf("Error reported to HA: %s\n", error);
  } else {
    Serial.printf("Failed to report error (HTTP %d)\n", httpCode);
  }
  http.end();
}

bool http_ota_update(const char* ha_url, const char* ota_path,
                     const char* mac, uint32_t expected_size) {
  if (expected_size == 0) {
    Serial.println("OTA: no expected size provided, aborting");
    return false;
  }

  Serial.printf("OTA: downloading firmware (%u bytes) from %s%s\n",
                expected_size, ha_url, ota_path);

  HTTPClient http;
  String url = String(ha_url) + ota_path;

  httpBegin(http, url);
  http.addHeader("X-MAC", mac);

  int httpCode = http.GET();
  if (httpCode != 200) {
    Serial.printf("OTA: HTTP %d\n", httpCode);
    http.end();
    return false;
  }

  int contentLength = http.getSize();
  if (contentLength <= 0) {
    Serial.println("OTA: invalid content length");
    http.end();
    return false;
  }

  if ((uint32_t)contentLength != expected_size) {
    Serial.printf("OTA: size mismatch: got %d, expected %u\n",
                  contentLength, expected_size);
    http.end();
    return false;
  }

  if (!Update.begin(contentLength)) {
    Serial.printf("OTA: Update.begin failed: %s\n", Update.errorString());
    http.end();
    return false;
  }

  Serial.println("OTA: flashing...");

  WiFiClient* stream = http.getStreamPtr();
  size_t written = 0;
  uint8_t buf[4096];
  unsigned long lastDataTime = millis();

  while (http.connected() && written < (size_t)contentLength) {
    // Reset watchdog — download + flash can take a while
    esp_task_wdt_reset();

    size_t available = stream->available();
    if (available > 0) {
      size_t toRead = min(available, sizeof(buf));
      toRead = min(toRead, (size_t)contentLength - written);
      size_t bytesRead = stream->readBytes(buf, toRead);
      size_t bytesWritten = Update.write(buf, bytesRead);
      if (bytesWritten != bytesRead) {
        Serial.printf("OTA: write error at %zu bytes: %s\n",
                      written, Update.errorString());
        Update.abort();
        http.end();
        return false;
      }
      written += bytesWritten;
      lastDataTime = millis();

      // Progress every 100KB
      if (written % 102400 < bytesWritten) {
        Serial.printf("OTA: %zu / %d bytes (%d%%)\n",
                      written, contentLength, (int)(written * 100 / contentLength));
      }
    } else if (millis() - lastDataTime > DOWNLOAD_STALL_TIMEOUT) {
      Serial.printf("OTA: download stalled at %zu / %d bytes\n",
                    written, contentLength);
      Update.abort();
      http.end();
      return false;
    }
    yield();
  }

  if (written < (size_t)contentLength) {
    Serial.printf("OTA: connection lost at %zu / %d bytes\n",
                  written, contentLength);
    Update.abort();
    http.end();
    return false;
  }

  http.end();

  if (!Update.end(true)) {
    Serial.printf("OTA: finalize failed: %s\n", Update.errorString());
    return false;
  }

  Serial.println("OTA: success! Rebooting...");
  Serial.flush();
  delay(100);
  ESP.restart();
  return true;  // Never reached
}
