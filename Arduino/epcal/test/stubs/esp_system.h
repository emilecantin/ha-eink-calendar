/**
 * Minimal esp_system.h stub for native unit tests.
 */
#ifndef ESP_SYSTEM_H_STUB
#define ESP_SYSTEM_H_STUB

#include <stdint.h>

typedef enum {
    ESP_RST_UNKNOWN = 0,
    ESP_RST_POWERON,
    ESP_RST_EXT,
    ESP_RST_SW,
    ESP_RST_PANIC,
    ESP_RST_INT_WDT,
    ESP_RST_TASK_WDT,
    ESP_RST_WDT,
    ESP_RST_DEEPSLEEP,
    ESP_RST_BROWNOUT,
    ESP_RST_SDIO,
} esp_reset_reason_t;

inline esp_reset_reason_t esp_reset_reason() { return ESP_RST_POWERON; }

#endif // ESP_SYSTEM_H_STUB
