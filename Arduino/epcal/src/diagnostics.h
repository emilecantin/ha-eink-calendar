#ifndef EINK_CALENDAR_DIAGNOSTICS_H
#define EINK_CALENDAR_DIAGNOSTICS_H

#include <Arduino.h>
#include <esp_system.h>

/**
 * Boot stage markers.
 *
 * The current stage is written to RTC memory as a boot progresses. If the
 * device resets unexpectedly (brownout, watchdog, panic), the *next* boot
 * reports how far the previous one got.
 *
 * This is the only visibility we have into the window between the WiFi
 * shutdown (see updateCalendar) and deep sleep, where the display refresh
 * happens and the device physically cannot report errors over the network.
 *
 * Values are ordered by progression: a higher value means the boot got further.
 */
enum BootStage : uint8_t {
  STAGE_BOOT = 0,
  STAGE_WIFI_CONNECTED,
  STAGE_ANNOUNCED,
  STAGE_CHECKED,
  STAGE_DOWNLOADED,
  STAGE_DISPLAY_INIT,
  STAGE_DISPLAY_SENT,
  STAGE_DISPLAY_REFRESHED,
  STAGE_SLEEPING,
};

inline const char* diag_stage_name(uint8_t stage) {
  switch (stage) {
    case STAGE_BOOT:              return "boot";
    case STAGE_WIFI_CONNECTED:    return "wifi_connected";
    case STAGE_ANNOUNCED:         return "announced";
    case STAGE_CHECKED:           return "checked";
    case STAGE_DOWNLOADED:        return "downloaded";
    case STAGE_DISPLAY_INIT:      return "display_init";
    case STAGE_DISPLAY_SENT:      return "display_sent";
    case STAGE_DISPLAY_REFRESHED: return "display_refreshed";
    case STAGE_SLEEPING:          return "sleeping";
    default:                      return "unknown";
  }
}

inline const char* diag_reset_reason_name(esp_reset_reason_t reason) {
  switch (reason) {
    case ESP_RST_POWERON:   return "poweron";
    case ESP_RST_EXT:       return "external";
    case ESP_RST_SW:        return "software";
    case ESP_RST_PANIC:     return "panic";
    case ESP_RST_INT_WDT:   return "int_wdt";
    case ESP_RST_TASK_WDT:  return "task_wdt";
    case ESP_RST_WDT:       return "other_wdt";
    case ESP_RST_DEEPSLEEP: return "deepsleep";
    case ESP_RST_BROWNOUT:  return "brownout";
    case ESP_RST_SDIO:      return "sdio";
    default:                return "unknown";
  }
}

/**
 * Snapshot of device health, sent to Home Assistant as headers on each
 * check-in so a reboot loop can be diagnosed without a serial cable.
 */
struct DeviceDiagnostics {
  const char* reset_reason;  // Why the ESP32 last reset
  const char* last_stage;    // Furthest stage the *previous* boot reached
  uint32_t boot_count;       // Boots since the last power-on
  uint32_t free_heap;        // Free heap at check-in time
  uint32_t last_sleep_s;     // Length of the sleep that preceded this boot
  // Whether the device believes the panel currently matches its stored ETag.
  // Only ever set true after a completed display_refresh(), so a device that
  // has never finished a refresh reports false — which distinguishes
  // "never worked" from "worked once, broke later".
  bool display_valid;
};

#endif  // EINK_CALENDAR_DIAGNOSTICS_H
