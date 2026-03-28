#include "display.h"
#include "DEV_Config.h"
#include "utility/EPD_12in48b.h"
#include "GUI_Paint.h"
#include "qrcode.h"

// Guard flag — prevents display_sleep() from being called before
// the display hardware has been initialized (which would hang at "M1 Busy").
static bool _display_initialized = false;

void display_init() {
  DEV_ModuleInit();
  EPD_12in48B_Init();
  _display_initialized = true;
}

void display_clear() {
  EPD_12in48B_Clear();
}

void display_send_black1(const uint8_t* data) {
  EPD_12in48B_SendBlack1((UBYTE*)data);
}

void display_send_black2(const uint8_t* data) {
  EPD_12in48B_SendBlack2((UBYTE*)data);
}

void display_send_red1(const uint8_t* data) {
  EPD_12in48B_SendRed1((UBYTE*)data);
}

void display_send_red2(const uint8_t* data) {
  EPD_12in48B_SendRed2((UBYTE*)data);
}

void display_refresh() {
  EPD_12in48B_TurnOnDisplay();
}

void display_sleep() {
  if (!_display_initialized) return;
  EPD_12in48B_Sleep();
}

bool display_is_initialized() {
  return _display_initialized;
}

void display_reset_initialized() {
  _display_initialized = false;
}

void display_show_message(const char* line1, const char* line2) {
  // Allocate buffer for one chunk (we'll only use part of it)
  UBYTE* image = (UBYTE*)malloc(CHUNK_BUFFER_SIZE);
  if (!image) {
    Serial.println("Failed to allocate display buffer");
    return;
  }

  // Initialize display (must call DEV_ModuleInit before EPD init)
  DEV_ModuleInit();
  EPD_12in48B_Init();
  _display_initialized = true;

  // Create image buffer
  Paint_NewImage(image, CHUNK_WIDTH, CHUNK_HEIGHT, 0, WHITE);

  // Draw black layer - top half with message
  Paint_Clear(WHITE);
  Paint_DrawString_EN(50, 200, line1, &Font24, WHITE, BLACK);
  if (line2) {
    Paint_DrawString_EN(50, 240, line2, &Font24, WHITE, BLACK);
  }
  EPD_12in48B_SendBlack1(image);

  // Bottom half - empty
  Paint_Clear(WHITE);
  EPD_12in48B_SendBlack2(image);

  // Red layer - empty (both halves)
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed1(image);
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed2(image);

  // Refresh display
  EPD_12in48B_TurnOnDisplay();

  free(image);
}

void display_show_error(const char* message) {
  // Allocate buffer for one chunk
  UBYTE* image = (UBYTE*)malloc(CHUNK_BUFFER_SIZE);
  if (!image) {
    Serial.println("Failed to allocate display buffer");
    return;
  }

  // Initialize display (must call DEV_ModuleInit before EPD init)
  DEV_ModuleInit();
  EPD_12in48B_Init();
  _display_initialized = true;

  // Create image buffer
  Paint_NewImage(image, CHUNK_WIDTH, CHUNK_HEIGHT, 0, WHITE);

  // Draw black layer - empty for both halves
  Paint_Clear(WHITE);
  EPD_12in48B_SendBlack1(image);
  Paint_Clear(WHITE);
  EPD_12in48B_SendBlack2(image);

  // Red layer - top half with error message
  Paint_Clear(WHITE);
  Paint_DrawString_EN(50, 200, "ERROR:", &Font24, WHITE, BLACK);
  Paint_DrawString_EN(50, 240, message, &Font24, WHITE, BLACK);
  EPD_12in48B_SendRed1(image);

  // Bottom half - empty
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed2(image);

  // Refresh display
  EPD_12in48B_TurnOnDisplay();

  free(image);
}

/**
 * Helper: draw a QR code onto the current Paint image at (x, y) with given pixel scale.
 */
static void drawQRCode(QRCode* qrcode, int x, int y, int scale) {
  int size = qrcode->size;
  for (int qy = 0; qy < size; qy++) {
    for (int qx = 0; qx < size; qx++) {
      if (qrcode_getModule(qrcode, qx, qy)) {
        Paint_DrawRectangle(
          x + qx * scale, y + qy * scale,
          x + (qx + 1) * scale - 1, y + (qy + 1) * scale - 1,
          BLACK, DRAW_FILL_FULL, DOT_PIXEL_1X1
        );
      }
    }
  }
}

void display_show_setup_screen(const char* ssid, const char* url) {
  UBYTE* image = (UBYTE*)malloc(CHUNK_BUFFER_SIZE);
  if (!image) {
    Serial.println("Failed to allocate display buffer");
    return;
  }

  DEV_ModuleInit();
  EPD_12in48B_Init();
  _display_initialized = true;

  // Generate WiFi QR code (WIFI:T:nopass;S:<ssid>;;)
  char wifiQrText[128];
  snprintf(wifiQrText, sizeof(wifiQrText), "WIFI:T:nopass;S:%s;;", ssid);

  QRCode wifiQr;
  uint8_t wifiQrData[qrcode_getBufferSize(6)];
  qrcode_initText(&wifiQr, wifiQrData, 6, ECC_LOW, wifiQrText);

  // Generate config URL QR code
  QRCode urlQr;
  uint8_t urlQrData[qrcode_getBufferSize(6)];
  qrcode_initText(&urlQr, urlQrData, 6, ECC_LOW, url);

  // === BLACK LAYER - TOP HALF ===
  Paint_NewImage(image, CHUNK_WIDTH, CHUNK_HEIGHT, 0, WHITE);
  Paint_Clear(WHITE);

  Paint_DrawString_EN(50, 20, "E-INK CALENDAR", &Font24, WHITE, BLACK);

  // Step 1 with WiFi QR
  int qrScale = 5;
  int qrSize = wifiQr.size * qrScale;

  Paint_DrawString_EN(50, 70, "1. Connectez-vous au WiFi", &Font24, WHITE, BLACK);
  Paint_DrawString_EN(70, 110, "du calendrier:", &Font20, WHITE, BLACK);
  drawQRCode(&wifiQr, 70, 155, qrScale);
  Paint_DrawString_EN(70, 155 + qrSize + 10, ssid, &Font16, WHITE, BLACK);
  Paint_DrawString_EN(70, 155 + qrSize + 35, "(pas de mot de passe)", &Font16, WHITE, BLACK);

  // Step 2 with config URL QR on the right side
  int rightX = CHUNK_WIDTH / 2 + 50;
  Paint_DrawString_EN(rightX, 70, "2. Ouvrez cette page:", &Font24, WHITE, BLACK);
  drawQRCode(&urlQr, rightX, 155, qrScale);
  Paint_DrawString_EN(rightX, 155 + qrSize + 10, url, &Font16, WHITE, BLACK);
  Paint_DrawString_EN(rightX, 155 + qrSize + 35, "(ou appuyez sur la notification)", &Font16, WHITE, BLACK);

  EPD_12in48B_SendBlack1(image);

  // === BLACK LAYER - BOTTOM HALF ===
  Paint_Clear(WHITE);

  Paint_DrawString_EN(50, 40, "3. Choisissez votre reseau WiFi", &Font24, WHITE, BLACK);
  Paint_DrawString_EN(70, 85, "et entrez le mot de passe.", &Font20, WHITE, BLACK);

  Paint_DrawString_EN(50, 150, "4. Appuyez sur 'Save'", &Font24, WHITE, BLACK);

  Paint_DrawString_EN(50, 230, "Le calendrier se connectera", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(50, 260, "automatiquement a Home Assistant.", &Font20, WHITE, BLACK);

  EPD_12in48B_SendBlack2(image);

  // === RED LAYER - empty (both halves) ===
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed1(image);
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed2(image);

  EPD_12in48B_TurnOnDisplay();

  free(image);
}

void display_show_ha_config_screen(const char* url) {
  UBYTE* image = (UBYTE*)malloc(CHUNK_BUFFER_SIZE);
  if (!image) {
    Serial.println("Failed to allocate display buffer");
    return;
  }

  DEV_ModuleInit();
  EPD_12in48B_Init();
  _display_initialized = true;

  // Generate QR code for the URL
  QRCode qrcode;
  uint8_t qrcodeData[qrcode_getBufferSize(6)];  // Version 6 handles up to 134 chars
  qrcode_initText(&qrcode, qrcodeData, 6, ECC_LOW, url);

  // === BLACK LAYER - TOP HALF ===
  Paint_NewImage(image, CHUNK_WIDTH, CHUNK_HEIGHT, 0, WHITE);
  Paint_Clear(WHITE);

  Paint_DrawString_EN(50, 30, "HOME ASSISTANT NON TROUVE", &Font24, WHITE, BLACK);
  Paint_DrawString_EN(50, 70, "Scannez le code QR pour entrer", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(50, 100, "l'adresse de Home Assistant:", &Font20, WHITE, BLACK);

  // Draw QR code centered — scale 6 gives ~250px for version 6 (41 modules)
  int qrPixelSize = 6;
  int qrTotalSize = qrcode.size * qrPixelSize;
  int qrX = (CHUNK_WIDTH - qrTotalSize) / 2;
  int qrY = 150;
  drawQRCode(&qrcode, qrX, qrY, qrPixelSize);

  // URL label below QR
  Paint_DrawString_EN(qrX, qrY + qrTotalSize + 15, url, &Font20, WHITE, BLACK);

  EPD_12in48B_SendBlack1(image);

  // === BLACK LAYER - BOTTOM HALF ===
  Paint_Clear(WHITE);
  Paint_DrawString_EN(50, 50, "Ou entrez l'adresse manuellement:", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(50, 90, "1. Ouvrez le lien ci-dessus", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 120, "2. Entrez l'URL de Home Assistant", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 150, "   (ex: http://homeassistant.local:8123)", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 180, "3. Cliquez 'Save'", &Font16, WHITE, BLACK);
  EPD_12in48B_SendBlack2(image);

  // === RED LAYER - empty ===
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed1(image);
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed2(image);

  EPD_12in48B_TurnOnDisplay();

  free(image);
}

void display_show_install_screen(const char* repo_url) {
  UBYTE* image = (UBYTE*)malloc(CHUNK_BUFFER_SIZE);
  if (!image) {
    Serial.println("Failed to allocate display buffer");
    return;
  }

  DEV_ModuleInit();
  EPD_12in48B_Init();
  _display_initialized = true;

  // Generate QR code for the repo URL
  QRCode qrcode;
  uint8_t qrcodeData[qrcode_getBufferSize(6)];
  qrcode_initText(&qrcode, qrcodeData, 6, ECC_LOW, repo_url);

  // === BLACK LAYER - TOP HALF ===
  Paint_NewImage(image, CHUNK_WIDTH, CHUNK_HEIGHT, 0, WHITE);
  Paint_Clear(WHITE);

  Paint_DrawString_EN(50, 30, "INTEGRATION NON INSTALLEE", &Font24, WHITE, BLACK);
  Paint_DrawString_EN(50, 70, "Home Assistant a ete trouve, mais", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(50, 100, "l'integration E-Ink Calendar n'est", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(50, 130, "pas encore installee.", &Font20, WHITE, BLACK);

  // Draw QR code centered
  int qrPixelSize = 5;
  int qrTotalSize = qrcode.size * qrPixelSize;
  int qrX = (CHUNK_WIDTH - qrTotalSize) / 2;
  int qrY = 180;
  drawQRCode(&qrcode, qrX, qrY, qrPixelSize);

  EPD_12in48B_SendBlack1(image);

  // === BLACK LAYER - BOTTOM HALF ===
  Paint_Clear(WHITE);
  Paint_DrawString_EN(50, 30, "Scannez le code QR pour les", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(50, 60, "instructions d'installation.", &Font20, WHITE, BLACK);

  Paint_DrawString_EN(50, 120, "1. Installez HACS si necessaire", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 150, "2. Ajoutez le depot E-Ink Calendar", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 180, "3. Redemarrez Home Assistant", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 210, "4. Cet ecran se mettra a jour", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 240, "   automatiquement.", &Font16, WHITE, BLACK);

  EPD_12in48B_SendBlack2(image);

  // === RED LAYER - empty ===
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed1(image);
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed2(image);

  EPD_12in48B_TurnOnDisplay();

  free(image);
}
