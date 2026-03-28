/**
 * Minimal Arduino.h stub for native (host) unit tests.
 *
 * Provides just enough of the Arduino API to compile firmware headers
 * (config.h, http_client.h, display.h) without the real SDK.
 */
#ifndef ARDUINO_H_STUB
#define ARDUINO_H_STUB

#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <string>

// --- Arduino type aliases ---
typedef uint8_t byte;
typedef bool boolean;

// --- String class (minimal subset used by firmware) ---
class String {
public:
    String() : _buf() {}
    String(const char* s) : _buf(s ? s : "") {}
    String(const String& other) : _buf(other._buf) {}

    const char* c_str() const { return _buf.c_str(); }
    unsigned int length() const { return (unsigned int)_buf.length(); }

    String operator+(const String& rhs) const {
        return String((_buf + rhs._buf).c_str());
    }
    String operator+(const char* rhs) const {
        return String((_buf + rhs).c_str());
    }

    bool startsWith(const char* prefix) const {
        return _buf.rfind(prefix, 0) == 0;
    }
    bool endsWith(const char* suffix) const {
        if (!suffix) return false;
        std::string s(suffix);
        if (s.size() > _buf.size()) return false;
        return _buf.compare(_buf.size() - s.size(), s.size(), s) == 0;
    }
    void remove(unsigned int index, unsigned int count = 1) {
        _buf.erase(index, count);
    }

    String substring(unsigned int from) const {
        return String(_buf.substr(from).c_str());
    }
    String substring(unsigned int from, unsigned int to) const {
        return String(_buf.substr(from, to - from).c_str());
    }

    int toInt() const { return std::atoi(_buf.c_str()); }

private:
    std::string _buf;
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
