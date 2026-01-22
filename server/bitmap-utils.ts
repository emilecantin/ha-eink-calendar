/**
 * Bitmap conversion utilities for EPCAL e-paper rendering.
 *
 * Handles image rotation, 1-bit conversion, and chunk extraction for ESP32 transfer.
 */

/**
 * Display dimensions (landscape - final output)
 */
const DISPLAY_W = 1304;
const DISPLAY_H = 984;

/**
 * Rotate image data 90 degrees clockwise
 *
 * @param imageData - Source image data
 * @returns Rotated image data (width and height are swapped)
 *
 * @example
 * Input: 984 × 1304 (portrait)
 * Output: 1304 × 984 (landscape)
 */
export function rotateImageData90CW(imageData: {
  width: number;
  height: number;
  data: Uint8ClampedArray;
}): {
  width: number;
  height: number;
  data: Uint8ClampedArray;
} {
  const { width, height, data } = imageData;
  const newWidth = height; // 1304
  const newHeight = width; // 984
  const newData = new Uint8ClampedArray(newWidth * newHeight * 4);

  for (let sy = 0; sy < height; sy++) {
    for (let sx = 0; sx < width; sx++) {
      // 90° clockwise: (sx, sy) → (height - 1 - sy, sx)
      const dx = height - 1 - sy;
      const dy = sx;

      const srcIndex = (sy * width + sx) * 4;
      const dstIndex = (dy * newWidth + dx) * 4;

      newData[dstIndex] = data[srcIndex];
      newData[dstIndex + 1] = data[srcIndex + 1];
      newData[dstIndex + 2] = data[srcIndex + 2];
      newData[dstIndex + 3] = data[srcIndex + 3];
    }
  }

  return { width: newWidth, height: newHeight, data: newData };
}

/**
 * Convert RGBA image data to 1-bit packed bitmap for e-paper display
 *
 * Waveshare e-paper format: 0 = colored, 1 = white/transparent
 *
 * @param imageData - RGBA image data to convert
 * @param isRed - Whether this is the red layer (different color detection)
 * @returns 1-bit packed buffer suitable for e-paper display
 */
export function imageDataTo1Bit(
  imageData: { width: number; height: number; data: Uint8ClampedArray },
  isRed: boolean,
): Buffer {
  const { width, height, data } = imageData;
  const bytesPerRow = Math.ceil(width / 8);
  // Waveshare e-paper: 0 = colored, 1 = white/transparent
  // Start with all 1s (white), then clear bits for colored pixels
  const buffer = Buffer.alloc(bytesPerRow * height, 0xff);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const pixelIndex = (y * width + x) * 4;
      const r = data[pixelIndex];
      const g = data[pixelIndex + 1];
      const b = data[pixelIndex + 2];

      let isColored = false;
      if (isRed) {
        // Red layer: pixel is colored if it's reddish
        isColored = r > 150 && g < 100 && b < 100;
      } else {
        // Black layer: higher threshold (170) captures more anti-aliased edges = bolder text
        const brightness = (r + g + b) / 3;
        const isRedColor = r > 150 && g < 100 && b < 100;
        isColored = brightness < 170 && !isRedColor;
      }

      if (isColored) {
        const byteIndex = y * bytesPerRow + Math.floor(x / 8);
        const bitIndex = 7 - (x % 8);
        buffer[byteIndex] &= ~(1 << bitIndex); // Clear bit to 0 for colored pixel
      }
    }
  }

  return buffer;
}

/**
 * Extract a chunk from a full layer bitmap
 *
 * Display is in landscape mode: 1304 wide x 984 tall
 * ESP32 expects two 492-row chunks for memory constraints
 *
 * @param layer - Full layer bitmap buffer
 * @param chunkIndex - Which chunk to extract (1 = top half, 2 = bottom half)
 * @returns Buffer containing the requested chunk
 *
 * @example
 * Chunk 1: rows 0-491
 * Chunk 2: rows 492-983
 */
export function extractChunk(layer: Buffer, chunkIndex: 1 | 2): Buffer {
  const bytesPerRow = Math.ceil(DISPLAY_W / 8); // 163 bytes
  const halfHeight = Math.ceil(DISPLAY_H / 2); // 492 rows
  const chunkSize = bytesPerRow * halfHeight; // 80196 bytes

  if (chunkIndex === 1) {
    return layer.subarray(0, chunkSize);
  } else {
    return layer.subarray(chunkSize);
  }
}
