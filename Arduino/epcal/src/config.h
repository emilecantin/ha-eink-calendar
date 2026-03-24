#ifndef EINK_CALENDAR_CONFIG_H
#define EINK_CALENDAR_CONFIG_H

#include <Arduino.h>

// Configuration structure stored in NVS
struct Config {
  char ha_url[128];            // Home Assistant URL (from mDNS or manual override)
  char entry_id[64];           // Config entry ID (from announce response)
  uint32_t refresh_interval;   // seconds, default 900 (15 min)
  bool configured;             // true if config has been set
  bool discovered;             // true if device has been discovered by HA
};

// Cache state for ETag-based change detection
struct CacheState {
  char etag[33];              // MD5 hash is 32 chars + null
  bool display_valid;         // true if current display matches stored etag
};

// Bitmap endpoint paths (relative to ha_url)
struct BitmapEndpoints {
  char black_top[128];
  char black_bottom[128];
  char red_top[128];
  char red_bottom[128];
  char check[128];
};

// Default values
#define DEFAULT_REFRESH_INTERVAL 900  // 15 minutes
#define CONFIG_NAMESPACE "eink_cal"

// Initialize config system
void config_init();

// Load config from NVS, returns true if valid config exists
bool config_load(Config* config);

// Save config to NVS
void config_save(const Config* config);

// Clear all config (factory reset)
void config_clear();

// Load cache state from NVS
bool cache_load(CacheState* cache);

// Save cache state to NVS
void cache_save(const CacheState* cache);

// Clear cache state
void cache_clear();

// Load bitmap endpoints from NVS
bool endpoints_load(BitmapEndpoints* endpoints);

// Save bitmap endpoints to NVS
void endpoints_save(const BitmapEndpoints* endpoints);

#endif // EINK_CALENDAR_CONFIG_H
