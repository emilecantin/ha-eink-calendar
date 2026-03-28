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
    config->ha_url[0] = '\0';
    config->entry_id[0] = '\0';
    config->refresh_interval = DEFAULT_REFRESH_INTERVAL;
    config->discovered = false;
    return false;
  }

  preferences.getString("ha_url", config->ha_url, sizeof(config->ha_url));
  preferences.getString("entry_id", config->entry_id, sizeof(config->entry_id));
  config->refresh_interval = preferences.getUInt("refresh_int", DEFAULT_REFRESH_INTERVAL);
  config->discovered = preferences.getBool("discovered", false);

  preferences.end();
  return true;
}

void config_save(const Config* config) {
  preferences.begin(CONFIG_NAMESPACE, false);  // read-write

  preferences.putBool("configured", config->configured);
  preferences.putString("ha_url", config->ha_url);
  preferences.putString("entry_id", config->entry_id);
  preferences.putUInt("refresh_int", config->refresh_interval);
  preferences.putBool("discovered", config->discovered);

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
    return false;
  }

  preferences.getString("etag", cache->etag, sizeof(cache->etag));

  preferences.end();
  return true;
}

void cache_save(const CacheState* cache) {
  preferences.begin(CONFIG_NAMESPACE, false);

  preferences.putBool("disp_valid", cache->display_valid);
  preferences.putString("etag", cache->etag);

  preferences.end();
}

void cache_clear() {
  preferences.begin(CONFIG_NAMESPACE, false);
  preferences.remove("disp_valid");
  preferences.remove("etag");
  preferences.end();
}

bool endpoints_load(BitmapEndpoints* endpoints) {
  preferences.begin(CONFIG_NAMESPACE, true);

  bool has_endpoints = preferences.getString("ep_black_top", endpoints->black_top, sizeof(endpoints->black_top)) > 0;

  if (!has_endpoints) {
    preferences.end();
    return false;
  }

  preferences.getString("ep_black_bot", endpoints->black_bottom, sizeof(endpoints->black_bottom));
  preferences.getString("ep_red_top", endpoints->red_top, sizeof(endpoints->red_top));
  preferences.getString("ep_red_bot", endpoints->red_bottom, sizeof(endpoints->red_bottom));
  preferences.getString("ep_check", endpoints->check, sizeof(endpoints->check));
  preferences.getString("ep_error", endpoints->error, sizeof(endpoints->error));

  preferences.end();
  return true;
}

void endpoints_save(const BitmapEndpoints* endpoints) {
  preferences.begin(CONFIG_NAMESPACE, false);

  preferences.putString("ep_black_top", endpoints->black_top);
  preferences.putString("ep_black_bot", endpoints->black_bottom);
  preferences.putString("ep_red_top", endpoints->red_top);
  preferences.putString("ep_red_bot", endpoints->red_bottom);
  preferences.putString("ep_check", endpoints->check);
  preferences.putString("ep_error", endpoints->error);

  preferences.end();
}
