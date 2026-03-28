/**
 * Minimal Update.h stub for native unit tests.
 */
#ifndef UPDATE_H_STUB
#define UPDATE_H_STUB

#include <stdint.h>
#include <stddef.h>

class UpdateClass {
public:
    bool begin(size_t) { return false; }
    size_t write(uint8_t*, size_t len) { return len; }
    bool end(bool = false) { return false; }
    void abort() {}
    const char* errorString() { return "stub"; }
};

extern UpdateClass Update;

#endif // UPDATE_H_STUB
