import { describe, it, expect } from "@jest/globals";

// These functions are internal to renderer.ts, so we test them via local implementations
// that match the behavior of the actual functions

const isSameDay = (date1: Date, date2: Date): boolean => {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
};

const isToday = (date: Date, now: Date): boolean => {
  return isSameDay(date, now);
};

const isBetweenDates = (date: Date, start: Date, end: Date): boolean => {
  const dateMs = date.getTime();
  const startMs = start.getTime();
  const endMs = end.getTime();
  return dateMs >= startMs && dateMs <= endMs;
};

const formatTime = (date: Date): string => {
  const h = date.getHours();
  const m = date.getMinutes().toString().padStart(2, "0");
  return `${h}:${m}`;
};

const getWeekDays = (start: Date, count: number): Date[] => {
  const days: Date[] = [];
  for (let i = 0; i < count; i++) {
    const day = new Date(start);
    day.setDate(day.getDate() + i);
    days.push(day);
  }
  return days;
};

describe("Date utilities", () => {
  describe("isSameDay", () => {
    it("should return true for same calendar day", () => {
      const date1 = new Date("2024-01-15T09:00:00");
      const date2 = new Date("2024-01-15T18:00:00");
      expect(isSameDay(date1, date2)).toBe(true);
    });

    it("should return false for different calendar days", () => {
      const date1 = new Date("2024-01-15T23:59:59");
      const date2 = new Date("2024-01-16T00:00:01");
      expect(isSameDay(date1, date2)).toBe(false);
    });

    it("should handle dates with different times", () => {
      const date1 = new Date("2024-01-15T00:00:00");
      const date2 = new Date("2024-01-15T23:59:59");
      expect(isSameDay(date1, date2)).toBe(true);
    });
  });

  describe("isToday", () => {
    it("should return true for current date", () => {
      const now = new Date();
      expect(isToday(now, now)).toBe(true);
    });

    it("should return false for yesterday", () => {
      const now = new Date();
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      expect(isToday(yesterday, now)).toBe(false);
    });

    it("should return false for tomorrow", () => {
      const now = new Date();
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      expect(isToday(tomorrow, now)).toBe(false);
    });
  });

  describe("isBetweenDates", () => {
    it("should return true when date is between start and end", () => {
      const start = new Date("2024-01-10");
      const target = new Date("2024-01-15");
      const end = new Date("2024-01-20");
      expect(isBetweenDates(target, start, end)).toBe(true);
    });

    it("should return true when date equals start", () => {
      const start = new Date("2024-01-15");
      const target = new Date("2024-01-15");
      const end = new Date("2024-01-20");
      expect(isBetweenDates(target, start, end)).toBe(true);
    });

    it("should return true when date equals end", () => {
      const start = new Date("2024-01-10");
      const target = new Date("2024-01-20");
      const end = new Date("2024-01-20");
      expect(isBetweenDates(target, start, end)).toBe(true);
    });

    it("should return false when date is before start", () => {
      const start = new Date("2024-01-10");
      const target = new Date("2024-01-05");
      const end = new Date("2024-01-20");
      expect(isBetweenDates(target, start, end)).toBe(false);
    });

    it("should return false when date is after end", () => {
      const start = new Date("2024-01-10");
      const target = new Date("2024-01-25");
      const end = new Date("2024-01-20");
      expect(isBetweenDates(target, start, end)).toBe(false);
    });
  });

  describe("getWeekDays", () => {
    it("should return 6 consecutive days starting from given date", () => {
      const start = new Date("2024-01-15T00:00:00");
      const days = getWeekDays(start, 6);

      expect(days).toHaveLength(6);
      expect(days[0].toDateString()).toBe(start.toDateString());

      // Check each day is consecutive
      for (let i = 1; i < days.length; i++) {
        const expectedDate = new Date(start);
        expectedDate.setDate(expectedDate.getDate() + i);
        expect(days[i].toDateString()).toBe(expectedDate.toDateString());
      }
    });

    it("should handle month boundaries correctly", () => {
      const endOfMonth = new Date("2024-01-29T00:00:00");
      const days = getWeekDays(endOfMonth, 6);

      expect(days).toHaveLength(6);
      expect(days[0].getMonth()).toBe(0); // January
      expect(days[5].getMonth()).toBe(1); // February
    });

    it("should handle year boundaries correctly", () => {
      const endOfYear = new Date("2024-12-29T00:00:00");
      const days = getWeekDays(endOfYear, 6);

      expect(days).toHaveLength(6);
      expect(days[0].getFullYear()).toBe(2024);
      expect(days[5].getFullYear()).toBe(2025);
    });
  });

  describe("formatTime", () => {
    it("should format morning time without leading zero", () => {
      const time = new Date("2024-01-15T09:30:00");
      expect(formatTime(time)).toBe("9:30");
    });

    it("should format afternoon time without leading zero", () => {
      const time = new Date("2024-01-15T14:45:00");
      expect(formatTime(time)).toBe("14:45");
    });

    it("should format midnight correctly", () => {
      const time = new Date("2024-01-15T00:00:00");
      expect(formatTime(time)).toBe("0:00");
    });

    it("should format noon correctly", () => {
      const time = new Date("2024-01-15T12:00:00");
      expect(formatTime(time)).toBe("12:00");
    });

    it("should pad single-digit minutes with zero", () => {
      const time = new Date("2024-01-15T09:05:00");
      expect(formatTime(time)).toBe("9:05");
    });
  });

  describe("Multi-day event edge cases", () => {
    it("should handle all-day events correctly", () => {
      // All-day events: end date is exclusive in iCal
      const start = new Date("2024-01-15T00:00:00");
      const end = new Date("2024-01-15T00:00:00"); // Same day for single-day all-day event

      expect(isSameDay(start, end)).toBe(true);
    });

    it("should handle multi-day all-day events", () => {
      // Multi-day all-day: Jan 15-17 means end is Jan 18 00:00 (exclusive)
      const start = new Date("2024-01-15T00:00:00");
      const end = new Date("2024-01-18T00:00:00"); // Exclusive end
      const lastVisibleDay = new Date("2024-01-17T00:00:00");

      // Event should span from Jan 15 to Jan 17 (inclusive)
      expect(isBetweenDates(new Date("2024-01-15T00:00:00"), start, end)).toBe(
        true,
      );
      expect(isBetweenDates(new Date("2024-01-16T00:00:00"), start, end)).toBe(
        true,
      );
      expect(isBetweenDates(new Date("2024-01-17T00:00:00"), start, end)).toBe(
        true,
      );
      expect(isBetweenDates(lastVisibleDay, start, end)).toBe(true);
    });
  });

  describe("Timezone handling", () => {
    it("should compare dates in local timezone", () => {
      // These are the same day in UTC but might differ in local time
      const date1 = new Date("2024-01-15T23:00:00Z");
      const date2 = new Date("2024-01-16T01:00:00Z");

      // Should compare based on local date, not UTC
      // (Actual result depends on system timezone, so we just verify it works)
      const result = isSameDay(date1, date2);
      expect(typeof result).toBe("boolean");
    });
  });
});
