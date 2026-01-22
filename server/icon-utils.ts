/**
 * Icon utilities for EPCAL calendar rendering.
 *
 * Handles collection icons (loading, caching, drawing) and icon positioning offsets.
 */

import { CanvasRenderingContext2D, Canvas, createCanvas, loadImage } from "canvas";
import path from "path";
import fs from "fs";

// Collection icon cache
const collectionIconCache = new Map<string, Canvas>();

/**
 * Vertical offset adjustments for icons (fraction of font size to shift)
 * Positive = shift down, negative = shift up
 *
 * For center alignment with text (used in TODAY and UPCOMING sections)
 */
const ICON_CENTER_OFFSETS: { [icon: string]: number } = {
  "●": -0.07,
  "■": -0.23,
  "▲": -0.04,
  "◆": -0.28,
  "★": -0.06,
  "♦": -0.07,
  "♣": -0.07,
  "♠": -0.07,
  "○": -0.23,
  "□": -0.04,
  "△": -0.23,
  "◇": -0.06,
  "☆": -0.06,
  "⬟": 0,
  "⬡": 0,
  "⬢": 0,
};

/**
 * For bottom alignment with time text (used in WEEK section)
 * Aligns icon bottom with "09:00" text bottom
 */
const ICON_BOTTOM_OFFSETS: { [icon: string]: number } = {
  "●": 0.29,
  "■": 0.38,
  "▲": -0.07,
  "◆": -0.15,
  "★": -0.22,
  "♦": -0.23,
  "♣": -0.15,
  "♠": -0.16,
  "○": 0.29,
  "□": 0.36,
  "△": -0.07,
  "◇": -0.15,
  "☆": -0.22,
  "⬟": -0.09,
  "⬡": 0.09,
  "⬢": 0.09,
};

/**
 * Get vertical offset for center-aligning an icon with text
 *
 * @param icon - Icon character
 * @param fontSize - Font size in pixels
 * @returns Vertical offset in pixels
 */
export function getIconCenterOffset(icon: string, fontSize: number): number {
  const factor = ICON_CENTER_OFFSETS[icon] || 0;
  return factor * fontSize;
}

/**
 * Get vertical offset for bottom-aligning an icon with text
 *
 * @param icon - Icon character
 * @param fontSize - Font size in pixels
 * @returns Vertical offset in pixels
 */
export function getIconBottomOffset(icon: string, fontSize: number): number {
  const factor = ICON_BOTTOM_OFFSETS[icon] || 0;
  return factor * fontSize;
}

/**
 * Load collection icon PNG and scale to specified size
 * Results are cached for performance
 *
 * @param iconName - Name of the icon file (without .png extension)
 * @param size - Target size in pixels (width and height)
 * @returns Canvas with the icon, or null if icon not found
 */
export async function loadCollectionIcon(
  iconName: string,
  size: number,
): Promise<Canvas | null> {
  const cacheKey = `${iconName}-${size}`;

  // Check cache first
  if (collectionIconCache.has(cacheKey)) {
    return collectionIconCache.get(cacheKey)!;
  }

  try {
    const iconsDir = path.join(__dirname, "collection-icons");
    const pngPath = path.join(iconsDir, `${iconName}.png`);

    if (!fs.existsSync(pngPath)) {
      console.warn(`Collection icon not found: ${iconName}`);
      return null;
    }

    // Load the pre-rendered PNG (72px with black fill)
    const img = await loadImage(pngPath);

    // Create a canvas at target size and downscale
    const iconCanvas = createCanvas(size, size);
    const iconCtx = iconCanvas.getContext("2d");

    // Draw the image scaled to target size (no background - keep transparency)
    iconCtx.drawImage(img, 0, 0, size, size);

    // Cache the result
    collectionIconCache.set(cacheKey, iconCanvas);
    return iconCanvas;
  } catch (error) {
    console.error(`Error loading collection icon ${iconName}:`, error);
    return null;
  }
}

/**
 * Draw a collection icon at the specified position
 * Only draws on the red layer (isRed=true)
 *
 * @param ctx - Canvas rendering context
 * @param iconName - Name of the icon file (without .png extension)
 * @param x - X coordinate (left edge)
 * @param y - Y coordinate (bottom edge - icon drawn upward from this point)
 * @param size - Icon size in pixels
 * @param isRed - Whether this is the red layer (icons only appear on red layer)
 * @returns Width of the drawn icon (size), or 0 if not drawn
 */
export async function drawCollectionIcon(
  ctx: CanvasRenderingContext2D,
  iconName: string,
  x: number,
  y: number,
  size: number,
  isRed: boolean,
): Promise<number> {
  // Only draw icons on the red layer
  if (!isRed) {
    return size;
  }

  const iconCanvas = await loadCollectionIcon(iconName, size);
  if (!iconCanvas) {
    return 0;
  }

  try {
    const drawY = y - size;

    // Get the icon's image data to convert black pixels to red
    const iconCtx = iconCanvas.getContext("2d");
    const imageData = iconCtx.getImageData(0, 0, size, size);
    const data = imageData.data;

    // Convert black pixels to red (for red layer rendering)
    // Red layer bitmap needs RGB(255, 0, 0) to be detected as colored by imageDataTo1Bit
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const a = data[i + 3];

      // If pixel is black (or dark) and not transparent
      if (r < 128 && g < 128 && b < 128 && a > 0) {
        data[i] = 255; // R = 255 (red)
        data[i + 1] = 0; // G = 0
        data[i + 2] = 0; // B = 0
        // Keep alpha unchanged
      } else {
        // Make non-black pixels transparent
        data[i + 3] = 0;
      }
    }

    // Create temporary canvas with converted pixels
    const redIconCanvas = createCanvas(size, size);
    const redIconCtx = redIconCanvas.getContext("2d");
    redIconCtx.putImageData(imageData, 0, 0);

    // Save context state
    ctx.save();

    // Ensure no transform or alpha issues
    ctx.globalAlpha = 1.0;
    ctx.globalCompositeOperation = "source-over";

    // Draw the red icon
    ctx.drawImage(redIconCanvas, x, drawY, size, size);

    // Restore context
    ctx.restore();

    return size;
  } catch (error) {
    console.error(`Error drawing collection icon ${iconName}:`, error);
    return 0;
  }
}
