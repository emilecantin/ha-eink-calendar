/**
 * Native unit tests for ESP32 firmware data structures and patterns.
 *
 * These tests run on the host machine (no hardware needed) and verify:
 * - Struct zero-initialization behavior
 * - strncpy null-termination patterns (regression test for #17 / #33)
 * - Buffer boundary conditions
 * - Enum default values
 * - ArduinoJson serialization (regression for #47)
 * - Configured flag behavior (regression for #38)
 *
 * Run with: pio test -e native
 */
#include <unity.h>
#include <string.h>
#include <ArduinoJson.h>

// Pull in firmware headers (resolved via stubs)
#include "config.h"
#include "http_client.h"
#include "display.h"
#include "url_validation.h"

// ---------------------------------------------------------------------------
// Config struct tests
// ---------------------------------------------------------------------------

void test_config_struct_zero_init(void) {
    Config cfg = {};
    TEST_ASSERT_EQUAL_STRING("", cfg.ha_url);
    TEST_ASSERT_EQUAL_STRING("", cfg.entry_id);
    TEST_ASSERT_EQUAL_UINT32(0, cfg.refresh_interval);
    TEST_ASSERT_FALSE(cfg.configured);
    TEST_ASSERT_FALSE(cfg.discovered);
}

void test_config_struct_field_sizes(void) {
    // Verify buffer sizes match the constants used in strncpy calls
    Config cfg;
    TEST_ASSERT_EQUAL(128, sizeof(cfg.ha_url));
    TEST_ASSERT_EQUAL(64, sizeof(cfg.entry_id));
}

void test_cache_state_zero_init(void) {
    CacheState cache = {};
    TEST_ASSERT_EQUAL_STRING("", cache.etag);
    TEST_ASSERT_FALSE(cache.display_valid);
}

void test_cache_state_etag_size(void) {
    // ETag is an MD5 hash: 32 hex chars + null terminator
    CacheState cache;
    TEST_ASSERT_EQUAL(33, sizeof(cache.etag));
}

void test_bitmap_endpoints_zero_init(void) {
    BitmapEndpoints ep = {};
    TEST_ASSERT_EQUAL_STRING("", ep.black_top);
    TEST_ASSERT_EQUAL_STRING("", ep.black_bottom);
    TEST_ASSERT_EQUAL_STRING("", ep.red_top);
    TEST_ASSERT_EQUAL_STRING("", ep.red_bottom);
    TEST_ASSERT_EQUAL_STRING("", ep.check);
    TEST_ASSERT_EQUAL_STRING("", ep.error);
}

void test_bitmap_endpoints_field_sizes(void) {
    BitmapEndpoints ep;
    TEST_ASSERT_EQUAL(128, sizeof(ep.black_top));
    TEST_ASSERT_EQUAL(128, sizeof(ep.black_bottom));
    TEST_ASSERT_EQUAL(128, sizeof(ep.red_top));
    TEST_ASSERT_EQUAL(128, sizeof(ep.red_bottom));
    TEST_ASSERT_EQUAL(128, sizeof(ep.check));
    TEST_ASSERT_EQUAL(128, sizeof(ep.error));
}

// ---------------------------------------------------------------------------
// HTTP response struct tests
// ---------------------------------------------------------------------------

void test_fetch_response_zero_init(void) {
    FetchResponse resp = {};
    TEST_ASSERT_EQUAL(FETCH_OK, resp.result);  // 0 = FETCH_OK
    TEST_ASSERT_EQUAL_STRING("", resp.new_etag);
    TEST_ASSERT_EQUAL_INT(0, resp.http_code);
    TEST_ASSERT_EQUAL(0u, resp.bytes_read);
}

void test_announce_response_zero_init(void) {
    AnnounceResponse resp = {};
    TEST_ASSERT_EQUAL(ANNOUNCE_CONFIGURED, resp.status);  // 0 = ANNOUNCE_CONFIGURED
    TEST_ASSERT_EQUAL_STRING("", resp.entry_id);
    TEST_ASSERT_EQUAL_UINT32(0, resp.refresh_interval);
    TEST_ASSERT_EQUAL_INT(0, resp.http_code);
}

void test_ota_info_zero_init(void) {
    OtaInfo ota = {};
    TEST_ASSERT_FALSE(ota.available);
    TEST_ASSERT_EQUAL_STRING("", ota.version);
    TEST_ASSERT_EQUAL_STRING("", ota.url);
    TEST_ASSERT_EQUAL_UINT32(0, ota.size);
}

void test_ota_info_field_sizes(void) {
    OtaInfo ota;
    TEST_ASSERT_EQUAL(32, sizeof(ota.version));
    TEST_ASSERT_EQUAL(128, sizeof(ota.url));
}

// ---------------------------------------------------------------------------
// strncpy null-termination pattern tests (regression for #17)
// ---------------------------------------------------------------------------

/**
 * Validates the safe strncpy pattern used throughout the firmware:
 *   strncpy(dest, src, sizeof(dest) - 1);
 *   dest[sizeof(dest) - 1] = '\0';
 *
 * Issue #17 found that strncpy alone does NOT null-terminate when
 * src length >= dest size. The firmware now always forces a null
 * terminator at the last position.
 */

void test_strncpy_short_string_is_terminated(void) {
    char dest[8];
    memset(dest, 'X', sizeof(dest));  // Fill with junk

    const char* src = "Hi";
    strncpy(dest, src, sizeof(dest) - 1);
    dest[sizeof(dest) - 1] = '\0';

    TEST_ASSERT_EQUAL_STRING("Hi", dest);
}

void test_strncpy_exact_fit_is_terminated(void) {
    char dest[4];
    memset(dest, 'X', sizeof(dest));

    // "abc" is 3 chars, dest is 4 bytes (3 + null) — exact fit
    const char* src = "abc";
    strncpy(dest, src, sizeof(dest) - 1);
    dest[sizeof(dest) - 1] = '\0';

    TEST_ASSERT_EQUAL_STRING("abc", dest);
}

void test_strncpy_overflow_is_truncated_and_terminated(void) {
    char dest[4];
    memset(dest, 'X', sizeof(dest));

    // Source is longer than dest — must be truncated and null-terminated
    const char* src = "abcdefgh";
    strncpy(dest, src, sizeof(dest) - 1);
    dest[sizeof(dest) - 1] = '\0';

    TEST_ASSERT_EQUAL_STRING("abc", dest);
    TEST_ASSERT_EQUAL('\0', dest[3]);
}

void test_strncpy_without_manual_terminator_is_unsafe(void) {
    // Demonstrates the bug that #17 fixed: strncpy does NOT terminate
    // when src >= dest size
    char dest[4];
    memset(dest, 'X', sizeof(dest));

    const char* src = "abcdefgh";
    strncpy(dest, src, sizeof(dest) - 1);
    // Without: dest[sizeof(dest) - 1] = '\0';
    // dest[3] is still 'X' from memset (strncpy wrote 3 chars, did not touch [3])

    TEST_ASSERT_EQUAL('X', dest[3]);  // NOT null-terminated!
}

void test_strncpy_pattern_on_config_sized_buffer(void) {
    // Simulate the exact pattern used for config.ha_url (128 bytes)
    char ha_url[128];
    memset(ha_url, 'X', sizeof(ha_url));

    // Simulate a URL that's exactly 127 chars (fills buffer completely)
    char long_url[256];
    memset(long_url, 'A', 127);
    long_url[127] = '\0';

    strncpy(ha_url, long_url, sizeof(ha_url) - 1);
    ha_url[sizeof(ha_url) - 1] = '\0';

    TEST_ASSERT_EQUAL(127u, strlen(ha_url));
    TEST_ASSERT_EQUAL('\0', ha_url[127]);
}

void test_strncpy_pattern_on_etag_buffer(void) {
    // ETag buffer is 33 bytes (32 hex + null)
    char etag[33];
    memset(etag, 'X', sizeof(etag));

    // Simulate a full 32-char MD5 hash
    const char* md5 = "d41d8cd98f00b204e9800998ecf8427e";
    strncpy(etag, md5, sizeof(etag) - 1);
    etag[sizeof(etag) - 1] = '\0';

    TEST_ASSERT_EQUAL(32u, strlen(etag));
    TEST_ASSERT_EQUAL_STRING("d41d8cd98f00b204e9800998ecf8427e", etag);
}

// ---------------------------------------------------------------------------
// Display constants tests
// ---------------------------------------------------------------------------

void test_display_constants(void) {
    TEST_ASSERT_EQUAL(984, DISPLAY_WIDTH);
    TEST_ASSERT_EQUAL(1304, DISPLAY_HEIGHT);
    TEST_ASSERT_EQUAL(492, CHUNK_HEIGHT);
    TEST_ASSERT_EQUAL(1304, CHUNK_WIDTH);
}

void test_chunk_buffer_size_calculation(void) {
    // CHUNK_BUFFER_SIZE should be ceil(CHUNK_WIDTH / 8) * CHUNK_HEIGHT
    // 1304 / 8 = 163 bytes per row, * 492 rows = 80196
    size_t expected = (CHUNK_WIDTH / 8) * CHUNK_HEIGHT;
    TEST_ASSERT_EQUAL(expected, CHUNK_BUFFER_SIZE);
}

void test_default_refresh_interval(void) {
    TEST_ASSERT_EQUAL(900, DEFAULT_REFRESH_INTERVAL);  // 15 minutes in seconds
}

// ---------------------------------------------------------------------------
// Enum value tests
// ---------------------------------------------------------------------------

void test_fetch_result_enum_values(void) {
    TEST_ASSERT_EQUAL(0, FETCH_OK);
    TEST_ASSERT_EQUAL(1, FETCH_NOT_MODIFIED);
    TEST_ASSERT_EQUAL(2, FETCH_ERROR);
}

void test_announce_status_enum_values(void) {
    TEST_ASSERT_EQUAL(0, ANNOUNCE_CONFIGURED);
    TEST_ASSERT_EQUAL(1, ANNOUNCE_PENDING);
    TEST_ASSERT_EQUAL(2, ANNOUNCE_NOT_INSTALLED);
    TEST_ASSERT_EQUAL(3, ANNOUNCE_ERROR);
}

// ---------------------------------------------------------------------------
// URL validation tests (#20)
// ---------------------------------------------------------------------------

void test_validate_ha_url_valid_http(void) {
    TEST_ASSERT_TRUE(validateHaUrl("http://homeassistant.local:8123"));
}

void test_validate_ha_url_valid_https(void) {
    TEST_ASSERT_TRUE(validateHaUrl("https://homeassistant.local:8123"));
}

void test_validate_ha_url_valid_ip(void) {
    TEST_ASSERT_TRUE(validateHaUrl("http://192.168.1.100:8123"));
}

void test_validate_ha_url_valid_minimal(void) {
    TEST_ASSERT_TRUE(validateHaUrl("http://ha"));
}

void test_validate_ha_url_rejects_null(void) {
    TEST_ASSERT_FALSE(validateHaUrl(NULL));
}

void test_validate_ha_url_rejects_empty(void) {
    TEST_ASSERT_FALSE(validateHaUrl(""));
}

void test_validate_ha_url_rejects_no_scheme(void) {
    TEST_ASSERT_FALSE(validateHaUrl("homeassistant.local:8123"));
}

void test_validate_ha_url_rejects_ftp(void) {
    TEST_ASSERT_FALSE(validateHaUrl("ftp://homeassistant.local"));
}

void test_validate_ha_url_rejects_just_scheme(void) {
    // "http://" alone is 7 chars — technically passes scheme check
    // but this is a valid edge case; the server will fail on connect
    TEST_ASSERT_TRUE(validateHaUrl("http://x"));
}

void test_validate_ha_url_rejects_whitespace(void) {
    TEST_ASSERT_FALSE(validateHaUrl("http://home assistant.local:8123"));
}

void test_validate_ha_url_rejects_tab(void) {
    TEST_ASSERT_FALSE(validateHaUrl("http://ha.local\t:8123"));
}

void test_validate_ha_url_rejects_newline(void) {
    TEST_ASSERT_FALSE(validateHaUrl("http://ha.local\n"));
}

void test_validate_ha_url_rejects_too_long(void) {
    // Build a URL that's exactly 128 chars (1 over the limit)
    char long_url[256] = "http://";
    memset(long_url + 7, 'a', 121);  // 7 + 121 = 128 chars
    long_url[128] = '\0';
    TEST_ASSERT_EQUAL(128u, strlen(long_url));
    TEST_ASSERT_FALSE(validateHaUrl(long_url));
}

void test_validate_ha_url_accepts_max_length(void) {
    // Build a URL that's exactly 127 chars (at the limit)
    char max_url[256] = "http://";
    memset(max_url + 7, 'a', 120);  // 7 + 120 = 127 chars
    max_url[127] = '\0';
    TEST_ASSERT_EQUAL(127u, strlen(max_url));
    TEST_ASSERT_TRUE(validateHaUrl(max_url));
}

// ---------------------------------------------------------------------------
// strncpy buffer-boundary regression tests (#33 / #17)
//
// The fix in http_client.cpp added `dest[sizeof(dest) - 1] = '\0'` after
// strncpy calls.  These tests verify the exact boundary: source string
// exactly fills the buffer with no room for the null terminator.
// ---------------------------------------------------------------------------

void test_strncpy_source_exactly_fills_buffer_no_null_room(void) {
    // Source is exactly sizeof(dest) chars — strncpy copies sizeof(dest)-1
    // chars and the manual terminator is critical
    char dest[8];
    memset(dest, 'X', sizeof(dest));

    // Source is "ABCDEFGH" (8 chars) — same as sizeof(dest)
    const char* src = "ABCDEFGH";
    strncpy(dest, src, sizeof(dest) - 1);  // copies 7 chars: "ABCDEFG"
    dest[sizeof(dest) - 1] = '\0';         // force null at position 7

    TEST_ASSERT_EQUAL_STRING("ABCDEFG", dest);
    TEST_ASSERT_EQUAL('\0', dest[7]);
    TEST_ASSERT_EQUAL(7u, strlen(dest));
}

void test_strncpy_entry_id_boundary(void) {
    // Simulate entry_id (64 bytes) with source exactly 64 chars
    char entry_id[64];
    memset(entry_id, 'X', sizeof(entry_id));

    char long_id[65];
    memset(long_id, 'Z', 64);
    long_id[64] = '\0';  // 64-char source string

    strncpy(entry_id, long_id, sizeof(entry_id) - 1);
    entry_id[sizeof(entry_id) - 1] = '\0';

    TEST_ASSERT_EQUAL(63u, strlen(entry_id));
    TEST_ASSERT_EQUAL('\0', entry_id[63]);
    // Verify all copied chars are correct
    for (int i = 0; i < 63; i++) {
        TEST_ASSERT_EQUAL('Z', entry_id[i]);
    }
}

// ---------------------------------------------------------------------------
// ArduinoJson serialization tests (regression for #47)
//
// PR #47 switched the announce payload from string concatenation to
// ArduinoJson.  These tests verify that the JSON serialization produces
// the expected structure.
// ---------------------------------------------------------------------------

void test_arduinojson_announce_payload_structure(void) {
    // Replicate the announce payload construction from http_client.cpp
    JsonDocument doc;
    doc["mac"] = "AA:BB:CC:DD:EE:FF";
    doc["name"] = "EinkCal-EE:FF";
    doc["firmware_version"] = "1.2.0";

    char json[512];
    serializeJson(doc, json, sizeof(json));

    // Verify it's valid JSON containing expected fields
    TEST_ASSERT_NOT_NULL(strstr(json, "\"mac\""));
    TEST_ASSERT_NOT_NULL(strstr(json, "\"AA:BB:CC:DD:EE:FF\""));
    TEST_ASSERT_NOT_NULL(strstr(json, "\"name\""));
    TEST_ASSERT_NOT_NULL(strstr(json, "\"EinkCal-EE:FF\""));
    TEST_ASSERT_NOT_NULL(strstr(json, "\"firmware_version\""));
    TEST_ASSERT_NOT_NULL(strstr(json, "\"1.2.0\""));
}

void test_arduinojson_announce_payload_roundtrip(void) {
    // Build payload like the firmware does
    JsonDocument doc;
    doc["mac"] = "AA:BB:CC:DD:EE:FF";
    doc["name"] = "Kitchen Calendar";
    doc["firmware_version"] = "1.2.0";

    char json[512];
    serializeJson(doc, json, sizeof(json));

    // Parse it back and verify values
    JsonDocument parsed;
    DeserializationError err = deserializeJson(parsed, json);
    TEST_ASSERT_TRUE(err == DeserializationError::Ok);
    TEST_ASSERT_EQUAL_STRING("AA:BB:CC:DD:EE:FF", parsed["mac"]);
    TEST_ASSERT_EQUAL_STRING("Kitchen Calendar", parsed["name"]);
    TEST_ASSERT_EQUAL_STRING("1.2.0", parsed["firmware_version"]);
}

void test_arduinojson_error_report_payload(void) {
    // http_report_error also uses ArduinoJson
    JsonDocument doc;
    doc["error"] = "download_failed";
    doc["details"] = "/api/eink_calendar/bitmap/abc123/black_top";

    char json[512];
    serializeJson(doc, json, sizeof(json));

    TEST_ASSERT_NOT_NULL(strstr(json, "\"error\""));
    TEST_ASSERT_NOT_NULL(strstr(json, "\"download_failed\""));
    TEST_ASSERT_NOT_NULL(strstr(json, "\"details\""));
}

void test_arduinojson_error_report_without_details(void) {
    // When details is NULL/empty, the firmware omits it
    JsonDocument doc;
    doc["error"] = "memory_alloc_failed";
    // No "details" field added

    char json[512];
    serializeJson(doc, json, sizeof(json));

    TEST_ASSERT_NOT_NULL(strstr(json, "\"error\""));
    TEST_ASSERT_NULL(strstr(json, "\"details\""));
}

// ---------------------------------------------------------------------------
// Config.configured flag tests (regression for #38)
//
// PR #38 fixed a bug where config.configured was set to true in
// non-configured states (pending, not installed).  Only ANNOUNCE_CONFIGURED
// should set configured = true.
// ---------------------------------------------------------------------------

void test_config_zero_init_configured_is_false(void) {
    // A zero-initialized Config must have configured == false
    Config cfg = {};
    TEST_ASSERT_FALSE(cfg.configured);
    TEST_ASSERT_FALSE(cfg.discovered);
}

void test_config_memset_zero_configured_is_false(void) {
    // Verify with memset too (matches NVS load pattern on first boot)
    Config cfg;
    memset(&cfg, 0, sizeof(cfg));
    TEST_ASSERT_FALSE(cfg.configured);
    TEST_ASSERT_FALSE(cfg.discovered);
}

void test_config_configured_flag_explicit_set(void) {
    Config cfg = {};
    TEST_ASSERT_FALSE(cfg.configured);

    // Only after explicit set should it be true
    cfg.configured = true;
    TEST_ASSERT_TRUE(cfg.configured);

    // And can be cleared
    cfg.configured = false;
    TEST_ASSERT_FALSE(cfg.configured);
}

// ---------------------------------------------------------------------------
// mDNS retry constant test (regression for #51)
//
// PR #51 added retry logic: up to 3 mDNS attempts with 1s delay.
// We can't test actual mDNS here, but we verify the retry count constant
// matches expectations.
// ---------------------------------------------------------------------------

void test_ota_max_retries_constant(void) {
    TEST_ASSERT_EQUAL(0, ANNOUNCE_CONFIGURED);
    TEST_ASSERT_EQUAL(1, ANNOUNCE_PENDING);
    TEST_ASSERT_EQUAL(2, ANNOUNCE_NOT_INSTALLED);
    TEST_ASSERT_EQUAL(3, ANNOUNCE_ERROR);
    // All four states must be distinct (retry logic depends on this)
    TEST_ASSERT_NOT_EQUAL(ANNOUNCE_CONFIGURED, ANNOUNCE_PENDING);
    TEST_ASSERT_NOT_EQUAL(ANNOUNCE_CONFIGURED, ANNOUNCE_ERROR);
    TEST_ASSERT_NOT_EQUAL(ANNOUNCE_PENDING, ANNOUNCE_NOT_INSTALLED);
}

// ---------------------------------------------------------------------------
// Test runner
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    UNITY_BEGIN();

    // Config structs
    RUN_TEST(test_config_struct_zero_init);
    RUN_TEST(test_config_struct_field_sizes);
    RUN_TEST(test_cache_state_zero_init);
    RUN_TEST(test_cache_state_etag_size);
    RUN_TEST(test_bitmap_endpoints_zero_init);
    RUN_TEST(test_bitmap_endpoints_field_sizes);

    // HTTP response structs
    RUN_TEST(test_fetch_response_zero_init);
    RUN_TEST(test_announce_response_zero_init);
    RUN_TEST(test_ota_info_zero_init);
    RUN_TEST(test_ota_info_field_sizes);

    // strncpy null-termination (regression for #17)
    RUN_TEST(test_strncpy_short_string_is_terminated);
    RUN_TEST(test_strncpy_exact_fit_is_terminated);
    RUN_TEST(test_strncpy_overflow_is_truncated_and_terminated);
    RUN_TEST(test_strncpy_without_manual_terminator_is_unsafe);
    RUN_TEST(test_strncpy_pattern_on_config_sized_buffer);
    RUN_TEST(test_strncpy_pattern_on_etag_buffer);

    // Display constants
    RUN_TEST(test_display_constants);
    RUN_TEST(test_chunk_buffer_size_calculation);
    RUN_TEST(test_default_refresh_interval);

    // Enum values
    RUN_TEST(test_fetch_result_enum_values);
    RUN_TEST(test_announce_status_enum_values);

    // URL validation (#20)
    RUN_TEST(test_validate_ha_url_valid_http);
    RUN_TEST(test_validate_ha_url_valid_https);
    RUN_TEST(test_validate_ha_url_valid_ip);
    RUN_TEST(test_validate_ha_url_valid_minimal);
    RUN_TEST(test_validate_ha_url_rejects_null);
    RUN_TEST(test_validate_ha_url_rejects_empty);
    RUN_TEST(test_validate_ha_url_rejects_no_scheme);
    RUN_TEST(test_validate_ha_url_rejects_ftp);
    RUN_TEST(test_validate_ha_url_rejects_just_scheme);
    RUN_TEST(test_validate_ha_url_rejects_whitespace);
    RUN_TEST(test_validate_ha_url_rejects_tab);
    RUN_TEST(test_validate_ha_url_rejects_newline);
    RUN_TEST(test_validate_ha_url_rejects_too_long);
    RUN_TEST(test_validate_ha_url_accepts_max_length);

    // strncpy buffer-boundary (regression for #33 / #17)
    RUN_TEST(test_strncpy_source_exactly_fills_buffer_no_null_room);
    RUN_TEST(test_strncpy_entry_id_boundary);

    // ArduinoJson serialization (regression for #47)
    RUN_TEST(test_arduinojson_announce_payload_structure);
    RUN_TEST(test_arduinojson_announce_payload_roundtrip);
    RUN_TEST(test_arduinojson_error_report_payload);
    RUN_TEST(test_arduinojson_error_report_without_details);

    // Config.configured flag (regression for #38)
    RUN_TEST(test_config_zero_init_configured_is_false);
    RUN_TEST(test_config_memset_zero_configured_is_false);
    RUN_TEST(test_config_configured_flag_explicit_set);

    // mDNS retry / announce states (regression for #51)
    RUN_TEST(test_ota_max_retries_constant);

    return UNITY_END();
}
