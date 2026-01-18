#ifndef EPCAL_HTTP_CLIENT_H
#define EPCAL_HTTP_CLIENT_H

#include <Arduino.h>

// Result of a fetch operation
enum FetchResult {
  FETCH_OK,            // 200 - new content downloaded
  FETCH_NOT_MODIFIED,  // 304 - content unchanged
  FETCH_ERROR          // Network or server error
};

// Response from fetch operation
struct FetchResponse {
  FetchResult result;
  char new_etag[33];   // ETag from response (if 200)
  int http_code;       // HTTP status code
  size_t bytes_read;   // Number of bytes downloaded
};

// Chunk endpoints
#define ENDPOINT_BLACK1 "/calendar/black1"
#define ENDPOINT_BLACK2 "/calendar/black2"
#define ENDPOINT_RED1   "/calendar/red1"
#define ENDPOINT_RED2   "/calendar/red2"
#define ENDPOINT_CHECK  "/calendar/check"

/**
 * Check if calendar has changed using ETag
 *
 * @param base_url      Server base URL (e.g., "http://192.168.1.50:4000")
 * @param current_etag  Current stored ETag (empty string if none)
 * @param new_etag      Buffer to store new ETag if changed (33 bytes)
 * @return              FETCH_OK if changed, FETCH_NOT_MODIFIED if same, FETCH_ERROR on failure
 */
FetchResponse http_check_calendar(const char* base_url, const char* current_etag);

/**
 * Fetch a bitmap chunk from the server
 *
 * @param base_url      Server base URL
 * @param endpoint      Endpoint path (e.g., ENDPOINT_BLACK1)
 * @param current_etag  Current stored ETag (send as If-None-Match)
 * @param buffer        Buffer to store downloaded data
 * @param buffer_size   Size of buffer
 * @return              FetchResponse with result and new ETag if applicable
 */
FetchResponse http_fetch_chunk(
  const char* base_url,
  const char* endpoint,
  const char* current_etag,
  uint8_t* buffer,
  size_t buffer_size
);

#endif // EPCAL_HTTP_CLIENT_H
