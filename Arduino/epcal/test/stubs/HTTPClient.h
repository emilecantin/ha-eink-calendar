/**
 * Minimal HTTPClient.h stub for native unit tests.
 * Only enough to let http_client.h compile.
 */
#ifndef HTTPCLIENT_H_STUB
#define HTTPCLIENT_H_STUB

#include "Arduino.h"
#include "WiFi.h"

class HTTPClient {
public:
    void begin(WiFiClient&, const String&) {}
    void end() {}
    void addHeader(const char*, const char*) {}
    void setTimeout(int) {}
    void collectHeaders(const char*[], int) {}
    bool hasHeader(const char*) { return false; }
    String header(const char*) { return String(""); }
    int  POST(const String&) { return -1; }
    int  GET() { return -1; }
    int  getSize() { return 0; }
    String getString() { return String(""); }
    bool connected() { return false; }
    WiFiClient* getStreamPtr() { return nullptr; }
};

#endif // HTTPCLIENT_H_STUB
