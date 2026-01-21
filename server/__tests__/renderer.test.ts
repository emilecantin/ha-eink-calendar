import { describe, it, expect } from "@jest/globals";
import { extractChunk } from "../renderer";

describe("Renderer - extractChunk", () => {
  // Display constants from renderer.ts
  const DISPLAY_W = 1304;
  const DISPLAY_H = 984;
  const bytesPerRow = Math.ceil(DISPLAY_W / 8); // 163 bytes
  const halfHeight = Math.ceil(DISPLAY_H / 2); // 492 rows
  const chunkSize = bytesPerRow * halfHeight; // 80,196 bytes

  describe("E-Paper display chunking (vertical split)", () => {
    it("should split display into top and bottom halves", () => {
      // Full display bitmap: 163 bytes/row × 984 rows = 160,392 bytes
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);

      // Fill top half with 0xAA, bottom half with 0xBB
      for (let row = 0; row < DISPLAY_H / 2; row++) {
        for (let col = 0; col < bytesPerRow; col++) {
          bitmap[row * bytesPerRow + col] = 0xaa;
        }
      }
      for (let row = DISPLAY_H / 2; row < DISPLAY_H; row++) {
        for (let col = 0; col < bytesPerRow; col++) {
          bitmap[row * bytesPerRow + col] = 0xbb;
        }
      }

      const chunk1 = extractChunk(bitmap, 1);
      const chunk2 = extractChunk(bitmap, 2);

      // Chunk 1: top 492 rows (80,196 bytes)
      expect(chunk1.length).toBe(chunkSize);
      expect(chunk1[0]).toBe(0xaa);
      expect(chunk1[chunkSize - 1]).toBe(0xaa);

      // Chunk 2: bottom 492 rows (80,196 bytes)
      expect(chunk2.length).toBe(chunkSize);
      expect(chunk2[0]).toBe(0xbb);
      expect(chunk2[chunkSize - 1]).toBe(0xbb);
    });

    it("should extract correct chunk sizes for e-paper display", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);

      const chunk1 = extractChunk(bitmap, 1);
      const chunk2 = extractChunk(bitmap, 2);

      // Both chunks should be exactly 80,196 bytes (492 rows × 163 bytes/row)
      expect(chunk1.length).toBe(80196);
      expect(chunk2.length).toBe(80196);
      expect(chunk1.length + chunk2.length).toBe(fullBitmapSize);
    });

    it("should handle chunk 1 (top half, rows 0-491)", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);

      // Fill each row with its row number % 256
      for (let row = 0; row < DISPLAY_H; row++) {
        for (let col = 0; col < bytesPerRow; col++) {
          bitmap[row * bytesPerRow + col] = row % 256;
        }
      }

      const chunk1 = extractChunk(bitmap, 1);

      // First byte should be from row 0
      expect(chunk1[0]).toBe(0);

      // Last byte should be from row 491
      expect(chunk1[chunk1.length - 1]).toBe(491 % 256);
    });

    it("should handle chunk 2 (bottom half, rows 492-983)", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);

      // Fill each row with its row number % 256
      for (let row = 0; row < DISPLAY_H; row++) {
        for (let col = 0; col < bytesPerRow; col++) {
          bitmap[row * bytesPerRow + col] = row % 256;
        }
      }

      const chunk2 = extractChunk(bitmap, 2);

      // First byte should be from row 492
      expect(chunk2[0]).toBe(492 % 256);

      // Last byte should be from row 983
      const lastRow = DISPLAY_H - 1;
      expect(chunk2[chunk2.length - 1]).toBe(lastRow % 256);
    });

    it("should not modify original bitmap", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const original = Buffer.alloc(fullBitmapSize);

      // Fill with pattern
      for (let i = 0; i < fullBitmapSize; i++) {
        original[i] = i % 256;
      }

      const originalCopy = Buffer.from(original);

      extractChunk(original, 1);
      extractChunk(original, 2);

      expect(original).toEqual(originalCopy);
    });

    it("should use subarray (view, not copy) for memory efficiency", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);
      bitmap.fill(0xff);

      const chunk1 = extractChunk(bitmap, 1);

      // Modify chunk1 - should affect original bitmap since it's a view
      chunk1[0] = 0x00;

      expect(bitmap[0]).toBe(0x00); // Proves it's a view, not a copy
    });
  });

  describe("Edge cases", () => {
    it("should handle bitmap with specific pattern in each chunk", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);

      // Top half: all 0x11
      bitmap.fill(0x11, 0, chunkSize);
      // Bottom half: all 0x22
      bitmap.fill(0x22, chunkSize);

      const chunk1 = extractChunk(bitmap, 1);
      const chunk2 = extractChunk(bitmap, 2);

      expect(chunk1.every((b) => b === 0x11)).toBe(true);
      expect(chunk2.every((b) => b === 0x22)).toBe(true);
    });

    it("should calculate correct byte offsets for row boundaries", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);

      // Mark the first byte of each row with the row number
      for (let row = 0; row < DISPLAY_H; row++) {
        bitmap[row * bytesPerRow] = row % 256;
      }

      const chunk1 = extractChunk(bitmap, 1);
      const chunk2 = extractChunk(bitmap, 2);

      // Chunk 1: first byte should be row 0
      expect(chunk1[0]).toBe(0);
      // Chunk 1: byte at second row should be row 1
      expect(chunk1[bytesPerRow]).toBe(1);

      // Chunk 2: first byte should be row 492
      expect(chunk2[0]).toBe(492 % 256);
      // Chunk 2: byte at second row of chunk should be row 493
      expect(chunk2[bytesPerRow]).toBe(493 % 256);
    });
  });

  describe("Real-world bitmap data", () => {
    it("should handle typical e-paper bitmap with mixed black and white", () => {
      const fullBitmapSize = bytesPerRow * DISPLAY_H;
      const bitmap = Buffer.alloc(fullBitmapSize);

      // Simulate checkerboard pattern
      for (let i = 0; i < fullBitmapSize; i++) {
        bitmap[i] = i % 2 === 0 ? 0xaa : 0x55; // Alternating bits
      }

      const chunk1 = extractChunk(bitmap, 1);
      const chunk2 = extractChunk(bitmap, 2);

      expect(chunk1.length).toBe(chunkSize);
      expect(chunk2.length).toBe(chunkSize);

      // Verify pattern continues correctly
      expect(chunk1[0]).toBe(0xaa);
      expect(chunk1[1]).toBe(0x55);
      expect(chunk2[0]).toBe(0xaa); // chunkSize is even, so pattern continues
      expect(chunk2[1]).toBe(0x55);
    });
  });
});
