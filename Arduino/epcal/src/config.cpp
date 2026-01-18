#include "config.h"
#include <Preferences.h>

static Preferences preferences;

void config_init() {
  // Nothing special needed, Preferences handles initialization
}

bool config_load(Config* config) {
  preferences.begin(CONFIG_NAMESPACE, true);  // read-only

  config->configured = preferences.getBool("configured", false);

  if (!config->configured) {
    preferences.end();
    // Set defaults
    config->server_url[0] = '\0';
    config->refresh_interval = DEFAULT_REFRESH_INTERVAL;
    return false;
  }

  preferences.getString("server_url", config->server_url, sizeof(config->server_url));
  config->refresh_interval = preferences.getUInt("refresh_int", DEFAULT_REFRESH_INTERVAL);

  preferences.end();
  return true;
}

void config_save(const Config* config) {
  preferences.begin(CONFIG_NAMESPACE, false);  // read-write

  preferences.putBool("configured", config->configured);
  preferences.putString("server_url", config->server_url);
  preferences.putUInt("refresh_int", config->refresh_interval);

  preferences.end();
}

void config_clear() {
  preferences.begin(CONFIG_NAMESPACE, false);
  preferences.clear();
  preferences.end();
}

bool cache_load(CacheState* cache) {
  preferences.begin(CONFIG_NAMESPACE, true);

  cache->display_valid = preferences.getBool("disp_valid", false);

  if (!cache->display_valid) {
    preferences.end();
    cache->etag[0] = '\0';
    cache->last_check_epoch = 0;
    return false;
  }

  preferences.getString("etag", cache->etag, sizeof(cache->etag));
  cache->last_check_epoch = preferences.getUInt("last_check", 0);

  preferences.end();
  return true;
}

void cache_save(const CacheState* cache) {
  preferences.begin(CONFIG_NAMESPACE, false);

  preferences.putBool("disp_valid", cache->display_valid);
  preferences.putString("etag", cache->etag);
  preferences.putUInt("last_check", cache->last_check_epoch);

  preferences.end();
}

void cache_clear() {
  preferences.begin(CONFIG_NAMESPACE, false);
  preferences.remove("disp_valid");
  preferences.remove("etag");
  preferences.remove("last_check");
  preferences.end();
}
