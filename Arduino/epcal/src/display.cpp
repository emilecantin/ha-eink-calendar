#include "display.h"
#include "DEV_Config.h"
#include "utility/EPD_12in48b.h"
#include "GUI_Paint.h"
#include "setup_screen.h"

void display_init() {
  DEV_ModuleInit();
  EPD_12in48B_Init();
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
  EPD_12in48B_Sleep();
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

void display_show_setup_screen(const char* ssid, const char* url) {
  // Allocate buffer for one chunk
  UBYTE* image = (UBYTE*)malloc(CHUNK_BUFFER_SIZE);
  if (!image) {
    Serial.println("Failed to allocate display buffer");
    return;
  }

  // Initialize display (need both module init and display init)
  DEV_ModuleInit();
  EPD_12in48B_Init();

  // === BLACK LAYER - TOP HALF (pre-rendered QR codes + runtime text) ===
  memcpy_P(image, setup_screen_bitmap, SETUP_SCREEN_BYTES);
  // Overlay text on the pre-rendered QR code bitmap
  // Paint_NewImage sets up drawing context without clearing
  Paint_NewImage(image, CHUNK_WIDTH, CHUNK_HEIGHT, 0, WHITE);

  Paint_DrawString_EN(50, 30, "CONFIGURATION EPCAL", &Font24, WHITE, BLACK);
  Paint_DrawString_EN(50, 70, "Scannez les codes QR pour configurer", &Font20, WHITE, BLACK);

  // Labels under QR codes (QR codes are at y=150, height=220, so labels at ~y=385)
  Paint_DrawString_EN(150, 385, "1. WiFi", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(150, 415, "EPCAL-Setup", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(700, 385, "2. Configuration", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(700, 415, "http://192.168.4.1", &Font16, WHITE, BLACK);

  EPD_12in48B_SendBlack1(image);

  // === BLACK LAYER - BOTTOM HALF ===
  Paint_Clear(WHITE);

  Paint_DrawString_EN(50, 50, "3. Entrez vos informations:", &Font20, WHITE, BLACK);
  Paint_DrawString_EN(80, 90, "- Nom et mot de passe de votre WiFi", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(80, 120, "- URL du serveur calendrier", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(80, 150, "- Intervalle de rafraichissement", &Font16, WHITE, BLACK);

  Paint_DrawString_EN(50, 210, "4. Cliquez sur 'Save' pour sauvegarder", &Font20, WHITE, BLACK);

  Paint_DrawString_EN(50, 290, "L'appareil se connectera automatiquement", &Font16, WHITE, BLACK);
  Paint_DrawString_EN(50, 320, "et affichera votre calendrier.", &Font16, WHITE, BLACK);

  EPD_12in48B_SendBlack2(image);

  // === RED LAYER - empty (both halves) ===
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed1(image);
  Paint_Clear(WHITE);
  EPD_12in48B_SendRed2(image);

  // Refresh display
  EPD_12in48B_TurnOnDisplay();

  free(image);
}
