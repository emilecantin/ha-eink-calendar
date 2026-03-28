/**
 * Minimal WiFi.h stub for native unit tests.
 * Only enough to let http_client.h compile.
 */
#ifndef WIFI_H_STUB
#define WIFI_H_STUB

#include "Arduino.h"

class WiFiClient {
public:
    bool connected() { return false; }
    int  available()  { return 0; }
    int  read()       { return -1; }
    size_t readBytes(uint8_t*, size_t) { return 0; }
    void stop() {}
    void print(const char*) {}
};

class WiFiClass {
public:
    void macAddress(uint8_t mac[6]) { memset(mac, 0, 6); }
};

extern WiFiClass WiFi;

#endif // WIFI_H_STUB
