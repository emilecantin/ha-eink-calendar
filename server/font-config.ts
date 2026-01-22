/**
 * Font configuration for EPCAL calendar rendering.
 *
 * Registers Inter font family for use in canvas rendering.
 */

import { registerFont } from "canvas";
import path from "path";

/**
 * Register all required fonts for calendar rendering
 * Call this once at application startup
 */
export function registerFonts(): void {
  const fontsDir = path.join(__dirname, "fonts");

  registerFont(path.join(fontsDir, "Inter-Regular.ttf"), {
    family: "Inter",
    weight: "normal",
  });

  registerFont(path.join(fontsDir, "Inter-Medium.ttf"), {
    family: "Inter",
    weight: "500",
  });

  registerFont(path.join(fontsDir, "Inter-Bold.ttf"), {
    family: "Inter",
    weight: "bold",
  });
}

// Register fonts immediately when this module is imported
registerFonts();
