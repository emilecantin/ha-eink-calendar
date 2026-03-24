#include "http_client.h"
#include <HTTPClient.h>
#include <WiFi.h>

// Timeout for HTTP operations (ms)
#define HTTP_TIMEOUT 15000
// Timeout for download stalls - if no new data received for this long, abort (ms)
#define DOWNLOAD_STALL_TIMEOUT 10000

FetchResponse http_check_calendar(const char* base_url, const char* current_etag) {
  FetchResponse response;
  response.result = FETCH_ERROR;
  response.new_etag[0] = '\0';
  response.http_code = 0;
  response.bytes_read = 0;

  HTTPClient http;
  String url = String(base_url) + ENDPOINT_CHECK;

  http.begin(url);
  http.setTimeout(HTTP_TIMEOUT);

  // Must collect ETag header before request
  const char* headerKeys[] = {"ETag"};
  http.collectHeaders(headerKeys, 1);

  // Send If-None-Match header if we have an etag
  if (current_etag && current_etag[0] != '\0') {
    http.addHeader("If-None-Match", current_etag);
  }

  int httpCode = http.GET();
  response.http_code = httpCode;

  if (httpCode == 304) {
    // Not modified
    response.result = FETCH_NOT_MODIFIED;
  } else if (httpCode == 200) {
    // Changed - extract new ETag
    response.result = FETCH_OK;

    String etag = http.header("ETag");
    Serial.printf("Received ETag: %s\n", etag.c_str());
    if (etag.length() > 0 && etag.length() < 33) {
      strncpy(response.new_etag, etag.c_str(), 32);
      response.new_etag[32] = '\0';
    }
  } else {
    // Error
    Serial.printf("HTTP check failed, code: %d\n", httpCode);
    response.result = FETCH_ERROR;
  }

  http.end();
  return response;
}

FetchResponse http_fetch_chunk(
  const char* base_url,
  const char* endpoint,
  const char* current_etag,
  uint8_t* buffer,
  size_t buffer_size
) {
  FetchResponse response;
  response.result = FETCH_ERROR;
  response.new_etag[0] = '\0';
  response.http_code = 0;
  response.bytes_read = 0;

  HTTPClient http;
  String url = String(base_url) + endpoint;

  http.begin(url);
  http.setTimeout(HTTP_TIMEOUT);

  // Must collect ETag header before request
  const char* headerKeys[] = {"ETag"};
  http.collectHeaders(headerKeys, 1);

  // Send If-None-Match header if we have an etag
  if (current_etag && current_etag[0] != '\0') {
    http.addHeader("If-None-Match", current_etag);
  }

  int httpCode = http.GET();
  response.http_code = httpCode;

  if (httpCode == 304) {
    // Not modified
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
