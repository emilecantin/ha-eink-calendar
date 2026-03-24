#include "http_client.h"
#include <HTTPClient.h>
#include <WiFi.h>
#include <ArduinoJson.h>

// Timeout for HTTP operations (ms)
#define HTTP_TIMEOUT 15000
// Timeout for download stalls - if no new data received for this long, abort (ms)
#define DOWNLOAD_STALL_TIMEOUT 10000

AnnounceResponse http_announce(const char* ha_url, const char* mac,
                               const char* name, const char* fw_version) {
  AnnounceResponse response;
  response.status = ANNOUNCE_ERROR;
  response.entry_id[0] = '\0';
  response.refresh_interval = 15;
  response.http_code = 0;

  HTTPClient http;
  String url = String(ha_url) + "/api/eink_calendar/announce";

  http.begin(url);
  http.setTimeout(HTTP_TIMEOUT);
  http.addHeader("Content-Type", "application/json");

  // Build JSON payload
  String payload = "{\"mac\":\"" + String(mac) +
                   "\",\"name\":\"" + String(name) +
                   "\",\"firmware_version\":\"" + String(fw_version) + "\"}";

  int httpCode = http.POST(payload);
  response.http_code = httpCode;

  if (httpCode != 200) {
    Serial.printf("Announce failed, HTTP %d\n", httpCode);
    http.end();
    return response;
  }

  // Parse JSON response
  String body = http.getString();
  http.end();

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, body);
  if (err) {
    Serial.printf("JSON parse error: %s\n", err.c_str());
    return response;
  }

  const char* status = doc["status"];
  if (!status) {
    Serial.println("No status in response");
    return response;
  }

  if (strcmp(status, "configured") == 0) {
    response.status = ANNOUNCE_CONFIGURED;

    const char* eid = doc["entry_id"];
    if (eid) {
      strncpy(response.entry_id, eid, sizeof(response.entry_id) - 1);
      response.entry_id[sizeof(response.entry_id) - 1] = '\0';
    }

    response.refresh_interval = doc["refresh_interval"] | 15;

    // Parse endpoints
    JsonObject endpoints = doc["endpoints"];
    if (endpoints) {
      const char* bt = endpoints["black_top"];
      const char* bb = endpoints["black_bottom"];
      const char* rt = endpoints["red_top"];
      const char* rb = endpoints["red_bottom"];
      const char* ck = endpoints["check"];

      if (bt) strncpy(response.endpoints.black_top, bt, sizeof(response.endpoints.black_top) - 1);
      if (bb) strncpy(response.endpoints.black_bottom, bb, sizeof(response.endpoints.black_bottom) - 1);
      if (rt) strncpy(response.endpoints.red_top, rt, sizeof(response.endpoints.red_top) - 1);
      if (rb) strncpy(response.endpoints.red_bottom, rb, sizeof(response.endpoints.red_bottom) - 1);
      if (ck) strncpy(response.endpoints.check, ck, sizeof(response.endpoints.check) - 1);
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
                                  const char* current_etag, const char* mac) {
  FetchResponse response;
  response.result = FETCH_ERROR;
  response.new_etag[0] = '\0';
  response.http_code = 0;
  response.bytes_read = 0;

  HTTPClient http;
  String url = String(ha_url) + check_path;

  http.begin(url);
  http.setTimeout(HTTP_TIMEOUT);

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
  } else if (httpCode == 200) {
    response.result = FETCH_OK;

    String etag = http.header("ETag");
    Serial.printf("Received ETag: %s\n", etag.c_str());
    if (etag.length() > 0 && etag.length() < 33) {
      strncpy(response.new_etag, etag.c_str(), 32);
      response.new_etag[32] = '\0';
    }
  } else {
    Serial.printf("HTTP check failed, code: %d\n", httpCode);
    response.result = FETCH_ERROR;
  }

  http.end();
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
  FetchResponse response;
  response.result = FETCH_ERROR;
  response.new_etag[0] = '\0';
  response.http_code = 0;
  response.bytes_read = 0;

  HTTPClient http;
  String url = String(ha_url) + endpoint;

  http.begin(url);
  http.setTimeout(HTTP_TIMEOUT);

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
