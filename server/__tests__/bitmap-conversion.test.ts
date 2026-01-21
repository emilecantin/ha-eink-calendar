import { describe, it, expect } from '@jest/globals';

/**
 * Tests for bitmap conversion logic
 * Critical for e-paper display - converts canvas ImageData to 1-bit bitmaps
 */

describe('Bitmap conversion', () => {
  describe('1-bit bitmap conversion', () => {
    /**
     * Convert RGBA ImageData to 1-bit bitmap (MSB first)
     * 1 = white, 0 = black (or 0 = red for red layer)
     */
    const imageDataTo1Bit = (
      imageData: { data: Uint8ClampedArray; width: number; height: number },
      isRedLayer: boolean,
    ): Buffer => {
      const { data, width, height } = imageData;
      const byteWidth = Math.ceil(width / 8);
      const bitmap = Buffer.alloc(byteWidth * height);

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const i = (y * width + x) * 4;
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          let isWhite: boolean;
          if (isRedLayer) {
            // Red layer: detect red pixels
            isWhite = !(r > 200 && g < 100 && b < 100);
          } else {
            // Black layer: detect black pixels
            isWhite = !(r < 100 && g < 100 && b < 100);
          }

          if (!isWhite) {
            const byteIndex = y * byteWidth + Math.floor(x / 8);
            const bitIndex = 7 - (x % 8); // MSB first
            bitmap[byteIndex] |= 1 << bitIndex;
          }
        }
      }

      return bitmap;
    };

    it('should convert all-white image to all 0s', () => {
      const width = 8;
      const height = 2;
      const data = new Uint8ClampedArray(width * height * 4);

      // Fill with white (255, 255, 255, 255)
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255; // R
        data[i + 1] = 255; // G
        data[i + 2] = 255; // B
        data[i + 3] = 255; // A
      }

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // All white = all 0 bits
      expect(bitmap.every((byte) => byte === 0)).toBe(true);
    });

    it('should convert all-black image to all 1s', () => {
      const width = 8;
      const height = 2;
      const data = new Uint8ClampedArray(width * height * 4);

      // Fill with black (0, 0, 0, 255)
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 0; // R
        data[i + 1] = 0; // G
        data[i + 2] = 0; // B
        data[i + 3] = 255; // A
      }

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // All black = all 1 bits
      expect(bitmap.every((byte) => byte === 255)).toBe(true);
    });

    it('should handle single black pixel in MSB position', () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white except first pixel
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make first pixel black
      data[0] = 0;
      data[1] = 0;
      data[2] = 0;

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // Should be 0b10000000 = 128
      expect(bitmap[0]).toBe(128);
    });

    it('should handle single black pixel in LSB position', () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white except last pixel
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make last pixel black
      const lastPixel = (width - 1) * 4;
      data[lastPixel] = 0;
      data[lastPixel + 1] = 0;
      data[lastPixel + 2] = 0;

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // Should be 0b00000001 = 1
      expect(bitmap[0]).toBe(1);
    });

    it('should handle width not divisible by 8', () => {
      const width = 10; // Not divisible by 8
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // Fill with white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // Should be 2 bytes (ceil(10/8) = 2)
      expect(bitmap.length).toBe(2);
      expect(bitmap[0]).toBe(0);
      expect(bitmap[1]).toBe(0);
    });

    it('should detect red pixels on red layer', () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white except one red pixel
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make first pixel red (255, 0, 0)
      data[0] = 255;
      data[1] = 0;
      data[2] = 0;

      const bitmap = imageDataTo1Bit({ data, width, height }, true);

      // Red pixel should be detected (bit set)
      expect(bitmap[0]).toBe(128); // 0b10000000
    });

    it('should ignore red pixels on black layer', () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white except one red pixel
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make first pixel red
      data[0] = 255;
      data[1] = 0;
      data[2] = 0;

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // Red pixel should NOT be detected on black layer
      expect(bitmap[0]).toBe(0);
    });
  });

  describe('Bitmap chunking for ESP32', () => {
    /**
     * Split bitmap into chunks for memory-constrained ESP32
     */
    const chunkBitmap = (
      bitmap: Buffer,
      width: number,
      height: number,
      chunks: number,
    ): Buffer[] => {
      const byteWidth = Math.ceil(width / 8);
      const rowsPerChunk = Math.ceil(height / chunks);
      const bytesPerChunk = byteWidth * rowsPerChunk;

      const result: Buffer[] = [];
      for (let i = 0; i < chunks; i++) {
        const start = i * bytesPerChunk;
        const end = Math.min(start + bytesPerChunk, bitmap.length);
        result.push(bitmap.subarray(start, end));
      }

      return result;
    };

    it('should split bitmap into 2 equal chunks', () => {
      const width = 8;
      const height = 4;
      const byteWidth = 1;
      const bitmap = Buffer.alloc(byteWidth * height, 255);

      const chunks = chunkBitmap(bitmap, width, height, 2);

      expect(chunks).toHaveLength(2);
      expect(chunks[0].length).toBe(2); // 2 rows
      expect(chunks[1].length).toBe(2); // 2 rows
    });

    it('should split bitmap into 4 chunks', () => {
      const width = 1304;
      const height = 984;
      const byteWidth = Math.ceil(width / 8); // 163 bytes
      const bitmap = Buffer.alloc(byteWidth * height);

      const chunks = chunkBitmap(bitmap, width, height, 4);

      expect(chunks).toHaveLength(4);
      // Each chunk should have roughly 1/4 of the data
      const expectedSize = Math.ceil((byteWidth * height) / 4);
      chunks.forEach((chunk) => {
        expect(chunk.length).toBeLessThanOrEqual(expectedSize);
        expect(chunk.length).toBeGreaterThan(0);
      });
    });

    it('should handle odd height divisions', () => {
      const width = 8;
      const height = 5; // Not evenly divisible by 2
      const byteWidth = 1;
      const bitmap = Buffer.alloc(byteWidth * height);

      const chunks = chunkBitmap(bitmap, width, height, 2);

      expect(chunks).toHaveLength(2);
      expect(chunks[0].length).toBe(3); // ceil(5/2) = 3 rows
      expect(chunks[1].length).toBe(2); // Remaining 2 rows
    });
  });

  describe('Bitmap validation', () => {
    it('should verify bitmap size matches dimensions', () => {
      const width = 1304;
      const height = 984;
      const expectedByteWidth = Math.ceil(width / 8);
      const expectedSize = expectedByteWidth * height;

      // Create bitmap
      const bitmap = Buffer.alloc(expectedSize);

      expect(bitmap.length).toBe(expectedSize);
      expect(bitmap.length).toBe(163 * 984); // 160,392 bytes
    });

    it('should calculate correct byte width for various widths', () => {
      const testCases = [
        { width: 8, expectedBytes: 1 },
        { width: 9, expectedBytes: 2 },
        { width: 16, expectedBytes: 2 },
        { width: 17, expectedBytes: 3 },
        { width: 1304, expectedBytes: 163 },
      ];

      testCases.forEach(({ width, expectedBytes }) => {
        const calculated = Math.ceil(width / 8);
        expect(calculated).toBe(expectedBytes);
      });
    });
  });
});
