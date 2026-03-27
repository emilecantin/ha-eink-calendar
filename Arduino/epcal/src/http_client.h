#ifndef EINK_CALENDAR_HTTP_CLIENT_H
#define EINK_CALENDAR_HTTP_CLIENT_H

#include <Arduino.h>
#include "config.h"

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
  int refresh_interval; // From X-Refresh-Interval header (-1 if absent)
};

// Announce status
enum AnnounceStatus {
  ANNOUNCE_CONFIGURED,      // Device is configured, endpoints returned
  ANNOUNCE_PENDING,         // Waiting for user to configure in HA
  ANNOUNCE_NOT_INSTALLED,   // HA found but integration not installed (404)
  ANNOUNCE_ERROR            // Error communicating with HA
};

// OTA firmware update info from announce response
struct OtaInfo {
  bool available;
  char version[32];
  char url[128];
  uint32_t size;
};

// Response from announce
struct AnnounceResponse {
  AnnounceStatus status;
  char entry_id[64];
  uint32_t refresh_interval;  // in minutes
  BitmapEndpoints endpoints;
  OtaInfo ota;
  int http_code;
};

/**
 * Announce this device to Home Assistant
 *
 * @param ha_url       Home Assistant base URL (e.g., "http://192.168.1.50:8123")
 * @param mac          Device MAC address
 * @param name         Device display name
 * @param fw_version   Firmware version string
 * @return             AnnounceResponse with status and endpoints if configured
 */
AnnounceResponse http_announce(const char* ha_url, const char* mac,
                               const char* name, const char* fw_version);

/**
 * Check if calendar has changed using ETag
 *
 * @param ha_url       Home Assistant base URL
 * @param check_path   Check endpoint path (from announce response)
 * @param current_etag Current stored ETag (empty string if none)
 * @param mac          Device MAC address (for X-MAC header)
 * @return             FETCH_OK if changed, FETCH_NOT_MODIFIED if same, FETCH_ERROR on failure
 */
FetchResponse http_check_calendar(const char* ha_url, const char* check_path,
                                  const char* current_etag, const char* mac);

/**
 * Fetch a bitmap chunk from the server
 *
 * @param ha_url       Home Assistant base URL
 * @param endpoint     Endpoint path (from announce response)
 * @param current_etag Current stored ETag (send as If-None-Match)
 * @param mac          Device MAC address (for X-MAC header)
 * @param buffer       Buffer to store downloaded data
 * @param buffer_size  Size of buffer
 * @return             FetchResponse with result and new ETag if applicable
 */
FetchResponse http_fetch_chunk(
  const char* ha_url,
  const char* endpoint,
  const char* current_etag,
  const char* mac,
  uint8_t* buffer,
  size_t buffer_size
);

#endif // EINK_CALENDAR_HTTP_CLIENT_H
