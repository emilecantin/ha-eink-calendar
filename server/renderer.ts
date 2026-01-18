import { createCanvas, Canvas, CanvasRenderingContext2D, registerFont } from "canvas";
import { format, startOfWeek, endOfWeek, addDays, startOfDay, isSameDay, isWithinInterval, differenceInDays, isWeekend } from "date-fns";
import { fr } from "date-fns/locale";
import crypto from "crypto";
import path from "path";

// Register Inter font family
const fontsDir = path.join(__dirname, "fonts");
registerFont(path.join(fontsDir, "Inter-Regular.ttf"), { family: "Inter", weight: "normal" });
registerFont(path.join(fontsDir, "Inter-Medium.ttf"), { family: "Inter", weight: "500" });
registerFont(path.join(fontsDir, "Inter-Bold.ttf"), { family: "Inter", weight: "bold" });

// Display dimensions
// Portrait mode (rotated 90° for display): 984 wide × 1304 tall
const PORTRAIT_W = 984;
const PORTRAIT_H = 1304;

// Landscape mode (native display orientation): 1304 wide × 984 tall
const LANDSCAPE_W = 1304;
const LANDSCAPE_H = 984;

// Portrait section heights
const TODAY_SECTION_HEIGHT = 450;
const WEEK_SECTION_HEIGHT = 600;
const UPCOMING_SECTION_HEIGHT = 254;

// Landscape layout dimensions
const LANDSCAPE_LEFT_WIDTH = 400;  // Today section
const LANDSCAPE_RIGHT_WIDTH = 904; // 6 days + upcoming (1304 - 400)
const LANDSCAPE_WEEK_HEIGHT = 700; // 6 days section
const LANDSCAPE_UPCOMING_HEIGHT = 284; // Upcoming section (984 - 700)

// Colors
const COLOR_BLACK = "#000000";
const COLOR_WHITE = "#FFFFFF";
const COLOR_RED = "#FF0000";

// Layout constants
const MARGIN = 16;

// Layout type
export type LayoutMode = "portrait" | "landscape";

// Legend item for calendar icons
export interface LegendItem {
  icon: string;
  name: string;
}

// Vertical offset adjustments for icons (fraction of font size to shift)
// Positive = shift down, negative = shift up

// For center alignment with text (used in TODAY and UPCOMING sections)
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

// For bottom alignment with time text (used in WEEK section)
// Aligns icon bottom with "09:00" text bottom
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

function getIconCenterOffset(icon: string, fontSize: number): number {
  const factor = ICON_CENTER_OFFSETS[icon] || 0;
  return factor * fontSize;
}

function getIconBottomOffset(icon: string, fontSize: number): number {
  const factor = ICON_BOTTOM_OFFSETS[icon] || 0;
  return factor * fontSize;
}

export interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay?: boolean;
  calendarColor?: string;
  calendarIcon?: string; // Icon/letter to identify the calendar
}

// Weather forecast for a single day
export interface DayForecast {
  date: Date;
  condition: string;  // sunny, cloudy, snowy, rainy, etc.
  tempHigh: number | null;
  tempLow: number | null;
}

// Weather icon mapping (condition -> character)
const WEATHER_ICONS: { [condition: string]: string } = {
  "sunny": "☀",
  "clear": "☀",
  "clear-night": "☀",
  "partlycloudy": "⛅",
  "cloudy": "☁",
  "fog": "🌫",
  "hail": "🌨",
  "lightning": "⚡",
  "lightning-rainy": "⛈",
  "pouring": "🌧",
  "rainy": "🌧",
  "snowy": "❄",
  "snowy-rainy": "🌨",
  "windy": "💨",
  "windy-variant": "💨",
  "exceptional": "⚠",
};

// Get weather icon for a condition
function getWeatherIcon(condition: string): string {
  return WEATHER_ICONS[condition.toLowerCase()] || "?";
}

// Get forecast for a specific date from array
function getForecastForDate(forecasts: DayForecast[], date: Date): DayForecast | undefined {
  return forecasts.find(f => isSameDay(f.date, date));
}

export interface RenderedCalendar {
  blackLayer: Buffer;
  redLayer: Buffer;
  etag: string;
  timestamp: Date;
}

function capitalize(text: string): string {
  return text.replace(/^(\w)/, (s) => s.toLocaleUpperCase());
}

function formatTime(date: Date): string {
  return format(date, "HH:mm");
}

function truncateText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
  const metrics = ctx.measureText(text);
  if (metrics.width <= maxWidth) return text;

  let truncated = text;
  while (truncated.length > 0 && ctx.measureText(truncated + "...").width > maxWidth) {
    truncated = truncated.slice(0, -1);
  }
  return truncated + "...";
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number, maxLines: number): string[] {
  const words = text.split(' ');
  const lines: string[] = [];
  let currentLine = '';
  let wordIndex = 0;

  for (; wordIndex < words.length; wordIndex++) {
    const word = words[wordIndex];
    const testLine = currentLine ? `${currentLine} ${word}` : word;
    if (ctx.measureText(testLine).width <= maxWidth) {
      currentLine = testLine;
    } else {
      if (currentLine) {
        lines.push(currentLine);
        if (lines.length >= maxLines) break;
      }
      currentLine = word;
    }
  }

  if (currentLine && lines.length < maxLines) {
    lines.push(currentLine);
    wordIndex++; // Mark that we consumed this word
  }

  // Check if there's remaining text that didn't fit
  const hasMoreText = wordIndex < words.length;

  // Truncate last line if needed
  if (lines.length > 0) {
    const lastIndex = lines.length - 1;

    if (hasMoreText) {
      // There's more text that didn't fit - force ellipsis
      let lastLine = lines[lastIndex];
      while (lastLine.length > 0 && ctx.measureText(lastLine + "...").width > maxWidth) {
        lastLine = lastLine.slice(0, -1);
      }
      lines[lastIndex] = lastLine + "...";
    } else if (ctx.measureText(lines[lastIndex]).width > maxWidth) {
      // Last line is too wide (single long word)
      lines[lastIndex] = truncateText(ctx, lines[lastIndex], maxWidth);
    }
  }

  return lines;
}

function drawTodaySection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean
): void {
  const sectionY = 0;
  const sectionHeight = TODAY_SECTION_HEIGHT;

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 3;
    ctx.strokeRect(MARGIN, sectionY + MARGIN, PORTRAIT_W - 2 * MARGIN, sectionHeight - MARGIN);
  }

  // Header area
  const headerX = MARGIN + 10;
  const headerY = sectionY + MARGIN + 10;

  if (!isRed) {
    // Date header
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "bold 28px Inter";
    const dateText = `AUJOURD'HUI - ${capitalize(format(today, "EEEE d MMMM yyyy", { locale: fr }))}`;
    ctx.fillText(dateText, headerX, headerY);

    // Separator line (below the header text)
    ctx.beginPath();
    ctx.moveTo(headerX, headerY + 35);
    ctx.lineTo(PORTRAIT_W - MARGIN - 10, headerY + 35);
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Event list
  const eventStartY = headerY + 50;
  const eventLineHeight = 36;
  const maxEvents = 7;

  const todayEvents = events
    .filter((e) => isSameDay(e.start, today) || (e.allDay && isSameDay(e.start, today)))
    .sort((a, b) => a.start.getTime() - b.start.getTime())
    .slice(0, maxEvents);

  // Fixed width for time column (fits "00:00 - 00:00")
  const timeColumnWidth = 160;

  todayEvents.forEach((event, index) => {
    const y = eventStartY + index * eventLineHeight;
    const timeStr = event.allDay
      ? "Journée"
      : `${formatTime(event.start)} - ${formatTime(event.end)}`;

    if (!isRed) {
      ctx.fillStyle = COLOR_BLACK;
      ctx.font = "bold 20px Inter";
      ctx.fillText(timeStr, headerX, y + 20);

      // Calendar icon + title
      ctx.font = "20px Inter";
      let titleX = headerX + timeColumnWidth;
      if (event.calendarIcon) {
        const iconOffset = getIconCenterOffset(event.calendarIcon, 20);
        ctx.fillText(event.calendarIcon, titleX, y + 20 + iconOffset);
        titleX += 22;
      }
      const maxTitleWidth = PORTRAIT_W - titleX - MARGIN - 20;
      const truncatedTitle = truncateText(ctx, event.title, maxTitleWidth);
      ctx.fillText(truncatedTitle, titleX, y + 20);
    }
  });

  // Show overflow indicator if needed
  const totalTodayEvents = events.filter((e) => isSameDay(e.start, today)).length;
  if (totalTodayEvents > maxEvents && !isRed) {
    const y = eventStartY + maxEvents * eventLineHeight;
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "italic 16px Inter";
    ctx.fillText(`... et ${totalTodayEvents - maxEvents} de plus`, headerX, y + 16);
  }
}

function drawWeekSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean
): void {
  const sectionY = TODAY_SECTION_HEIGHT;
  const sectionHeight = WEEK_SECTION_HEIGHT;
  // Start from tomorrow, show 7 days rolling window
  const tomorrow = addDays(today, 1);

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 3;
    ctx.strokeRect(MARGIN, sectionY + MARGIN, PORTRAIT_W - 2 * MARGIN, sectionHeight - 2 * MARGIN);
  }

  // Section header
  const headerY = sectionY + MARGIN + 5;
  if (!isRed) {
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "bold 24px Inter";
    ctx.fillText("LES 7 PROCHAINS JOURS", MARGIN + 10, headerY);
  }

  // Day columns - start after header text (24px font + padding)
  const gridY = headerY + 32;
  const gridHeight = sectionHeight - 80;
  const dayWidth = (PORTRAIT_W - 2 * MARGIN - 20) / 7;
  const dayHeaderHeight = 55;

  for (let d = 0; d < 7; d++) {
    const day = addDays(tomorrow, d);
    const isWeekendDay = isWeekend(day);
    const dayX = MARGIN + 10 + d * dayWidth;

    // Day header background for weekend days (red layer)
    if (isWeekendDay && isRed) {
      ctx.fillStyle = COLOR_RED;
      ctx.fillRect(dayX, gridY, dayWidth - 2, dayHeaderHeight);
    }

    if (!isRed) {
      // Day column border
      ctx.strokeStyle = COLOR_BLACK;
      ctx.lineWidth = 2;
      ctx.strokeRect(dayX, gridY, dayWidth - 4, gridHeight);

      // Day header border
      ctx.beginPath();
      ctx.moveTo(dayX, gridY + dayHeaderHeight);
      ctx.lineTo(dayX + dayWidth - 4, gridY + dayHeaderHeight);
      ctx.lineWidth = 2;
      ctx.stroke();

      // Day name and number (skip for weekend - drawn with white text on red)
      if (!isWeekendDay) {
        ctx.fillStyle = COLOR_BLACK;
        ctx.font = "bold 18px Inter";
        const dayName = capitalize(format(day, "EEEEE", { locale: fr }));
        const dayNameWidth = ctx.measureText(dayName).width;
        ctx.fillText(dayName, dayX + (dayWidth - dayNameWidth) / 2, gridY + 5);

        ctx.font = "bold 28px Inter";
        const dayNum = format(day, "d");
        const dayNumWidth = ctx.measureText(dayNum).width;
        ctx.fillText(dayNum, dayX + (dayWidth - dayNumWidth) / 2, gridY + 26);
      }
    }

    // Draw weekend day name/number in white on red background (red layer)
    if (isWeekendDay && isRed) {
      ctx.fillStyle = COLOR_WHITE;
      ctx.font = "bold 18px Inter";
      const dayName = capitalize(format(day, "EEEEE", { locale: fr }));
      const dayNameWidth = ctx.measureText(dayName).width;
      ctx.fillText(dayName, dayX + (dayWidth - dayNameWidth) / 2, gridY + 5);

      ctx.font = "bold 28px Inter";
      const dayNum = format(day, "d");
      const dayNumWidth = ctx.measureText(dayNum).width;
      ctx.fillText(dayNum, dayX + (dayWidth - dayNumWidth) / 2, gridY + 26);
    }

    // Day events - include events that start on this day OR span across this day
    const dayEventsUnsorted = events
      .filter((e) => {
        const startsOnDay = isSameDay(e.start, day);
        const spansDay = e.start < day && e.end > day;
        return startsOnDay || spansDay;
      })
      .sort((a, b) => {
        // All-day events first, then by start time
        if (a.allDay && !b.allDay) return -1;
        if (!a.allDay && b.allDay) return 1;
        return a.start.getTime() - b.start.getTime();
      });

    const eventAreaTop = gridY + dayHeaderHeight + 8;
    const eventAreaHeight = gridHeight - dayHeaderHeight - 30; // Leave room for overflow indicator
    const eventHeight = Math.floor(eventAreaHeight / 7); // Fit ~7 events (with 2-line titles)
    const maxEventsToShow = 7;
    const dayEvents = dayEventsUnsorted.slice(0, maxEventsToShow);
    const hasMoreEvents = dayEventsUnsorted.length > maxEventsToShow;

    dayEvents.forEach((event, index) => {
      const eventY = eventAreaTop + index * eventHeight;

      if (!isRed) {
        ctx.fillStyle = COLOR_BLACK;
        ctx.font = "bold 16px Inter";

        // Determine time/indicator string
        const isMultiDay = !isSameDay(event.start, event.end);
        const startsToday = isSameDay(event.start, day);
        // For all-day events, end date is exclusive (iCal convention)
        // So the last day of the event is end - 1 day
        // For all-day events with exclusive end dates (end != start), subtract a day
        // If start == end (single-day all-day), don't subtract
        const lastDay = event.allDay && !isSameDay(event.start, event.end)
          ? addDays(event.end, -1)
          : event.end;
        const endsToday = isSameDay(lastDay, day);

        let timeStr = "";
        let endTimeStr = "";

        if (event.allDay) {
          // Draw line with triangle caps for all-day events
          const lineY = eventY + 5;
          const lineLeft = dayX + 5;
          const lineRight = dayX + dayWidth - 10;
          const triSize = 6;

          // Draw the line
          ctx.beginPath();
          ctx.moveTo(lineLeft + (startsToday ? triSize : 0), lineY);
          ctx.lineTo(lineRight - (endsToday ? triSize : 0), lineY);
          ctx.strokeStyle = COLOR_BLACK;
          ctx.lineWidth = 2;
          ctx.stroke();

          // Draw start triangle (pointing right) if starts today
          if (startsToday) {
            ctx.beginPath();
            ctx.moveTo(lineLeft, lineY - triSize);
            ctx.lineTo(lineLeft + triSize, lineY);
            ctx.lineTo(lineLeft, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }

          // Draw end triangle (pointing left) if ends today
          if (endsToday) {
            ctx.beginPath();
            ctx.moveTo(lineRight, lineY - triSize);
            ctx.lineTo(lineRight - triSize, lineY);
            ctx.lineTo(lineRight, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }
        } else if (isMultiDay) {
          // Multi-day timed event
          if (startsToday) {
            timeStr = formatTime(event.start) + " ▶";
          } else if (endsToday) {
            timeStr = "◀ " + formatTime(event.end);
          } else {
            timeStr = "◀ ▶";
          }
        } else {
          // Normal timed event
          timeStr = formatTime(event.start);
          endTimeStr = formatTime(event.end);
        }

        ctx.fillText(timeStr, dayX + 5, eventY);

        // End time aligned right
        if (endTimeStr) {
          const endTimeWidth = ctx.measureText(endTimeStr).width;
          ctx.fillText(endTimeStr, dayX + dayWidth - endTimeWidth - 8, eventY);
        }

        // Calendar icon centered horizontally, center-aligned but capped so it doesn't go below time baseline
        if (event.calendarIcon) {
          const iconWidth = ctx.measureText(event.calendarIcon).width;
          const iconX = dayX + (dayWidth - iconWidth) / 2;
          // Use center alignment, but if that would put icon below baseline, bump it up
          const centerOffset = getIconCenterOffset(event.calendarIcon, 16);
          const bottomOffset = getIconBottomOffset(event.calendarIcon, 16);
          const iconOffset = Math.min(centerOffset, bottomOffset);
          ctx.fillText(event.calendarIcon, iconX, eventY + iconOffset);
        }

        // Title (2 lines max)
        ctx.font = "17px Inter";
        const titleMaxWidth = dayWidth - 12;
        const titleLines = wrapText(ctx, event.title, titleMaxWidth, 2);
        titleLines.forEach((line, lineIndex) => {
          ctx.fillText(line, dayX + 5, eventY + 19 + lineIndex * 18);
        });
      }
    });

    // Red overflow indicator - positioned where the next event would go
    if (hasMoreEvents && isRed) {
      const overflowY = eventAreaTop + maxEventsToShow * eventHeight;
      const moreCount = dayEventsUnsorted.length - maxEventsToShow;
      ctx.fillStyle = COLOR_RED;
      ctx.font = "bold 14px Inter";
      ctx.fillText(`+${moreCount} autres`, dayX + 5, overflowY);
    }
  }
}

function drawUpcomingSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean
): void {
  const sectionY = TODAY_SECTION_HEIGHT + WEEK_SECTION_HEIGHT;
  const sectionHeight = UPCOMING_SECTION_HEIGHT;

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 3;
    ctx.strokeRect(MARGIN, sectionY, PORTRAIT_W - 2 * MARGIN, sectionHeight - MARGIN);
  }

  // Section header
  if (!isRed) {
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "bold 22px Inter";
    ctx.fillText("À VENIR", MARGIN + 10, sectionY + 25);
  }

  // Filter upcoming events - multi-day events and all-day events beyond the 7-day rolling window
  // The week section shows today+1 through today+7, so "À VENIR" starts at today+8
  const windowEnd = startOfDay(addDays(today, 8));
  const upcomingEvents = events
    .filter((e) => {
      const isMultiDay = differenceInDays(e.end, e.start) >= 1;
      const startsAfterWindow = e.start >= windowEnd;
      return (isMultiDay || e.allDay) && startsAfterWindow;
    })
    .sort((a, b) => a.start.getTime() - b.start.getTime())
    .slice(0, 8);

  // Two-column layout
  const colWidth = (PORTRAIT_W - 2 * MARGIN - 30) / 2;
  const eventLineHeight = 36;
  const startY = sectionY + 55;

  const maxRows = 4;
  upcomingEvents.forEach((event, index) => {
    const col = Math.floor(index / maxRows);
    const row = index % maxRows;
    const x = MARGIN + 10 + col * (colWidth + 20);
    const y = startY + row * eventLineHeight;

    if (!isRed) {
      ctx.fillStyle = COLOR_BLACK;
      ctx.font = "bold 19px Inter";

      // Format date range
      const isMultiDay = differenceInDays(event.end, event.start) >= 1;
      let dateStr: string;
      if (isMultiDay) {
        dateStr = `${format(event.start, "MMM d", { locale: fr })}-${format(event.end, "d")}`;
      } else {
        dateStr = format(event.start, "MMM d", { locale: fr });
      }
      dateStr = dateStr.toUpperCase();

      ctx.fillText(dateStr, x, y);

      // Calendar icon + title
      let titleX = x + 105;
      if (event.calendarIcon) {
        ctx.font = "18px Inter";
        const iconOffset = getIconCenterOffset(event.calendarIcon, 18);
        ctx.fillText(event.calendarIcon, titleX, y + iconOffset);
        titleX += 20;
      }

      ctx.font = "19px Inter";
      const maxTitleWidth = colWidth - 115 - (event.calendarIcon ? 20 : 0);
      const truncatedTitle = truncateText(ctx, event.title, maxTitleWidth);
      ctx.fillText(truncatedTitle, titleX, y);
    }

    // Red bar for multi-day events (to distinguish from single all-day events)
    const isMultiDay = differenceInDays(event.end, event.start) > 1;
    if (isRed && isMultiDay) {
      ctx.fillStyle = COLOR_RED;
      ctx.fillRect(x - 8, y, 3, 14);
    }
  });
}

// ============================================================
// Landscape Layout Drawing Functions
// ============================================================

function drawLandscapeTodaySection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
  legend: LegendItem[] = [],
  weather: DayForecast[] = []
): void {
  const sectionX = 0;
  const sectionWidth = LANDSCAPE_LEFT_WIDTH;
  const sectionHeight = LANDSCAPE_H;

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 2;
    ctx.strokeRect(MARGIN, MARGIN, sectionWidth - MARGIN, sectionHeight - 2 * MARGIN);
  }

  // Header - standardized style matching day columns
  const headerX = MARGIN + 10;
  const headerY = MARGIN;
  const headerHeight = 70;
  const isWeekendDay = isWeekend(today);

  // Weekend header background (red layer)
  if (isWeekendDay && isRed) {
    ctx.fillStyle = COLOR_RED;
    ctx.fillRect(MARGIN + 1, headerY + 1, sectionWidth - MARGIN - 2, headerHeight - 1);
  }

  // Header text - white on red for weekends, black otherwise
  if ((isWeekendDay && isRed) || (!isWeekendDay && !isRed)) {
    ctx.fillStyle = isWeekendDay ? COLOR_WHITE : COLOR_BLACK;
    // Day name
    ctx.font = "bold 22px Inter";
    const dayName = capitalize(format(today, "EEEE", { locale: fr }));
    ctx.fillText(dayName, headerX, headerY + 8);

    // Full date below
    ctx.font = "bold 28px Inter";
    const dateText = format(today, "d MMMM yyyy", { locale: fr });
    ctx.fillText(dateText, headerX, headerY + 36);

    // Weather info on the right side of header: large icon + stacked temps
    const todayForecast = getForecastForDate(weather, today);
    if (todayForecast) {
      const weatherRightEdge = sectionWidth - 15;

      // Temps stacked on the right (skip if null, keep positions stable)
      ctx.font = "bold 20px Inter";
      const hasHigh = todayForecast.tempHigh !== null;
      const hasLow = todayForecast.tempLow !== null;

      let tempWidth = 0;
      if (hasHigh || hasLow) {
        const highTemp = hasHigh ? `${Math.round(todayForecast.tempHigh!)}°` : "";
        const lowTemp = hasLow ? `${Math.round(todayForecast.tempLow!)}°` : "";
        const highMetrics = hasHigh ? ctx.measureText(highTemp) : { width: 0 };
        const lowMetrics = hasLow ? ctx.measureText(lowTemp) : { width: 0 };
        tempWidth = Math.max(highMetrics.width, lowMetrics.width);

        // Keep positions stable: high always on top, low always on bottom
        if (hasHigh) {
          ctx.fillText(highTemp, weatherRightEdge - highMetrics.width, headerY + 12);
        }
        if (hasLow) {
          ctx.fillText(lowTemp, weatherRightEdge - lowMetrics.width, headerY + 38);
        }
      }

      // Large weather icon to the left of temps
      ctx.font = "44px Inter";
      const icon = getWeatherIcon(todayForecast.condition);
      const iconMetrics = ctx.measureText(icon);
      const iconX = tempWidth > 0
        ? weatherRightEdge - tempWidth - 8 - iconMetrics.width
        : weatherRightEdge - iconMetrics.width;
      ctx.fillText(icon, iconX, headerY + 10);
    }
  }

  // Separator line at bottom of header (black layer only)
  if (!isRed) {
    ctx.beginPath();
    ctx.moveTo(MARGIN, headerY + headerHeight);
    ctx.lineTo(sectionWidth, headerY + headerHeight);
    ctx.stroke();
  }

  // Event list - 3 lines per event: time row, then 2 lines for title
  const eventStartY = headerY + headerHeight + 8;
  const lineHeight = 22;
  const eventBlockHeight = lineHeight * 3 + 10; // 3 lines + padding
  const eventWidth = sectionWidth - MARGIN - headerX;

  // Calculate legend height to reserve space
  const legendItemHeight = 18;
  const legendHeaderHeight = 20;
  const legendRows = legend.length > 0 ? Math.ceil(legend.length / 2) : 0;
  const legendHeight = legend.length > 0
    ? legendRows * legendItemHeight + legendHeaderHeight
    : 0;
  const bottomPadding = 20; // Space at very bottom to avoid cutoff
  // Note: overflow indicator is now placed in the event area (where next event would go)
  // so we don't need to reserve separate space for it
  const reservedBottom = bottomPadding + legendHeight;
  const maxEvents = Math.floor((sectionHeight - eventStartY - reservedBottom) / eventBlockHeight);

  const todayEvents = events
    .filter((e) => isSameDay(e.start, today) || (e.allDay && isSameDay(e.start, today)))
    .sort((a, b) => a.start.getTime() - b.start.getTime())
    .slice(0, maxEvents);

  const maxTitleWidth = eventWidth - 10;

  todayEvents.forEach((event, index) => {
    const blockY = eventStartY + index * eventBlockHeight;
    const isMultiDay = !isSameDay(event.start, event.end);
    const startsToday = isSameDay(event.start, today);
    // For all-day events, end date is exclusive (iCal convention)
    // So the last day of the event is end - 1 day
    // For all-day events with exclusive end dates (end != start), subtract a day
        // If start == end (single-day all-day), don't subtract
        const lastDay = event.allDay && !isSameDay(event.start, event.end)
          ? addDays(event.end, -1)
          : event.end;
    const endsToday = isSameDay(lastDay, today);

    if (!isRed) {
      ctx.fillStyle = COLOR_BLACK;
      ctx.font = "bold 18px Inter";

      if (event.allDay) {
        // All-day: horizontal line with triangles (symmetric margins)
        const lineY = blockY + 8;
        const lineLeft = headerX;
        const lineRight = sectionWidth - 10; // Same 10px margin as left (headerX = MARGIN + 10)
        const triSize = 6;

        ctx.beginPath();
        ctx.moveTo(lineLeft + (startsToday ? triSize : 0), lineY);
        ctx.lineTo(lineRight - (endsToday ? triSize : 0), lineY);
        ctx.strokeStyle = COLOR_BLACK;
        ctx.lineWidth = 2;
        ctx.stroke();

        if (startsToday) {
          ctx.beginPath();
          ctx.moveTo(lineLeft, lineY - triSize);
          ctx.lineTo(lineLeft + triSize, lineY);
          ctx.lineTo(lineLeft, lineY + triSize);
          ctx.closePath();
          ctx.fill();
        }
        if (endsToday) {
          ctx.beginPath();
          ctx.moveTo(lineRight, lineY - triSize);
          ctx.lineTo(lineRight - triSize, lineY);
          ctx.lineTo(lineRight, lineY + triSize);
          ctx.closePath();
          ctx.fill();
        }

        // Icon centered on the line
        if (event.calendarIcon) {
          const iconWidth = ctx.measureText(event.calendarIcon).width;
          const iconX = lineLeft + (lineRight - lineLeft - iconWidth) / 2;
          const iconOffset = getIconCenterOffset(event.calendarIcon, 18);
          ctx.fillText(event.calendarIcon, iconX, blockY + iconOffset);
        }
      } else if (isMultiDay) {
        // Multi-day: time with arrows
        let timeStr = "";
        if (startsToday) {
          timeStr = formatTime(event.start) + " ▶";
        } else if (endsToday) {
          timeStr = "◀ " + formatTime(event.end);
        } else {
          timeStr = "◀ ▶";
        }
        ctx.fillText(timeStr, headerX, blockY);

        // Icon centered
        if (event.calendarIcon) {
          const iconWidth = ctx.measureText(event.calendarIcon).width;
          const iconX = headerX + (eventWidth - iconWidth) / 2;
          const iconOffset = getIconCenterOffset(event.calendarIcon, 18);
          ctx.fillText(event.calendarIcon, iconX, blockY + iconOffset);
        }
      } else {
        // Regular event: start time left, end time right, icon centered
        ctx.fillText(formatTime(event.start), headerX, blockY);

        const endTimeStr = formatTime(event.end);
        const endTimeWidth = ctx.measureText(endTimeStr).width;
        ctx.fillText(endTimeStr, headerX + eventWidth - endTimeWidth - 5, blockY);

        // Icon centered
        if (event.calendarIcon) {
          const iconWidth = ctx.measureText(event.calendarIcon).width;
          const iconX = headerX + (eventWidth - iconWidth) / 2;
          const iconOffset = getIconCenterOffset(event.calendarIcon, 18);
          ctx.fillText(event.calendarIcon, iconX, blockY + iconOffset);
        }
      }

      // Lines 2-3: Title (wrapped to 2 lines)
      ctx.font = "20px Inter";
      const titleLines = wrapText(ctx, event.title, maxTitleWidth, 2);
      titleLines.forEach((line, lineIndex) => {
        ctx.fillText(line, headerX, blockY + (lineIndex + 1) * lineHeight);
      });
    }
  });

  // Calculate legend position (at bottom of section)
  const legendX = headerX;
  const legendTop = sectionHeight - bottomPadding - legendHeight;

  // Overflow indicator - positioned where the next event would go, minus a few pixels
  const totalTodayEvents = events.filter((e) => isSameDay(e.start, today)).length;
  if (totalTodayEvents > maxEvents && isRed) {
    const moreCount = totalTodayEvents - maxEvents;
    const y = eventStartY + maxEvents * eventBlockHeight - 6;
    ctx.fillStyle = COLOR_RED;
    ctx.font = "bold 18px Inter";
    ctx.fillText(`+ ${moreCount} autres événements`, headerX, y);
  }

  // Legend at the bottom of the Today section
  if (legend.length > 0 && !isRed) {
    // "Légende" header
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "bold 14px Inter";
    ctx.fillText("Légende", legendX, legendTop);

    // Two-column legend layout
    ctx.font = "14px Inter";
    const colWidth = (sectionWidth - MARGIN - headerX) / 2;
    legend.forEach((item, index) => {
      const col = index % 2;
      const row = Math.floor(index / 2);
      const x = legendX + col * colWidth;
      const y = legendTop + legendHeaderHeight + row * legendItemHeight;

      // Icon
      const iconOffset = getIconCenterOffset(item.icon, 14);
      ctx.fillText(item.icon, x, y + iconOffset);

      // Name
      const nameX = x + 20;
      const maxNameWidth = colWidth - 25;
      const truncatedName = truncateText(ctx, item.name, maxNameWidth);
      ctx.fillText(truncatedName, nameX, y);
    });
  }
}

function drawLandscapeWeekSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
  weather: DayForecast[] = []
): void {
  const sectionX = LANDSCAPE_LEFT_WIDTH;
  const sectionY = 0;
  const sectionWidth = LANDSCAPE_RIGHT_WIDTH;
  const sectionHeight = LANDSCAPE_WEEK_HEIGHT;
  const tomorrow = addDays(today, 1);

  // 6 day columns (no section title)
  // Align with Today section (top at MARGIN) and À venir section (bottom at sectionHeight)
  const gridLeft = sectionX;
  const gridTop = MARGIN;
  const gridRight = sectionX + sectionWidth - MARGIN;
  const gridBottom = sectionHeight;
  const dayWidth = (gridRight - gridLeft) / 6;
  const dayHeaderHeight = 70;

  // Draw section border and shared lines (black layer only)
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 2;

    // Top line (aligned with Today section top)
    ctx.beginPath();
    ctx.moveTo(gridLeft, gridTop);
    ctx.lineTo(gridRight, gridTop);
    ctx.stroke();

    // Right line (full height, covers both 6-day and À venir sections)
    ctx.beginPath();
    ctx.moveTo(gridRight, gridTop);
    ctx.lineTo(gridRight, LANDSCAPE_H - MARGIN);
    ctx.stroke();

    // Header separator line
    ctx.beginPath();
    ctx.moveTo(gridLeft, gridTop + dayHeaderHeight);
    ctx.lineTo(gridRight, gridTop + dayHeaderHeight);
    ctx.stroke();

    // Vertical dividers between columns
    for (let d = 1; d < 6; d++) {
      const dividerX = gridLeft + d * dayWidth;
      ctx.beginPath();
      ctx.moveTo(dividerX, gridTop);
      ctx.lineTo(dividerX, gridBottom);
      ctx.stroke();
    }

    // Bottom line (separates 6-day from À venir)
    ctx.beginPath();
    ctx.moveTo(gridLeft, gridBottom);
    ctx.lineTo(gridRight, gridBottom);
    ctx.stroke();
  }

  for (let d = 0; d < 6; d++) {
    const day = addDays(tomorrow, d);
    const isWeekendDay = isWeekend(day);
    const dayX = gridLeft + d * dayWidth;

    // Day header background for weekend days (red layer)
    if (isWeekendDay && isRed) {
      ctx.fillStyle = COLOR_RED;
      ctx.fillRect(dayX + 1, gridTop + 1, dayWidth - 2, dayHeaderHeight - 1);
    }

    // Get forecast for this day
    const dayForecast = getForecastForDate(weather, day);

    // Helper to draw day header content (used for both weekday and weekend)
    const drawDayHeader = (textColor: string) => {
      ctx.fillStyle = textColor;
      const leftMargin = dayX + 8;
      const rightMargin = dayX + dayWidth - 8;

      // 3-letter day name (left-aligned) - LUN, MAR, MER, JEU, VEN, SAM, DIM
      ctx.font = "bold 18px Inter";
      const dayName = format(day, "EEE", { locale: fr }).toUpperCase().slice(0, 3);
      ctx.fillText(dayName, leftMargin, gridTop + 10);

      // Day number below day name (left-aligned)
      ctx.font = "bold 32px Inter";
      const dayNum = format(day, "d");
      ctx.fillText(dayNum, leftMargin, gridTop + 34);

      // Weather on the right side: icon + stacked temps (skip blanks, keep positions stable)
      if (dayForecast) {
        const hasHigh = dayForecast.tempHigh !== null;
        const hasLow = dayForecast.tempLow !== null;

        // Stacked temps (right-aligned, skip if null)
        ctx.font = "bold 16px Inter";
        let tempWidth = 0;
        if (hasHigh || hasLow) {
          const highTemp = hasHigh ? `${Math.round(dayForecast.tempHigh!)}°` : "";
          const lowTemp = hasLow ? `${Math.round(dayForecast.tempLow!)}°` : "";
          const highMetrics = hasHigh ? ctx.measureText(highTemp) : { width: 0 };
          const lowMetrics = hasLow ? ctx.measureText(lowTemp) : { width: 0 };
          tempWidth = Math.max(highMetrics.width, lowMetrics.width);

          // Keep positions stable: high always on top, low always on bottom
          if (hasHigh) {
            ctx.fillText(highTemp, rightMargin - highMetrics.width, gridTop + 16);
          }
          if (hasLow) {
            ctx.fillText(lowTemp, rightMargin - lowMetrics.width, gridTop + 36);
          }
        }

        // Weather icon to the left of temps
        ctx.font = "32px Inter";
        const icon = getWeatherIcon(dayForecast.condition);
        const iconMetrics = ctx.measureText(icon);
        const iconX = tempWidth > 0
          ? rightMargin - tempWidth - 6 - iconMetrics.width
          : rightMargin - iconMetrics.width;
        ctx.fillText(icon, iconX, gridTop + 18);
      }
    };

    // Draw header content for weekdays (black layer)
    if (!isRed && !isWeekendDay) {
      drawDayHeader(COLOR_BLACK);
    }

    // Draw header content for weekends (red layer, white text)
    if (isRed && isWeekendDay) {
      drawDayHeader(COLOR_WHITE);
    }

    // Day events
    const dayEventsUnsorted = events
      .filter((e) => {
        const startsOnDay = isSameDay(e.start, day);
        const spansDay = e.start < day && e.end > day;
        return startsOnDay || spansDay;
      })
      .sort((a, b) => {
        if (a.allDay && !b.allDay) return -1;
        if (!a.allDay && b.allDay) return 1;
        return a.start.getTime() - b.start.getTime();
      });

    const eventAreaTop = gridTop + dayHeaderHeight + 8;
    const eventAreaHeight = sectionHeight - gridTop - dayHeaderHeight - 40;
    const eventHeight = Math.floor(eventAreaHeight / 8);
    const maxEventsToShow = 8;
    const dayEvents = dayEventsUnsorted.slice(0, maxEventsToShow);
    const hasMoreEvents = dayEventsUnsorted.length > maxEventsToShow;

    dayEvents.forEach((event, index) => {
      const eventY = eventAreaTop + index * eventHeight;

      if (!isRed) {
        ctx.fillStyle = COLOR_BLACK;
        ctx.font = "bold 14px Inter";

        const isMultiDay = !isSameDay(event.start, event.end);
        const startsToday = isSameDay(event.start, day);
        // For all-day events, end date is exclusive (iCal convention)
        // So the last day of the event is end - 1 day
        // For all-day events with exclusive end dates (end != start), subtract a day
        // If start == end (single-day all-day), don't subtract
        const lastDay = event.allDay && !isSameDay(event.start, event.end)
          ? addDays(event.end, -1)
          : event.end;
        const endsToday = isSameDay(lastDay, day);

        let timeStr = "";
        let endTimeStr = "";

        if (event.allDay) {
          // All-day indicator line
          const lineY = eventY + 5;
          const lineLeft = dayX + 5;
          const lineRight = dayX + dayWidth - 10;
          const triSize = 5;

          ctx.beginPath();
          ctx.moveTo(lineLeft + (startsToday ? triSize : 0), lineY);
          ctx.lineTo(lineRight - (endsToday ? triSize : 0), lineY);
          ctx.strokeStyle = COLOR_BLACK;
          ctx.lineWidth = 2;
          ctx.stroke();

          if (startsToday) {
            ctx.beginPath();
            ctx.moveTo(lineLeft, lineY - triSize);
            ctx.lineTo(lineLeft + triSize, lineY);
            ctx.lineTo(lineLeft, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }
          if (endsToday) {
            ctx.beginPath();
            ctx.moveTo(lineRight, lineY - triSize);
            ctx.lineTo(lineRight - triSize, lineY);
            ctx.lineTo(lineRight, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }
        } else if (isMultiDay) {
          if (startsToday) {
            timeStr = formatTime(event.start) + " ▶";
          } else if (endsToday) {
            timeStr = "◀ " + formatTime(event.end);
          } else {
            timeStr = "◀ ▶";
          }
        } else {
          timeStr = formatTime(event.start);
          endTimeStr = formatTime(event.end);
        }

        ctx.fillText(timeStr, dayX + 5, eventY);
        if (endTimeStr) {
          const endTimeWidth = ctx.measureText(endTimeStr).width;
          ctx.fillText(endTimeStr, dayX + dayWidth - endTimeWidth - 8, eventY);
        }

        // Calendar icon
        if (event.calendarIcon) {
          const iconWidth = ctx.measureText(event.calendarIcon).width;
          const iconX = dayX + (dayWidth - iconWidth) / 2;
          const iconOffset = Math.min(
            getIconCenterOffset(event.calendarIcon, 14),
            getIconBottomOffset(event.calendarIcon, 14)
          );
          ctx.fillText(event.calendarIcon, iconX, eventY + iconOffset);
        }

        // Title (2 lines max)
        ctx.font = "16px Inter";
        const titleMaxWidth = dayWidth - 12;
        const titleLines = wrapText(ctx, event.title, titleMaxWidth, 2);
        titleLines.forEach((line, lineIndex) => {
          ctx.fillText(line, dayX + 5, eventY + 17 + lineIndex * 18);
        });
      }
    });

    // Overflow indicator - positioned where the next event would go
    if (hasMoreEvents && isRed) {
      const overflowY = eventAreaTop + maxEventsToShow * eventHeight;
      const moreCount = dayEventsUnsorted.length - maxEventsToShow;
      ctx.fillStyle = COLOR_RED;
      ctx.font = "bold 14px Inter";
      ctx.fillText(`+${moreCount} autres`, dayX + 5, overflowY);
    }
  }
}

function drawLandscapeUpcomingSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean
): void {
  const sectionX = LANDSCAPE_LEFT_WIDTH;
  const sectionY = LANDSCAPE_WEEK_HEIGHT;
  const sectionWidth = LANDSCAPE_RIGHT_WIDTH;
  const sectionHeight = LANDSCAPE_UPCOMING_HEIGHT;

  // Draw section border (only bottom line - top is shared with 6-day, left with Today, right with 6-day)
  const gridRight = sectionX + sectionWidth - MARGIN;
  const gridBottom = sectionY + sectionHeight - MARGIN;
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 2;

    // Bottom line
    ctx.beginPath();
    ctx.moveTo(sectionX, gridBottom);
    ctx.lineTo(gridRight, gridBottom);
    ctx.stroke();
  }

  // Section header
  if (!isRed) {
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "bold 20px Inter";
    ctx.fillText("À VENIR", sectionX + 10, sectionY + 20);
  }

  // Filter upcoming events - beyond the 6-day window
  const windowEnd = startOfDay(addDays(today, 7));
  const upcomingEvents = events
    .filter((e) => {
      const isMultiDay = differenceInDays(e.end, e.start) >= 1;
      const startsAfterWindow = e.start >= windowEnd;
      return (isMultiDay || e.allDay) && startsAfterWindow;
    })
    .sort((a, b) => a.start.getTime() - b.start.getTime())
    .slice(0, 12);

  // Two-column layout
  const colWidth = (sectionWidth - 30) / 2;
  const eventLineHeight = 32;
  const startY = sectionY + 50;

  const maxRows = 6;
  upcomingEvents.forEach((event, index) => {
    const col = Math.floor(index / maxRows);
    const row = index % maxRows;
    const x = sectionX + 10 + col * (colWidth + 10);
    const y = startY + row * eventLineHeight;

    if (!isRed) {
      ctx.fillStyle = COLOR_BLACK;
      ctx.font = "bold 16px Inter";

      const isMultiDay = differenceInDays(event.end, event.start) >= 1;
      let dateStr: string;
      if (isMultiDay) {
        dateStr = `${format(event.start, "MMM d", { locale: fr })}-${format(event.end, "d")}`;
      } else {
        dateStr = format(event.start, "MMM d", { locale: fr });
      }
      dateStr = dateStr.toUpperCase();

      ctx.fillText(dateStr, x, y);

      // Calendar icon + title
      let titleX = x + 110;
      if (event.calendarIcon) {
        ctx.font = "16px Inter";
        const iconOffset = getIconCenterOffset(event.calendarIcon, 16);
        ctx.fillText(event.calendarIcon, titleX, y + iconOffset);
        titleX += 18;
      }

      ctx.font = "16px Inter";
      const maxTitleWidth = colWidth - 120 - (event.calendarIcon ? 18 : 0);
      const truncatedTitle = truncateText(ctx, event.title, maxTitleWidth);
      ctx.fillText(truncatedTitle, titleX, y);
    }

    // Red bar for multi-day events
    const isMultiDay = differenceInDays(event.end, event.start) >= 1;
    if (isRed && isMultiDay) {
      ctx.fillStyle = COLOR_RED;
      ctx.fillRect(x - 6, y + 2, 3, 14);
    }
  });
}

// Display physical dimensions (landscape - final output)
const DISPLAY_W = 1304;
const DISPLAY_H = 984;

export function renderCalendar(events: CalendarEvent[], now: Date, layout: LayoutMode = "portrait", legend: LegendItem[] = [], weather: DayForecast[] = []): RenderedCalendar {
  if (layout === "landscape") {
    return renderCalendarLandscape(events, now, legend, weather);
  }
  return renderCalendarPortrait(events, now, legend, weather);
}

function renderCalendarPortrait(events: CalendarEvent[], now: Date, legend: LegendItem[] = [], weather: DayForecast[] = []): RenderedCalendar {
  // Create canvas in portrait mode for rendering
  const canvas = createCanvas(PORTRAIT_W, PORTRAIT_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Draw all sections (black layer)
  ctx.textBaseline = "top";
  drawTodaySection(ctx, events, now, false);
  drawWeekSection(ctx, events, now, false);
  drawUpcomingSection(ctx, events, now, false);

  // Get black layer image data
  const blackImageData = ctx.getImageData(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Clear and draw red layer
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  drawTodaySection(ctx, events, now, true);
  drawWeekSection(ctx, events, now, true);
  drawUpcomingSection(ctx, events, now, true);

  const redImageData = ctx.getImageData(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Rotate 90° clockwise for landscape display
  // Portrait 984×1304 → Landscape 1304×984
  const rotatedBlack = rotateImageData90CW(blackImageData);
  const rotatedRed = rotateImageData90CW(redImageData);

  // Convert to 1-bit packed bitmaps (now in landscape orientation)
  const blackLayer = imageDataTo1Bit(rotatedBlack, false);
  const redLayer = imageDataTo1Bit(rotatedRed, true);

  // Generate ETag
  const hash = crypto.createHash("md5");
  hash.update(blackLayer);
  hash.update(redLayer);
  const etag = hash.digest("hex");

  return {
    blackLayer,
    redLayer,
    etag,
    timestamp: now,
  };
}

function renderCalendarLandscape(events: CalendarEvent[], now: Date, legend: LegendItem[] = [], weather: DayForecast[] = []): RenderedCalendar {
  // Create canvas directly in landscape mode (no rotation needed)
  const canvas = createCanvas(LANDSCAPE_W, LANDSCAPE_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  // Draw all sections (black layer)
  ctx.textBaseline = "top";
  drawLandscapeTodaySection(ctx, events, now, false, legend, weather);
  drawLandscapeWeekSection(ctx, events, now, false, weather);
  drawLandscapeUpcomingSection(ctx, events, now, false);

  // Get black layer image data
  const blackImageData = ctx.getImageData(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  // Clear and draw red layer
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  drawLandscapeTodaySection(ctx, events, now, true, legend, weather);
  drawLandscapeWeekSection(ctx, events, now, true, weather);
  drawLandscapeUpcomingSection(ctx, events, now, true);

  const redImageData = ctx.getImageData(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  // No rotation needed - already in landscape
  const blackLayer = imageDataTo1Bit(blackImageData, false);
  const redLayer = imageDataTo1Bit(redImageData, true);

  // Generate ETag
  const hash = crypto.createHash("md5");
  hash.update(blackLayer);
  hash.update(redLayer);
  const etag = hash.digest("hex");

  return {
    blackLayer,
    redLayer,
    etag,
    timestamp: now,
  };
}

// Rotate image data 90 degrees clockwise
// Input: PORTRAIT_W × PORTRAIT_H (984 × 1304)
// Output: PORTRAIT_H × PORTRAIT_W (1304 × 984)
function rotateImageData90CW(imageData: { width: number; height: number; data: Uint8ClampedArray }): {
  width: number;
  height: number;
  data: Uint8ClampedArray;
} {
  const { width, height, data } = imageData;
  const newWidth = height;  // 1304
  const newHeight = width;  // 984
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

function imageDataTo1Bit(imageData: { width: number; height: number; data: Uint8ClampedArray }, isRed: boolean): Buffer {
  const { width, height, data } = imageData;
  const bytesPerRow = Math.ceil(width / 8);
  // Waveshare e-paper: 0 = colored, 1 = white/transparent
  // Start with all 1s (white), then clear bits for colored pixels
  const buffer = Buffer.alloc(bytesPerRow * height, 0xFF);

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
        buffer[byteIndex] &= ~(1 << bitIndex);  // Clear bit to 0 for colored pixel
      }
    }
  }

  return buffer;
}

export function extractChunk(layer: Buffer, chunkIndex: 1 | 2): Buffer {
  // Display is in landscape mode: 1304 wide x 984 tall
  // ESP32 expects two 492-row chunks
  // Chunk 1: rows 0-491, Chunk 2: rows 492-983
  const bytesPerRow = Math.ceil(DISPLAY_W / 8);  // 163 bytes
  const halfHeight = Math.ceil(DISPLAY_H / 2);   // 492 rows
  const chunkSize = bytesPerRow * halfHeight;    // 80196 bytes

  if (chunkIndex === 1) {
    return layer.subarray(0, chunkSize);
  } else {
    return layer.subarray(chunkSize);
  }
}

// For debugging: render to PNG
export function renderToPng(events: CalendarEvent[], now: Date, layout: LayoutMode = "portrait", legend: LegendItem[] = [], weather: DayForecast[] = []): Buffer {
  if (layout === "landscape") {
    return renderToPngLandscape(events, now, legend, weather);
  }
  return renderToPngPortrait(events, now, legend, weather);
}

function renderToPngPortrait(events: CalendarEvent[], now: Date, legend: LegendItem[] = [], weather: DayForecast[] = []): Buffer {
  const canvas = createCanvas(PORTRAIT_W, PORTRAIT_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Draw all sections
  ctx.textBaseline = "top";
  drawTodaySection(ctx, events, now, false);
  drawWeekSection(ctx, events, now, false);
  drawUpcomingSection(ctx, events, now, false);

  // Draw red elements on top
  drawTodaySection(ctx, events, now, true);
  drawWeekSection(ctx, events, now, true);
  drawUpcomingSection(ctx, events, now, true);

  // TODO: Add legend and weather support for portrait mode

  return canvas.toBuffer("image/png");
}

function renderToPngLandscape(events: CalendarEvent[], now: Date, legend: LegendItem[] = [], weather: DayForecast[] = []): Buffer {
  const canvas = createCanvas(LANDSCAPE_W, LANDSCAPE_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  // Draw all sections
  ctx.textBaseline = "top";
  drawLandscapeTodaySection(ctx, events, now, false, legend, weather);
  drawLandscapeWeekSection(ctx, events, now, false, weather);
  drawLandscapeUpcomingSection(ctx, events, now, false);

  // Draw red elements on top
  drawLandscapeTodaySection(ctx, events, now, true, legend, weather);
  drawLandscapeWeekSection(ctx, events, now, true, weather);
  drawLandscapeUpcomingSection(ctx, events, now, true);

  return canvas.toBuffer("image/png");
}
