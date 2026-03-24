#ifndef EINK_CALENDAR_DISPLAY_H
#define EINK_CALENDAR_DISPLAY_H

#include <Arduino.h>

// Display dimensions (portrait mode)
#define DISPLAY_WIDTH  984
#define DISPLAY_HEIGHT 1304

// Chunk size (half the display height)
#define CHUNK_HEIGHT 492
#define CHUNK_WIDTH  1304

// Chunk buffer size in bytes (1-bit packed)
// 1304 pixels / 8 bits = 163 bytes per row * 492 rows = 80,196 bytes
#define CHUNK_BUFFER_SIZE 80196

/**
 * Initialize the e-paper display
 */
void display_init();

/**
 * Clear the display to white
 */
void display_clear();

/**
 * Send black layer chunk 1 (top half)
 * @param data  Packed 1-bit bitmap data
 */
void display_send_black1(const uint8_t* data);

/**
 * Send black layer chunk 2 (bottom half)
 * @param data  Packed 1-bit bitmap data
 */
void display_send_black2(const uint8_t* data);

/**
 * Send red layer chunk 1 (top half)
 * @param data  Packed 1-bit bitmap data
 */
void display_send_red1(const uint8_t* data);

/**
 * Send red layer chunk 2 (bottom half)
 * @param data  Packed 1-bit bitmap data
 */
void display_send_red2(const uint8_t* data);

/**
 * Trigger display refresh after sending all chunks
 */
void display_refresh();

/**
 * Put display into sleep mode
 */
void display_sleep();

/**
 * Display a simple text message (for status/errors during setup)
 * Note: This uses the Paint library and does a full refresh
 *
 * @param line1  First line of text
 * @param line2  Second line of text (optional, can be NULL)
 */
void display_show_message(const char* line1, const char* line2);

/**
 * Display an error message in red
 *
 * @param message  Error message to display
 */
void display_show_error(const char* message);

/**
 * Display the setup screen with QR codes for WiFi and config URL
 *
 * @param ssid  WiFi network name (for QR code)
 * @param url   Config portal URL (for QR code)
 */
void display_show_setup_screen(const char* ssid, const char* url);

#endif // EINK_CALENDAR_DISPLAY_H
