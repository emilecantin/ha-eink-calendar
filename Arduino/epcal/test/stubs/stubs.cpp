/**
 * Definitions for stub global objects.
 * Link this file into native tests so that symbols like Serial, WiFi,
 * and Update are available.
 */
#include "Arduino.h"
#include "WiFi.h"
#include "Update.h"

SerialStub Serial;
WiFiClass WiFi;
UpdateClass Update;
