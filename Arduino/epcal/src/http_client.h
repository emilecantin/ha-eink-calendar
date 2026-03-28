#ifndef EINK_CALENDAR_HTTP_CLIENT_H
#define EINK_CALENDAR_HTTP_CLIENT_H

#include <Arduino.h>
#include "config.h"

// OTA download buffer size (heap-allocated, must be power of 2 for flash alignment)
#define OTA_BUFFER_SIZE 4096

// Result of a fetch operation
enum FetchResult {
  FETCH_OK,            // 200 - new content downloaded
  FETCH_NOT_MODIFIED,  // 304 - content unchanged
  FETCH_ERROR          // Network or server error
};

// OTA firmware update info (from announce or check response)
struct OtaInfo {
  bool available;
  char version[32];
  char url[128];
  uint32_t size;
};

// Response from fetch operation
struct FetchResponse {
  FetchResult result;
  char new_etag[33];   // ETag from response (if 200)
  int http_code;       // HTTP status code
  size_t bytes_read;   // Number of bytes downloaded
  int refresh_interval; // From X-Refresh-Interval header (-1 if absent)
  OtaInfo ota;         // OTA info from check response headers
};

// Announce status
enum AnnounceStatus {
  ANNOUNCE_CONFIGURED,      // Device is configured, endpoints returned
  ANNOUNCE_PENDING,         // Waiting for user to configure in HA
  ANNOUNCE_NOT_INSTALLED,   // HA found but integration not installed (404)
  ANNOUNCE_ERROR            // Error communicating with HA
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
 * Sync device state with Home Assistant.
 * Sends current ETag and firmware version; HA responds with what needs updating.
 *
 * @param ha_url       Home Assistant base URL
 * @param check_path   Check endpoint path (from announce response)
 * @param current_etag Current stored ETag (empty string if none)
 * @param mac          Device MAC address (for X-MAC header)
 * @param fw_version   Current firmware version (for OTA check)
 * @return             FetchResponse with image/OTA/refresh info
 */
FetchResponse http_check_calendar(const char* ha_url, const char* check_path,
                                  const char* current_etag, const char* mac,
                                  const char* fw_version);

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

/**
 * Download and flash OTA firmware update.
 * On success, calls ESP.restart() and never returns.
 *
 * @param ha_url         Home Assistant base URL
 * @param ota_path       Firmware endpoint path (from OtaInfo.url)
 * @param mac            Device MAC address (for X-MAC header)
 * @param expected_size  Expected firmware size in bytes (from OtaInfo.size)
 * @return               false on error (true never returned — success reboots)
 */
bool http_ota_update(const char* ha_url, const char* ota_path,
                     const char* mac, uint32_t expected_size);

/**
 * Report an error to Home Assistant.
 * Fire-and-forget — errors during reporting are silently ignored.
 *
 * @param ha_url       Home Assistant base URL
 * @param error_path   Error endpoint path (from announce response)
 * @param mac          Device MAC address (for X-MAC header)
 * @param error        Short error description (e.g., "display_refresh_failed")
 * @param details      Optional details string (can be NULL)
 */
void http_report_error(const char* ha_url, const char* error_path,
                       const char* mac, const char* error,
                       const char* details);

#endif // EINK_CALENDAR_HTTP_CLIENT_H
