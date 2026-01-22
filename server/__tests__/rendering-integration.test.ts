import { describe, it, expect } from "@jest/globals";
import { renderCalendar, renderToPng, CalendarEvent } from "../renderer";

describe("Calendar Rendering Integration Tests", () => {
  const createMockEvent = (
    id: string,
    title: string,
    start: Date,
    end: Date,
    options?: Partial<CalendarEvent>,
  ): CalendarEvent => ({
    id,
    title,
    start,
    end,
    allDay: false,
    ...options,
  });

  describe("renderCalendar - Basic Rendering", () => {
    it("should render calendar with no events", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const result = await renderCalendar([], now, "landscape");

      expect(result).toHaveProperty("blackLayer");
      expect(result).toHaveProperty("redLayer");
      expect(result).toHaveProperty("etag");
      expect(result).toHaveProperty("timestamp");

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.redLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toMatch(/^[a-f0-9]{32}$/); // MD5 hash
      expect(result.timestamp).toEqual(now);
    });

    it("should render landscape mode with single event", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Test Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");

      expect(result.blackLayer.length).toBeGreaterThan(0);
      expect(result.redLayer.length).toBeGreaterThan(0);

      // Landscape: 1304x984, bytes per row = ceil(1304/8) = 163
      const expectedSize = 163 * 984; // 160,392 bytes
      expect(result.blackLayer.length).toBe(expectedSize);
      expect(result.redLayer.length).toBe(expectedSize);
    });

    it("should render portrait mode with single event", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Test Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const result = await renderCalendar(events, now, "portrait");

      // Portrait: 984x1304, bytes per row = ceil(984/8) = 123
      const expectedSize = 123 * 1304; // 160,392 bytes (same total after rotation)
      expect(result.blackLayer.length).toBe(expectedSize);
      expect(result.redLayer.length).toBe(expectedSize);
    });

    it("should generate different ETags for different content", async () => {
      const now = new Date("2024-01-15T10:00:00");

      const result1 = await renderCalendar([], now, "landscape");

      const events = [
        createMockEvent(
          "1",
          "Test Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];
      const result2 = await renderCalendar(events, now, "landscape");

      expect(result1.etag).not.toBe(result2.etag);
    });

    it("should generate same ETag for identical content", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Test Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const result1 = await renderCalendar(events, now, "landscape");
      const result2 = await renderCalendar(events, now, "landscape");

      expect(result1.etag).toBe(result2.etag);
    });
  });

  describe("renderCalendar - Event Types", () => {
    it("should render all-day events", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "All Day Event",
          new Date("2024-01-15T00:00:00"),
          new Date("2024-01-16T00:00:00"),
          { allDay: true },
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toBeTruthy();
    });

    it("should render multi-day events", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Multi-Day Event",
          new Date("2024-01-14T09:00:00"),
          new Date("2024-01-17T17:00:00"),
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toBeTruthy();
    });

    it("should render events with calendar colors", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Red Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
          { calendarColor: "#FF0000", calendarIcon: "●" },
        ),
        createMockEvent(
          "2",
          "Blue Event",
          new Date("2024-01-15T16:00:00"),
          new Date("2024-01-15T17:00:00"),
          { calendarColor: "#0000FF", calendarIcon: "■" },
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.redLayer).toBeInstanceOf(Buffer);
    });

    it("should handle many events (overflow scenario)", async () => {
      const now = new Date("2024-01-15T10:00:00");

      // Create 20 events for today
      const events = Array.from({ length: 20 }, (_, i) =>
        createMockEvent(
          `event-${i}`,
          `Event ${i + 1}`,
          new Date(`2024-01-15T${8 + i}:00:00`),
          new Date(`2024-01-15T${9 + i}:00:00`),
        ),
      );

      const result = await renderCalendar(events, now, "landscape");

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toBeTruthy();
    });
  });

  describe("renderCalendar - Optional Features", () => {
    it("should render with legend", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Event 1",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
          { calendarId: "cal1", calendarIcon: "●", calendarColor: "#FF0000" },
        ),
      ];

      const legend = [
        { icon: "●", name: "Work Calendar" },
        { icon: "■", name: "Personal" },
      ];

      const result = await renderCalendar(events, now, "landscape", legend);

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toBeTruthy();
    });

    it("should render with weather data", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const weather = [
        {
          date: new Date("2024-01-15T00:00:00"),
          condition: "sunny",
          tempHigh: 22,
          tempLow: 15,
        },
        {
          date: new Date("2024-01-16T00:00:00"),
          condition: "cloudy",
          tempHigh: 20,
          tempLow: 14,
        },
      ];

      const result = await renderCalendar(
        events,
        now,
        "landscape",
        [],
        weather,
      );

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toBeTruthy();
    });

    it("should render with indicators", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events: CalendarEvent[] = [];

      const indicators = [
        {
          entityId: "binary_sensor.trash",
          state: "on" as const,
          label: "Garbage",
          icon: "🗑️",
          shouldDisplay: true,
        },
      ];

      const result = await renderCalendar(
        events,
        now,
        "landscape",
        [],
        [],
        indicators,
      );

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toBeTruthy();
    });

    it("should render with collection calendars", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Garbage Collection",
          new Date("2024-01-15T00:00:00"),
          new Date("2024-01-16T00:00:00"),
          { allDay: true, calendarId: "collection.garbage" },
        ),
      ];

      const collectionCalendars = [
        "collection.garbage",
        "collection.recycling",
      ];
      const collectionTypes = [
        { name: "garbage", icon: "🗑️" },
        { name: "recycling", icon: "♻️" },
      ];

      const result = await renderCalendar(
        events,
        now,
        "landscape",
        [],
        [],
        [],
        collectionCalendars,
        collectionTypes,
      );

      expect(result.blackLayer).toBeInstanceOf(Buffer);
      expect(result.etag).toBeTruthy();
    });
  });

  describe("renderToPng - PNG Output", () => {
    it("should render PNG with no events", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const png = await renderToPng([], now, "landscape");

      expect(png).toBeInstanceOf(Buffer);
      expect(png.length).toBeGreaterThan(0);

      // PNG signature
      expect(png[0]).toBe(0x89);
      expect(png[1]).toBe(0x50);
      expect(png[2]).toBe(0x4e);
      expect(png[3]).toBe(0x47);
    });

    it("should render PNG in landscape mode", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Test Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const png = await renderToPng(events, now, "landscape");

      expect(png).toBeInstanceOf(Buffer);
      expect(png.length).toBeGreaterThan(1000); // Reasonable minimum size
    });

    it("should render PNG in portrait mode", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Test Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const png = await renderToPng(events, now, "portrait");

      expect(png).toBeInstanceOf(Buffer);
      expect(png.length).toBeGreaterThan(1000);
    });

    it("should render PNG with all optional features", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Test Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
          { calendarIcon: "●", calendarColor: "#FF0000" },
        ),
      ];

      const legend = [{ icon: "●", name: "Work" }];
      const weather = [
        {
          date: new Date("2024-01-15T00:00:00"),
          condition: "sunny",
          tempHigh: 22,
          tempLow: 15,
        },
      ];
      const indicators = [
        {
          entityId: "binary_sensor.test",
          state: "on" as const,
          label: "Test",
          icon: "🔔",
          shouldDisplay: true,
        },
      ];

      const png = await renderToPng(
        events,
        now,
        "landscape",
        legend,
        weather,
        indicators,
      );

      expect(png).toBeInstanceOf(Buffer);
      expect(png.length).toBeGreaterThan(1000);
    });
  });

  describe("Bitmap Layer Consistency", () => {
    it("should have consistent bitmap sizes between black and red layers", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Event",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const landscape = await renderCalendar(events, now, "landscape");
      expect(landscape.blackLayer.length).toBe(landscape.redLayer.length);

      const portrait = await renderCalendar(events, now, "portrait");
      expect(portrait.blackLayer.length).toBe(portrait.redLayer.length);
    });

    it("should produce valid bitmap data (all bytes)", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const result = await renderCalendar([], now, "landscape");

      // Check that buffers are not empty and contain valid byte values
      expect(result.blackLayer.length).toBeGreaterThan(0);
      expect(result.redLayer.length).toBeGreaterThan(0);

      // All bytes should be valid (0-255)
      for (let i = 0; i < 100; i++) {
        // Sample first 100 bytes
        expect(result.blackLayer[i]).toBeGreaterThanOrEqual(0);
        expect(result.blackLayer[i]).toBeLessThanOrEqual(255);
        expect(result.redLayer[i]).toBeGreaterThanOrEqual(0);
        expect(result.redLayer[i]).toBeLessThanOrEqual(255);
      }
    });

    it("should have mostly white pixels in empty calendar (bits set to 1)", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const result = await renderCalendar([], now, "landscape");

      // Count bytes with value 0xFF (all white pixels in that byte)
      let whiteByteCount = 0;
      for (let i = 0; i < result.blackLayer.length; i++) {
        if (result.blackLayer[i] === 0xff) {
          whiteByteCount++;
        }
      }

      // Most of an empty calendar should be white
      const whitePercentage = (whiteByteCount / result.blackLayer.length) * 100;
      expect(whitePercentage).toBeGreaterThan(50); // At least 50% white
    });
  });

  describe("Edge Cases and Error Handling", () => {
    it("should handle events at midnight", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Midnight Event",
          new Date("2024-01-15T00:00:00"),
          new Date("2024-01-15T01:00:00"),
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");
      expect(result.etag).toBeTruthy();
    });

    it("should handle events at end of day", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Late Event",
          new Date("2024-01-15T23:00:00"),
          new Date("2024-01-15T23:59:59"),
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");
      expect(result.etag).toBeTruthy();
    });

    it("should handle events with very long titles", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "This is a very long event title that should be truncated or wrapped appropriately to fit within the display constraints of the e-paper calendar",
          new Date("2024-01-15T14:00:00"),
          new Date("2024-01-15T15:00:00"),
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");
      expect(result.etag).toBeTruthy();
    });

    it("should handle past events on current day", async () => {
      const now = new Date("2024-01-15T15:00:00");
      const events = [
        createMockEvent(
          "1",
          "Past Event",
          new Date("2024-01-15T09:00:00"),
          new Date("2024-01-15T10:00:00"),
        ),
        createMockEvent(
          "2",
          "Future Event",
          new Date("2024-01-15T16:00:00"),
          new Date("2024-01-15T17:00:00"),
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");
      expect(result.etag).toBeTruthy();
    });

    it("should handle events spanning weeks", async () => {
      const now = new Date("2024-01-15T10:00:00");
      const events = [
        createMockEvent(
          "1",
          "Long Event",
          new Date("2024-01-10T09:00:00"),
          new Date("2024-01-25T17:00:00"),
        ),
      ];

      const result = await renderCalendar(events, now, "landscape");
      expect(result.etag).toBeTruthy();
    });
  });
});
