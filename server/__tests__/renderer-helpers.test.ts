import { describe, it, expect } from "@jest/globals";
import {
  getIconCenterOffset,
  getIconBottomOffset,
  getWeatherIcon,
  formatTime,
  truncateText,
  wrapText,
  rotateImageData90CW,
  imageDataTo1Bit,
} from "../renderer";
import { createCanvas } from "canvas";

describe("Icon positioning helpers", () => {
  describe("getIconCenterOffset", () => {
    it("should return 0 for unknown icons", () => {
      expect(getIconCenterOffset("unknown", 20)).toBe(0);
    });

    it("should calculate offset for known icons", () => {
      // From ICON_CENTER_OFFSETS: "●": -0.07
      expect(getIconCenterOffset("●", 20)).toBeCloseTo(-1.4); // -0.07 * 20
      expect(getIconCenterOffset("●", 40)).toBeCloseTo(-2.8); // -0.07 * 40
    });

    it("should handle different font sizes", () => {
      // From ICON_CENTER_OFFSETS: "■": -0.23
      expect(getIconCenterOffset("■", 100)).toBeCloseTo(-23); // -0.23 * 100
      expect(getIconCenterOffset("■", 20)).toBeCloseTo(-4.6); // -0.23 * 20
    });
  });

  describe("getIconBottomOffset", () => {
    it("should return 0 for unknown icons", () => {
      expect(getIconBottomOffset("unknown", 20)).toBe(0);
    });

    it("should calculate offset for known icons", () => {
      // From ICON_BOTTOM_OFFSETS: "●": 0.29
      expect(getIconBottomOffset("●", 20)).toBeCloseTo(5.8); // 0.29 * 20
      expect(getIconBottomOffset("●", 100)).toBeCloseTo(29); // 0.29 * 100
    });
  });
});

describe("Weather icon mapping", () => {
  it("should map clear-night to moon icon", () => {
    expect(getWeatherIcon("clear-night")).toBe("☽");
  });

  it("should map sunny to sun icon", () => {
    expect(getWeatherIcon("sunny")).toBe("☀");
    expect(getWeatherIcon("clear")).toBe("☀");
  });

  it("should map cloudy to cloud icon", () => {
    expect(getWeatherIcon("cloudy")).toBe("☁");
  });

  it("should map rainy to umbrella icon", () => {
    expect(getWeatherIcon("rainy")).toBe("☂");
  });

  it("should map pouring to umbrella with drops", () => {
    expect(getWeatherIcon("pouring")).toBe("☔");
  });

  it("should map snowy to snowflake icon", () => {
    expect(getWeatherIcon("snowy")).toBe("❄");
  });

  it("should map lightning to lightning bolt", () => {
    expect(getWeatherIcon("lightning")).toBe("⚡");
  });

  it("should map exceptional to warning icon", () => {
    expect(getWeatherIcon("exceptional")).toBe("⚠");
  });

  it("should be case-insensitive", () => {
    expect(getWeatherIcon("CLOUDY")).toBe("☁");
    expect(getWeatherIcon("Rainy")).toBe("☂");
    expect(getWeatherIcon("SUNNY")).toBe("☀");
  });

  it("should return ? for unknown conditions", () => {
    expect(getWeatherIcon("unknown-weather")).toBe("?");
    expect(getWeatherIcon("")).toBe("?");
  });
});

describe("Time formatting", () => {
  it("should format time in HH:mm format", () => {
    const date = new Date("2024-01-15T09:30:00");
    expect(formatTime(date)).toBe("09:30");
  });

  it("should handle midnight correctly", () => {
    const date = new Date("2024-01-15T00:00:00");
    expect(formatTime(date)).toBe("00:00");
  });

  it("should handle afternoon times", () => {
    const date = new Date("2024-01-15T14:45:00");
    expect(formatTime(date)).toBe("14:45");
  });

  it("should handle end of day", () => {
    const date = new Date("2024-01-15T23:59:00");
    expect(formatTime(date)).toBe("23:59");
  });
});

describe("Text truncation", () => {
  it("should not truncate text that fits", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const result = truncateText(ctx, "Short", 200);
    expect(result).toBe("Short");
  });

  it("should truncate long text with ellipsis", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const longText = "This is a very long text that will not fit";
    const result = truncateText(ctx, longText, 100);

    expect(result.endsWith("...")).toBe(true);
    expect(result.length).toBeLessThan(longText.length);
    expect(ctx.measureText(result).width).toBeLessThanOrEqual(100);
  });

  it("should handle very narrow width", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const result = truncateText(ctx, "Hello World", 20);
    expect(result.endsWith("...")).toBe(true);
  });

  it("should preserve short text exactly", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const text = "Hi";
    const result = truncateText(ctx, text, 100);
    expect(result).toBe(text);
  });
});

describe("Text wrapping", () => {
  it("should not wrap text that fits on one line", () => {
    const canvas = createCanvas(500, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const result = wrapText(ctx, "Short text", 500, 3);
    expect(result).toEqual(["Short text"]);
  });

  it("should wrap long text into multiple lines", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const result = wrapText(
      ctx,
      "This is a long text that needs wrapping",
      100,
      5,
    );

    expect(result.length).toBeGreaterThan(1);
    result.forEach((line) => {
      expect(ctx.measureText(line).width).toBeLessThanOrEqual(100);
    });
  });

  it("should respect maxLines limit", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const result = wrapText(
      ctx,
      "This is a very long text with many words that would wrap into many lines if allowed",
      80,
      2,
    );

    expect(result.length).toBeLessThanOrEqual(2);
  });

  it("should add ellipsis when text exceeds maxLines", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const result = wrapText(
      ctx,
      "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8",
      60,
      2,
    );

    expect(result.length).toBe(2);
    expect(result[result.length - 1].endsWith("...")).toBe(true);
  });

  it("should handle single word that fits", () => {
    const canvas = createCanvas(200, 100);
    const ctx = canvas.getContext("2d");
    ctx.font = "20px Inter";

    const result = wrapText(ctx, "Hello", 200, 3);
    expect(result).toEqual(["Hello"]);
  });
});

describe("Image rotation", () => {
  it("should rotate 2x3 image 90 degrees clockwise", () => {
    // Create a simple 2x3 image (2 wide, 3 tall)
    const width = 2;
    const height = 3;
    const data = new Uint8ClampedArray([
      // Row 0: Red, Green
      255, 0, 0, 255, 0, 255, 0, 255,
      // Row 1: Blue, Yellow
      0, 0, 255, 255, 255, 255, 0, 255,
      // Row 2: Magenta, Cyan
      255, 0, 255, 255, 0, 255, 255, 255,
    ]);

    const rotated = rotateImageData90CW({ width, height, data });

    expect(rotated.width).toBe(3); // height becomes width
    expect(rotated.height).toBe(2); // width becomes height

    // After 90° CW rotation:
    // Original:    Rotated:
    // R G          M B R
    // B Y    =>    C Y G
    // M C

    // Check first row of rotated image (M, B, R)
    expect(rotated.data[0]).toBe(255); // M: R component
    expect(rotated.data[1]).toBe(0); // M: G component
    expect(rotated.data[2]).toBe(255); // M: B component

    expect(rotated.data[4]).toBe(0); // B: R component
    expect(rotated.data[5]).toBe(0); // B: G component
    expect(rotated.data[6]).toBe(255); // B: B component

    expect(rotated.data[8]).toBe(255); // R: R component
    expect(rotated.data[9]).toBe(0); // R: G component
    expect(rotated.data[10]).toBe(0); // R: B component
  });

  it("should preserve dimensions for square image", () => {
    const width = 4;
    const height = 4;
    const data = new Uint8ClampedArray(width * height * 4);

    const rotated = rotateImageData90CW({ width, height, data });

    expect(rotated.width).toBe(4);
    expect(rotated.height).toBe(4);
  });

  it("should handle 1x1 image", () => {
    const data = new Uint8ClampedArray([100, 150, 200, 255]);

    const rotated = rotateImageData90CW({ width: 1, height: 1, data });

    expect(rotated.width).toBe(1);
    expect(rotated.height).toBe(1);
    expect(rotated.data).toEqual(data);
  });
});

describe("Bitmap conversion (imageDataTo1Bit)", () => {
  describe("Black layer conversion", () => {
    it("should convert all-white image to all 1s", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);
      // Fill with white (255, 255, 255)
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // All white = all bits set to 1 = 0xFF
      expect(bitmap[0]).toBe(0xff);
    });

    it("should convert all-black image to all 0s", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);
      // All pixels black (0, 0, 0)

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // All black = all bits cleared to 0 = 0x00
      expect(bitmap[0]).toBe(0x00);
    });

    it("should handle single black pixel in MSB position", () => {
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

      // Should be 0b01111111 = 0x7F (bit 7 cleared for black pixel)
      expect(bitmap[0]).toBe(0x7f);
    });

    it("should ignore red pixels in black layer", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make first pixel red (200, 50, 50) - should be ignored by black layer
      data[0] = 200;
      data[1] = 50;
      data[2] = 50;

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // Red pixels should be treated as white in black layer
      expect(bitmap[0]).toBe(0xff);
    });

    it("should use brightness threshold of 170", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Pixel with brightness just above threshold (avg = 171)
      data[0] = 171;
      data[1] = 171;
      data[2] = 171;

      const bitmap1 = imageDataTo1Bit({ data, width, height }, false);
      expect(bitmap1[0]).toBe(0xff); // Above threshold = white

      // Pixel with brightness just below threshold (avg = 169)
      data[0] = 169;
      data[1] = 169;
      data[2] = 169;

      const bitmap2 = imageDataTo1Bit({ data, width, height }, false);
      expect(bitmap2[0]).toBe(0x7f); // Below threshold = black (bit 7 cleared)
    });
  });

  describe("Red layer conversion", () => {
    it("should convert red pixels to 0 bits", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make first pixel red (200, 50, 50)
      data[0] = 200;
      data[1] = 50;
      data[2] = 50;

      const bitmap = imageDataTo1Bit({ data, width, height }, true);

      // Red pixel should set bit to 0 in red layer
      expect(bitmap[0]).toBe(0x7f); // 0b01111111
    });

    it("should ignore black pixels in red layer", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
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

      const bitmap = imageDataTo1Bit({ data, width, height }, true);

      // Black pixels should be treated as white in red layer
      expect(bitmap[0]).toBe(0xff);
    });

    it("should detect reddish colors (r>150, g<100, b<100)", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Test edge case: r=151, g=99, b=99 (just barely red)
      data[0] = 151;
      data[1] = 99;
      data[2] = 99;

      const bitmap1 = imageDataTo1Bit({ data, width, height }, true);
      expect(bitmap1[0]).toBe(0x7f); // Should be detected as red

      // Test edge case: r=150, g=99, b=99 (not quite red)
      data[0] = 150;
      data[1] = 99;
      data[2] = 99;

      const bitmap2 = imageDataTo1Bit({ data, width, height }, true);
      expect(bitmap2[0]).toBe(0xff); // Should NOT be detected as red
    });
  });

  describe("Multi-byte and multi-row handling", () => {
    it("should handle 16-pixel wide image (2 bytes per row)", () => {
      const width = 16;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make pixel 0 black (byte 0, bit 7)
      data[0] = 0;
      data[1] = 0;
      data[2] = 0;

      // Make pixel 8 black (byte 1, bit 7)
      const pixel8Index = 8 * 4;
      data[pixel8Index] = 0;
      data[pixel8Index + 1] = 0;
      data[pixel8Index + 2] = 0;

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      expect(bitmap.length).toBe(2);
      expect(bitmap[0]).toBe(0x7f); // First byte: bit 7 cleared
      expect(bitmap[1]).toBe(0x7f); // Second byte: bit 7 cleared
    });

    it("should handle multiple rows correctly", () => {
      const width = 8;
      const height = 2;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make first pixel of first row black
      data[0] = 0;
      data[1] = 0;
      data[2] = 0;

      // Make first pixel of second row black (pixel index 8)
      const row2Index = 8 * 4;
      data[row2Index] = 0;
      data[row2Index + 1] = 0;
      data[row2Index + 2] = 0;

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      expect(bitmap.length).toBe(2); // 1 byte per row
      expect(bitmap[0]).toBe(0x7f); // Row 0: bit 7 cleared
      expect(bitmap[1]).toBe(0x7f); // Row 1: bit 7 cleared
    });

    it("should handle non-multiple-of-8 width", () => {
      const width = 10; // Not a multiple of 8
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // Should be 2 bytes (ceil(10/8) = 2)
      expect(bitmap.length).toBe(2);
      expect(bitmap[0]).toBe(0xff);
      expect(bitmap[1]).toBe(0xff);
    });
  });

  describe("MSB-first bit ordering", () => {
    it("should use MSB-first ordering for e-paper display", () => {
      const width = 8;
      const height = 1;
      const data = new Uint8ClampedArray(width * height * 4);

      // All white
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;
        data[i + 1] = 255;
        data[i + 2] = 255;
        data[i + 3] = 255;
      }

      // Make specific pixels black to test bit positions
      // Pixel 0 (bit 7), Pixel 2 (bit 5), Pixel 7 (bit 0)
      data[0] = 0;
      data[1] = 0;
      data[2] = 0; // Pixel 0

      data[8] = 0;
      data[9] = 0;
      data[10] = 0; // Pixel 2

      data[28] = 0;
      data[29] = 0;
      data[30] = 0; // Pixel 7

      const bitmap = imageDataTo1Bit({ data, width, height }, false);

      // Binary: 01011110 = 0x5E
      // bit 7 (pixel 0): 0
      // bit 6 (pixel 1): 1
      // bit 5 (pixel 2): 0
      // bit 4 (pixel 3): 1
      // bit 3 (pixel 4): 1
      // bit 2 (pixel 5): 1
      // bit 1 (pixel 6): 1
      // bit 0 (pixel 7): 0
      expect(bitmap[0]).toBe(0x5e);
    });
  });
});
