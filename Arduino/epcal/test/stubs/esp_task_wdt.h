/**
 * Minimal esp_task_wdt.h stub for native unit tests.
 */
#ifndef ESP_TASK_WDT_H_STUB
#define ESP_TASK_WDT_H_STUB

#include <stdint.h>
#include <stddef.h>

typedef int esp_err_t;
#define ESP_OK 0

struct esp_task_wdt_config_t {
    uint32_t timeout_ms;
    uint32_t idle_core_mask;
    bool trigger_panic;
};

inline esp_err_t esp_task_wdt_reconfigure(const esp_task_wdt_config_t*) { return ESP_OK; }
inline esp_err_t esp_task_wdt_add(void*) { return ESP_OK; }
inline esp_err_t esp_task_wdt_delete(void*) { return ESP_OK; }
inline esp_err_t esp_task_wdt_reset() { return ESP_OK; }

#endif // ESP_TASK_WDT_H_STUB
