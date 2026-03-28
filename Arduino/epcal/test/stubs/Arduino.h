/**
 * Minimal Arduino.h stub for native (host) unit tests.
 *
 * Provides just enough of the Arduino API to compile firmware headers
 * (config.h, http_client.h, display.h) without the real SDK.
 *
 * Uses only C standard headers (string.h, stdint.h, etc.) to avoid
 * C++ stdlib availability issues with PlatformIO's native toolchain
 * on macOS (Apple Clang may not find <cstring>, <string>, etc.).
 */
#ifndef ARDUINO_H_STUB
#define ARDUINO_H_STUB

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

// --- Arduino type aliases ---
typedef uint8_t byte;
typedef bool boolean;

// --- String class (minimal subset used by firmware) ---
// Uses a fixed-size internal buffer instead of std::string to avoid
// C++ stdlib dependency.
class String {
public:
    String() { _buf[0] = '\0'; }
    String(const char* s) {
        if (s) {
            strncpy(_buf, s, sizeof(_buf) - 1);
            _buf[sizeof(_buf) - 1] = '\0';
        } else {
            _buf[0] = '\0';
        }
    }
    String(const String& other) {
        strncpy(_buf, other._buf, sizeof(_buf) - 1);
        _buf[sizeof(_buf) - 1] = '\0';
    }

    const char* c_str() const { return _buf; }
    unsigned int length() const { return (unsigned int)strlen(_buf); }

    String operator+(const String& rhs) const {
        String result;
        strncpy(result._buf, _buf, sizeof(result._buf) - 1);
        result._buf[sizeof(result._buf) - 1] = '\0';
        size_t len = strlen(result._buf);
        if (len < sizeof(result._buf) - 1) {
            strncpy(result._buf + len, rhs._buf, sizeof(result._buf) - 1 - len);
            result._buf[sizeof(result._buf) - 1] = '\0';
        }
        return result;
    }
    String operator+(const char* rhs) const {
        return *this + String(rhs);
    }

    bool startsWith(const char* prefix) const {
        return strncmp(_buf, prefix, strlen(prefix)) == 0;
    }
    bool endsWith(const char* suffix) const {
        if (!suffix) return false;
        size_t slen = strlen(suffix);
        size_t blen = strlen(_buf);
        if (slen > blen) return false;
        return strcmp(_buf + blen - slen, suffix) == 0;
    }
    void remove(unsigned int index, unsigned int count = 1) {
        size_t len = strlen(_buf);
        if (index >= len) return;
        if (index + count >= len) {
            _buf[index] = '\0';
        } else {
            memmove(_buf + index, _buf + index + count, len - index - count + 1);
        }
    }

    String substring(unsigned int from) const {
        size_t len = strlen(_buf);
        if (from >= len) return String("");
        return String(_buf + from);
    }
    String substring(unsigned int from, unsigned int to) const {
        size_t len = strlen(_buf);
        if (from >= len) return String("");
        if (to > len) to = (unsigned int)len;
        if (to <= from) return String("");
        String result;
        size_t count = to - from;
        if (count >= sizeof(result._buf)) count = sizeof(result._buf) - 1;
        strncpy(result._buf, _buf + from, count);
        result._buf[count] = '\0';
        return result;
    }

    int toInt() const { return atoi(_buf); }

private:
    char _buf[512];
};

// --- Serial stub (no-op) ---
struct SerialStub {
    void begin(unsigned long) {}
    void println(const char*) {}
    void println(const String&) {}
    void printf(const char*, ...) {}
    void flush() {}
};
extern SerialStub Serial;

// --- Common Arduino functions ---
inline unsigned long millis() { return 0; }
inline void delay(unsigned long) {}
inline void yield() {}

// --- GPIO stubs ---
#define INPUT_PULLUP 0x05
#define HIGH 1
#define LOW  0
inline void pinMode(uint8_t, uint8_t) {}
inline int  digitalRead(uint8_t) { return HIGH; }

#endif // ARDUINO_H_STUB
