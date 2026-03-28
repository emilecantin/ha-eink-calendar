#ifndef URL_VALIDATION_H
#define URL_VALIDATION_H

#include <string.h>

/**
 * Validate a Home Assistant URL.
 * Returns true if the URL is valid:
 * - Not empty
 * - Starts with http:// or https://
 * - Length <= 127 (must fit in a 128-byte buffer with null terminator)
 * - No whitespace characters
 */
inline bool validateHaUrl(const char* url) {
  if (!url || url[0] == '\0') {
    return false;
  }

  size_t len = strlen(url);

  // Must fit in config.ha_url (128 bytes including null terminator)
  if (len > 127) {
    return false;
  }

  // Must start with http:// or https://
  if (strncmp(url, "http://", 7) != 0 && strncmp(url, "https://", 8) != 0) {
    return false;
  }

  // No whitespace allowed
  for (size_t i = 0; i < len; i++) {
    if (url[i] == ' ' || url[i] == '\t' || url[i] == '\n' || url[i] == '\r') {
      return false;
    }
  }

  return true;
}

#endif // URL_VALIDATION_H
