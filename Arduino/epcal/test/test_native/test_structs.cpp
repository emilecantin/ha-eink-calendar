/**
 * Native unit tests for ESP32 firmware data structures and patterns.
 *
 * These tests run on the host machine (no hardware needed) and verify:
 * - Struct zero-initialization behavior
 * - strncpy null-termination patterns (regression test for #17)
 * - Buffer boundary conditions
 * - Enum default values
 *
 * Run with: pio test -e native
 */
#include <unity.h>
#include <cstring>

// Pull in firmware headers (resolved via stubs)
#include "config.h"
#include "http_client.h"
#include "display.h"

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

    return UNITY_END();
}
