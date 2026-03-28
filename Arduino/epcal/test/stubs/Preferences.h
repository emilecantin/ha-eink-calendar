/**
 * Minimal Preferences.h stub for native unit tests.
 *
 * The real ESP32 Preferences library wraps NVS (non-volatile storage).
 * This stub is intentionally empty — config.cpp uses Preferences directly,
 * so we can't unit-test config_load/config_save without a full NVS mock.
 * This stub exists only so that config.h (which includes Arduino.h but
 * not Preferences.h directly) can be included in tests.
 *
 * If you need to test config persistence, create a mock implementation
 * of the Preferences class here.
 */
#ifndef PREFERENCES_H_STUB
#define PREFERENCES_H_STUB

#include <cstdint>
#include <cstddef>
#include <cstring>

class Preferences {
public:
    bool begin(const char*, bool = false) { return true; }
    void end() {}
    bool clear() { return true; }
    bool remove(const char*) { return true; }

    bool   getBool(const char*, bool def = false) { return def; }
    unsigned int getUInt(const char*, uint32_t def = 0) { return def; }
    size_t getString(const char*, char* buf, size_t len) {
        if (buf && len > 0) buf[0] = '\0';
        return 0;
    }

    bool   putBool(const char*, bool) { return true; }
    bool   putUInt(const char*, uint32_t) { return true; }
    size_t putString(const char*, const char*) { return 0; }
};

#endif // PREFERENCES_H_STUB
