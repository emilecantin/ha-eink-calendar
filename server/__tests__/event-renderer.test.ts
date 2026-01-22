import { describe, it, expect } from "@jest/globals";
import {
  drawEventTriangle,
  formatMultiDayTime,
  drawOverflowIndicator,
  sortEventsByPriority,
} from "../event-renderer";
import { CalendarEvent } from "../renderer";

// Mock canvas context
const createMockContext = () => {
  const operations: string[] = [];
  return {
    operations,
    ctx: {
      beginPath: () => operations.push("beginPath"),
      moveTo: (x: number, y: number) => operations.push(`moveTo(${x},${y})`),
      lineTo: (x: number, y: number) => operations.push(`lineTo(${x},${y})`),
      closePath: () => operations.push("closePath"),
      fill: () => operations.push("fill"),
      fillText: (text: string, x: number, y: number) =>
        operations.push(`fillText("${text}",${x},${y})`),
      measureText: (text: string) => ({ width: text.length * 10 }),
      set fillStyle(_value: string) {
        operations.push(`fillStyle=${_value}`);
      },
      set font(_value: string) {
        operations.push(`font=${_value}`);
      },
    } as any,
  };
};

describe("event-renderer", () => {
  describe("drawEventTriangle", () => {
    it("should draw left-pointing triangle correctly", () => {
      const { ctx, operations } = createMockContext();

      drawEventTriangle({
        ctx,
        x: 100,
        y: 50,
        size: 6,
        direction: "left",
      });

      expect(operations).toContain("beginPath");
      expect(operations).toContain("moveTo(100,44)");
      expect(operations).toContain("lineTo(106,50)");
      expect(operations).toContain("lineTo(100,56)");
      expect(operations).toContain("closePath");
      expect(operations).toContain("fill");
    });

    it("should draw right-pointing triangle correctly", () => {
      const { ctx, operations } = createMockContext();

      drawEventTriangle({
        ctx,
        x: 100,
        y: 50,
        size: 6,
        direction: "right",
      });

      expect(operations).toContain("beginPath");
      expect(operations).toContain("moveTo(100,44)");
      expect(operations).toContain("lineTo(94,50)");
      expect(operations).toContain("lineTo(100,56)");
      expect(operations).toContain("closePath");
      expect(operations).toContain("fill");
    });
  });

  describe("formatMultiDayTime", () => {
    it("should return empty string for all-day events", () => {
      const event: CalendarEvent = {
        id: "1",
        title: "Test Event",
        start: new Date("2024-01-15"),
        end: new Date("2024-01-15"),
        allDay: true,
      };

      const result = formatMultiDayTime({
        event,
        dayIndicators: { startsOnDay: true, endsOnDay: true },
      });

      expect(result).toBe("");
    });

    it("should format start time with arrow when event starts on day", () => {
      const event: CalendarEvent = {
        id: "1",
        title: "Test Event",
        start: new Date("2024-01-15T09:00:00"),
        end: new Date("2024-01-16T10:00:00"),
        allDay: false,
      };

      const result = formatMultiDayTime({
        event,
        dayIndicators: { startsOnDay: true, endsOnDay: false },
      });

      expect(result).toMatch(/^\d{1,2}:\d{2} ▶$/);
    });

    it("should format end time with arrow when event ends on day", () => {
      const event: CalendarEvent = {
        id: "1",
        title: "Test Event",
        start: new Date("2024-01-14T09:00:00"),
        end: new Date("2024-01-15T10:00:00"),
        allDay: false,
      };

      const result = formatMultiDayTime({
        event,
        dayIndicators: { startsOnDay: false, endsOnDay: true },
      });

      expect(result).toMatch(/^◀ \d{1,2}:\d{2}$/);
    });

    it("should show double arrows when event spans day", () => {
      const event: CalendarEvent = {
        id: "1",
        title: "Test Event",
        start: new Date("2024-01-14T09:00:00"),
        end: new Date("2024-01-16T10:00:00"),
        allDay: false,
      };

      const result = formatMultiDayTime({
        event,
        dayIndicators: { startsOnDay: false, endsOnDay: false },
      });

      expect(result).toBe("◀ ▶");
    });
  });

  describe("drawOverflowIndicator", () => {
    it("should draw French text for single event", () => {
      const { ctx, operations } = createMockContext();

      drawOverflowIndicator({
        ctx,
        x: 10,
        y: 20,
        count: 1,
        fontSize: 18,
        language: "fr",
      });

      expect(operations).toContain("fillStyle=#FF0000");
      expect(operations).toContain("font=bold 18px Inter");
      expect(operations.some((op) => op.includes("+1 autre événement"))).toBe(
        true,
      );
    });

    it("should draw French text for multiple events", () => {
      const { ctx, operations } = createMockContext();

      drawOverflowIndicator({
        ctx,
        x: 10,
        y: 20,
        count: 3,
        fontSize: 18,
        language: "fr",
      });

      expect(operations.some((op) => op.includes("+3 autres événements"))).toBe(
        true,
      );
    });

    it("should draw English text when specified", () => {
      const { ctx, operations } = createMockContext();

      drawOverflowIndicator({
        ctx,
        x: 10,
        y: 20,
        count: 5,
        fontSize: 18,
        language: "en",
      });

      expect(operations.some((op) => op.includes("+5 more"))).toBe(true);
    });
  });

  describe("sortEventsByPriority", () => {
    it("should put all-day events first", () => {
      const events = [
        {
          event: {
            id: "1",
            title: "Timed Event",
            start: new Date("2024-01-15T09:00:00"),
            end: new Date("2024-01-15T10:00:00"),
            allDay: false,
          },
          startsOnDay: true,
          endsOnDay: true,
        },
        {
          event: {
            id: "2",
            title: "All Day Event",
            start: new Date("2024-01-15"),
            end: new Date("2024-01-15"),
            allDay: true,
          },
          startsOnDay: true,
          endsOnDay: true,
        },
      ];

      const sorted = sortEventsByPriority(events);

      expect(sorted[0].event.allDay).toBe(true);
      expect(sorted[1].event.allDay).toBe(false);
    });

    it("should sort by start time for timed events", () => {
      const events = [
        {
          event: {
            id: "1",
            title: "Event 2",
            start: new Date("2024-01-15T10:00:00"),
            end: new Date("2024-01-15T11:00:00"),
            allDay: false,
          },
          startsOnDay: true,
          endsOnDay: true,
        },
        {
          event: {
            id: "2",
            title: "Event 1",
            start: new Date("2024-01-15T09:00:00"),
            end: new Date("2024-01-15T10:00:00"),
            allDay: false,
          },
          startsOnDay: true,
          endsOnDay: true,
        },
      ];

      const sorted = sortEventsByPriority(events);

      expect(sorted[0].event.start.getHours()).toBe(9);
      expect(sorted[1].event.start.getHours()).toBe(10);
    });

    it("should maintain order for all-day events", () => {
      const events = [
        {
          event: {
            id: "1",
            title: "Event B",
            start: new Date("2024-01-15T00:00:00"),
            end: new Date("2024-01-15T00:00:00"),
            allDay: true,
          },
          startsOnDay: true,
          endsOnDay: true,
        },
        {
          event: {
            id: "2",
            title: "Event A",
            start: new Date("2024-01-14T00:00:00"),
            end: new Date("2024-01-14T00:00:00"),
            allDay: true,
          },
          startsOnDay: true,
          endsOnDay: true,
        },
      ];

      const sorted = sortEventsByPriority(events);

      // Should sort by start date even for all-day events
      expect(sorted[0].event.start < sorted[1].event.start).toBe(true);
      expect(sorted[0].event.id).toBe("2"); // Event A (Jan 14) should be first
      expect(sorted[1].event.id).toBe("1"); // Event B (Jan 15) should be second
    });
  });
});
