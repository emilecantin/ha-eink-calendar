#ifndef EPCAL_CONFIG_H
#define EPCAL_CONFIG_H

#include <Arduino.h>

// Configuration structure stored in NVS
struct Config {
  char server_url[128];       // e.g., "http://192.168.1.50:4000"
  uint32_t refresh_interval;  // seconds, default 1800 (30 min)
  bool configured;            // true if config has been set
};

// Cache state for ETag-based change detection
struct CacheState {
  char etag[33];              // MD5 hash is 32 chars + null
  uint32_t last_check_epoch;  // Unix timestamp of last successful check
  bool display_valid;         // true if current display matches stored etag
};

// Default values
#define DEFAULT_REFRESH_INTERVAL 900  // 15 minutes
#define CONFIG_NAMESPACE "epcal"

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

#endif // EPCAL_CONFIG_H
