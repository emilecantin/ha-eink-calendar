/**
 * Native unit tests for boot diagnostics (diagnostics.h).
 *
 * The stage and reset-reason names are the contract between the firmware and
 * the Home Assistant integration: they arrive as X-Last-Stage / X-Reset-Reason
 * headers and are matched against BOOT_STAGES in device_diagnostics.py. A typo
 * here silently degrades the diagnosis, so the mappings are pinned.
 *
 * Run with: pio test -e native
 */
#include <unity.h>
#include <string.h>

#include "diagnostics.h"

void setUp(void) {}
void tearDown(void) {}

// --- Stage names ---

void test_stage_names_match_ha_contract(void) {
    TEST_ASSERT_EQUAL_STRING("boot", diag_stage_name(STAGE_BOOT));
    TEST_ASSERT_EQUAL_STRING("wifi_connected", diag_stage_name(STAGE_WIFI_CONNECTED));
    TEST_ASSERT_EQUAL_STRING("announced", diag_stage_name(STAGE_ANNOUNCED));
    TEST_ASSERT_EQUAL_STRING("checked", diag_stage_name(STAGE_CHECKED));
    TEST_ASSERT_EQUAL_STRING("downloaded", diag_stage_name(STAGE_DOWNLOADED));
    TEST_ASSERT_EQUAL_STRING("display_init", diag_stage_name(STAGE_DISPLAY_INIT));
    TEST_ASSERT_EQUAL_STRING("display_sent", diag_stage_name(STAGE_DISPLAY_SENT));
    TEST_ASSERT_EQUAL_STRING("display_refreshed", diag_stage_name(STAGE_DISPLAY_REFRESHED));
    TEST_ASSERT_EQUAL_STRING("sleeping", diag_stage_name(STAGE_SLEEPING));
}

void test_stage_ordering_is_monotonic(void) {
    // HA compares stage positions to decide whether the display refresh
    // completed, so the progression must stay ordered.
    TEST_ASSERT_TRUE(STAGE_BOOT < STAGE_WIFI_CONNECTED);
    TEST_ASSERT_TRUE(STAGE_WIFI_CONNECTED < STAGE_ANNOUNCED);
    TEST_ASSERT_TRUE(STAGE_ANNOUNCED < STAGE_CHECKED);
    TEST_ASSERT_TRUE(STAGE_CHECKED < STAGE_DOWNLOADED);
    TEST_ASSERT_TRUE(STAGE_DOWNLOADED < STAGE_DISPLAY_INIT);
    TEST_ASSERT_TRUE(STAGE_DISPLAY_INIT < STAGE_DISPLAY_SENT);
    TEST_ASSERT_TRUE(STAGE_DISPLAY_SENT < STAGE_DISPLAY_REFRESHED);
    TEST_ASSERT_TRUE(STAGE_DISPLAY_REFRESHED < STAGE_SLEEPING);
}

void test_out_of_range_stage_is_unknown(void) {
    // A hard brownout can leave RTC memory holding garbage; setup() bounds-checks
    // it, but the name lookup must not read past the table either.
    TEST_ASSERT_EQUAL_STRING("unknown", diag_stage_name(200));
    TEST_ASSERT_EQUAL_STRING("unknown", diag_stage_name(STAGE_SLEEPING + 1));
}

// --- Reset reasons ---

void test_reset_reason_names(void) {
    TEST_ASSERT_EQUAL_STRING("poweron", diag_reset_reason_name(ESP_RST_POWERON));
    TEST_ASSERT_EQUAL_STRING("deepsleep", diag_reset_reason_name(ESP_RST_DEEPSLEEP));
    TEST_ASSERT_EQUAL_STRING("brownout", diag_reset_reason_name(ESP_RST_BROWNOUT));
    TEST_ASSERT_EQUAL_STRING("panic", diag_reset_reason_name(ESP_RST_PANIC));
    TEST_ASSERT_EQUAL_STRING("task_wdt", diag_reset_reason_name(ESP_RST_TASK_WDT));
    TEST_ASSERT_EQUAL_STRING("int_wdt", diag_reset_reason_name(ESP_RST_INT_WDT));
    TEST_ASSERT_EQUAL_STRING("other_wdt", diag_reset_reason_name(ESP_RST_WDT));
    TEST_ASSERT_EQUAL_STRING("software", diag_reset_reason_name(ESP_RST_SW));
    TEST_ASSERT_EQUAL_STRING("external", diag_reset_reason_name(ESP_RST_EXT));
    TEST_ASSERT_EQUAL_STRING("sdio", diag_reset_reason_name(ESP_RST_SDIO));
}

void test_unknown_reset_reason(void) {
    TEST_ASSERT_EQUAL_STRING("unknown", diag_reset_reason_name(ESP_RST_UNKNOWN));
}

void test_fault_reset_reasons_are_distinguishable(void) {
    // The whole point of shipping this: a brownout must not look like a
    // normal deep-sleep wake.
    TEST_ASSERT_NOT_EQUAL(0, strcmp(diag_reset_reason_name(ESP_RST_BROWNOUT),
                                    diag_reset_reason_name(ESP_RST_DEEPSLEEP)));
    TEST_ASSERT_NOT_EQUAL(0, strcmp(diag_reset_reason_name(ESP_RST_TASK_WDT),
                                    diag_reset_reason_name(ESP_RST_PANIC)));
}

// --- Diagnostics struct ---

void test_diagnostics_struct_zero_init(void) {
    DeviceDiagnostics diag = {};
    TEST_ASSERT_NULL(diag.reset_reason);
    TEST_ASSERT_NULL(diag.last_stage);
    TEST_ASSERT_EQUAL_UINT32(0, diag.boot_count);
    TEST_ASSERT_EQUAL_UINT32(0, diag.free_heap);
    TEST_ASSERT_EQUAL_UINT32(0, diag.last_sleep_s);
}

void test_diagnostics_struct_holds_static_names(void) {
    // The names come from static string tables, so the struct can hold plain
    // pointers without copying — verify they stay valid after assignment.
    DeviceDiagnostics diag = {};
    diag.reset_reason = diag_reset_reason_name(ESP_RST_BROWNOUT);
    diag.last_stage = diag_stage_name(STAGE_DISPLAY_SENT);
    diag.boot_count = 42;

    TEST_ASSERT_EQUAL_STRING("brownout", diag.reset_reason);
    TEST_ASSERT_EQUAL_STRING("display_sent", diag.last_stage);
    TEST_ASSERT_EQUAL_UINT32(42, diag.boot_count);
}

int main(int argc, char** argv) {
    UNITY_BEGIN();

    RUN_TEST(test_stage_names_match_ha_contract);
    RUN_TEST(test_stage_ordering_is_monotonic);
    RUN_TEST(test_out_of_range_stage_is_unknown);

    RUN_TEST(test_reset_reason_names);
    RUN_TEST(test_unknown_reset_reason);
    RUN_TEST(test_fault_reset_reasons_are_distinguishable);

    RUN_TEST(test_diagnostics_struct_zero_init);
    RUN_TEST(test_diagnostics_struct_holds_static_names);

    return UNITY_END();
}
