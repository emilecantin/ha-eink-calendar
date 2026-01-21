import {
  createCanvas,
  Canvas,
  CanvasRenderingContext2D,
  registerFont,
  Image,
  loadImage,
} from "canvas";
import {
  drawEventTriangle,
  formatMultiDayTime,
  drawOverflowIndicator,
  sortEventsByPriority,
  type EventWithIndicators,
} from "./event-renderer";
import {
  DISPLAY,
  MARGINS,
  LAYOUT_PORTRAIT,
  LAYOUT_LANDSCAPE,
  TYPOGRAPHY,
  ICON_SIZES,
  EVENT_DIMENSIONS,
  COLORS,
  LAYOUT_MISC,
} from "./layout-config";
import {
  format,
  startOfWeek,
  endOfWeek,
  addDays,
  startOfDay,
  isSameDay,
  isWithinInterval,
  differenceInDays,
  isWeekend,
} from "date-fns";
import { fr } from "date-fns/locale";
import crypto from "crypto";
import path from "path";
import fs from "fs";

// Register Inter font family
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

// Display dimensions - imported from layout-config.ts
const PORTRAIT_W = DISPLAY.PORTRAIT.width;
const PORTRAIT_H = DISPLAY.PORTRAIT.height;
const LANDSCAPE_W = DISPLAY.LANDSCAPE.width;
const LANDSCAPE_H = DISPLAY.LANDSCAPE.height;

// Portrait section heights
const TODAY_SECTION_HEIGHT = LAYOUT_PORTRAIT.TODAY.height;
const WEEK_SECTION_HEIGHT = LAYOUT_PORTRAIT.WEEK.height;
const UPCOMING_SECTION_HEIGHT = LAYOUT_PORTRAIT.UPCOMING.height;

// Landscape layout dimensions
const LANDSCAPE_LEFT_WIDTH = LAYOUT_LANDSCAPE.TODAY.width;
const LANDSCAPE_RIGHT_WIDTH = LAYOUT_LANDSCAPE.RIGHT_PANEL.width;
const LANDSCAPE_WEEK_HEIGHT = LAYOUT_LANDSCAPE.WEEK.height;
const LANDSCAPE_UPCOMING_HEIGHT = LAYOUT_LANDSCAPE.UPCOMING.height;

// Colors - imported from layout-config.ts
const COLOR_BLACK = COLORS.BLACK;
const COLOR_WHITE = COLORS.WHITE;
const COLOR_RED = COLORS.RED;

// Layout constants
const MARGIN = MARGINS.STANDARD;

// Collection icon cache
const collectionIconCache = new Map<string, Canvas>();

// Load collection icon PNG and scale to specified size
async function loadCollectionIcon(
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

// Draw a collection icon at the specified position
async function drawCollectionIcon(
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

// Layout type
export type LayoutMode = "portrait" | "landscape";

// Legend item for calendar icons
export interface LegendItem {
  icon: string;
  name: string;
}

// Indicator data structure for binary sensor display
export interface IndicatorData {
  entityId: string;
  state: "on" | "off";
  label: string;
  icon: string;
  shouldDisplay: boolean;
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
  calendarId?: string; // Entity ID of the calendar this event belongs to
}

// Event filter result with day-specific indicators
interface EventForDay {
  event: CalendarEvent;
  startsOnDay: boolean;
  endsOnDay: boolean;
}

/**
 * Filters events for a specific day and returns them with indicators
 * showing whether each event starts/ends on that day.
 *
 * Includes:
 * - Events that start on this day
 * - Multi-day events that span across this day (started before, end on/after)
 */
function getEventsForDay(events: CalendarEvent[], day: Date): EventForDay[] {
  const dayStart = startOfDay(day);

  return events
    .filter((e) => {
      const startsOnDay = isSameDay(e.start, day);
      const spansDay = e.start < dayStart && e.end >= dayStart;
      return startsOnDay || spansDay;
    })
    .map((e) => ({
      event: e,
      startsOnDay: isSameDay(e.start, day),
      endsOnDay: isSameDay(e.end, day),
    }));
}

/**
 * Gets collection calendar icons for a specific day
 * Returns icons for each collection type found in events on this day
 */
function getCollectionIconsForDay(
  events: CalendarEvent[],
  day: Date,
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
): string[] {
  if (collectionCalendars.length === 0 || collectionTypes.length === 0)
    return [];

  const icons: string[] = [];
  const foundTypes = new Set<string>();

  // Find all collection events on this day
  const collectionEvents = events.filter(
    (e) =>
      e.calendarId &&
      collectionCalendars.includes(e.calendarId) &&
      e.allDay &&
      isSameDay(e.start, day),
  );

  // Keywords for matching event titles to collection types
  const typeKeywords: { [typeName: string]: string[] } = {
    Garbage: ["garbage", "trash", "waste", "déchet", "ordure", "poubelle"],
    Recycling: ["recycling", "recycle", "recyclage", "récupération"],
    Compost: ["compost", "organic", "organique", "food waste"],
    "Yard Waste": ["yard", "green", "vert", "garden"],
    Glass: ["glass", "verre"],
    Paper: ["paper", "papier"],
    Cardboard: ["cardboard", "carton"],
  };

  // Match each event title against collection types using keywords
  for (const event of collectionEvents) {
    const titleLower = event.title.toLowerCase();

    for (const type of collectionTypes) {
      const keywords = typeKeywords[type.name] || [type.name.toLowerCase()];

      if (
        keywords.some((kw) => titleLower.includes(kw)) &&
        !foundTypes.has(type.name)
      ) {
        icons.push(type.icon);
        foundTypes.add(type.name);
      }
    }
  }

  return icons;
}

// Weather forecast for a single day
export interface DayForecast {
  date: Date;
  condition: string; // sunny, cloudy, snowy, rainy, etc.
  tempHigh: number | null;
  tempLow: number | null;
}

// Weather icon mapping (condition -> Unicode symbol)
// These render with Symbola or DejaVu Sans fonts
const WEATHER_ICONS: { [condition: string]: string } = {
  sunny: "☀", // U+2600
  clear: "☀",
  "clear-night": "☽", // U+263D
  partlycloudy: "⛅", // U+26C5
  cloudy: "☁", // U+2601
  fog: "▒", // U+2592 (medium shade)
  hail: "☁",
  lightning: "⚡", // U+26A1
  "lightning-rainy": "⛈", // U+26C8
  pouring: "☔", // U+2614
  rainy: "☂", // U+2602
  snowy: "❄", // U+2744
  "snowy-rainy": "❄",
  windy: "≋", // U+224B
  "windy-variant": "≋",
  exceptional: "⚠", // U+26A0
};

// Get weather icon for a condition
function getWeatherIcon(condition: string): string {
  return WEATHER_ICONS[condition.toLowerCase()] || "?";
}

// Get forecast for a specific date from array
function getForecastForDate(
  forecasts: DayForecast[],
  date: Date,
): DayForecast | undefined {
  return forecasts.find((f) => isSameDay(f.date, date));
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

function truncateText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
): string {
  const metrics = ctx.measureText(text);
  if (metrics.width <= maxWidth) return text;

  let truncated = text;
  while (
    truncated.length > 0 &&
    ctx.measureText(truncated + "...").width > maxWidth
  ) {
    truncated = truncated.slice(0, -1);
  }
  return truncated + "...";
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxLines: number,
): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let currentLine = "";
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
      while (
        lastLine.length > 0 &&
        ctx.measureText(lastLine + "...").width > maxWidth
      ) {
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

// Draw indicator bar (for binary sensors like garbage day reminders)
function drawIndicators(
  ctx: CanvasRenderingContext2D,
  indicators: IndicatorData[],
  x: number,
  y: number,
  maxWidth: number,
  isRed: boolean,
): number {
  if (indicators.length === 0) return 0;

  const indicatorHeight = 30;
  const padding = 8;

  if (isRed) {
    // Draw red background for emphasis
    ctx.fillStyle = COLOR_RED;
    ctx.fillRect(x, y, maxWidth, indicatorHeight);

    // White text on red background (like weekend headers)
    ctx.fillStyle = COLOR_WHITE;
    ctx.font = "bold 18px Inter";

    let currentX = x + padding;
    indicators.forEach((indicator) => {
      const text = `${indicator.icon} ${indicator.label}`;
      const textWidth = ctx.measureText(text).width;

      if (currentX + textWidth + padding <= x + maxWidth) {
        ctx.fillText(text, currentX, y + 20);
        currentX += textWidth + 20; // Space between indicators
      }
    });
  } else {
    // Draw indicator text (black layer)
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "bold 18px Inter";

    let currentX = x + padding;
    indicators.forEach((indicator) => {
      const text = `${indicator.icon} ${indicator.label}`;
      const textWidth = ctx.measureText(text).width;

      // Check if it fits on current line
      if (currentX + textWidth + padding <= x + maxWidth) {
        ctx.fillText(text, currentX, y + 20);
        currentX += textWidth + 20; // Space between indicators
      }
    });
  }

  return indicatorHeight + 8; // Return height used (including bottom padding)
}

function drawTodaySection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
  indicators: IndicatorData[] = [],
): void {
  const sectionY = 0;
  const sectionHeight = TODAY_SECTION_HEIGHT;

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 3;
    ctx.strokeRect(
      MARGIN,
      sectionY + MARGIN,
      PORTRAIT_W - 2 * MARGIN,
      sectionHeight - MARGIN,
    );
  }

  // Draw indicator bar at top if any indicators are present
  let indicatorHeight = 0;
  if (indicators.length > 0) {
    indicatorHeight = drawIndicators(
      ctx,
      indicators,
      MARGIN + 10,
      sectionY + MARGIN + 10,
      PORTRAIT_W - 2 * MARGIN - 20,
      isRed,
    );
  }

  // Header area
  const headerX = MARGIN + 10;
  const headerY = sectionY + MARGIN + 10 + indicatorHeight;

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

  const todayEventsWithIndicators = getEventsForDay(events, today)
    .sort((a, b) => a.event.start.getTime() - b.event.start.getTime())
    .slice(0, maxEvents);

  // Fixed width for time column (fits "00:00 - 00:00")
  const timeColumnWidth = 160;

  todayEventsWithIndicators.forEach(({ event }, index) => {
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
  const totalTodayEvents = getEventsForDay(events, today).length;
  if (totalTodayEvents > maxEvents && !isRed) {
    const y = eventStartY + maxEvents * eventLineHeight;
    ctx.fillStyle = COLOR_BLACK;
    ctx.font = "italic 16px Inter";
    ctx.fillText(
      `... et ${totalTodayEvents - maxEvents} de plus`,
      headerX,
      y + 16,
    );
  }
}

function drawWeekSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
): void {
  const sectionY = TODAY_SECTION_HEIGHT;
  const sectionHeight = WEEK_SECTION_HEIGHT;
  // Start from tomorrow, show 7 days rolling window
  const tomorrow = addDays(today, 1);

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 3;
    ctx.strokeRect(
      MARGIN,
      sectionY + MARGIN,
      PORTRAIT_W - 2 * MARGIN,
      sectionHeight - 2 * MARGIN,
    );
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
    const dayEventsWithIndicators = sortEventsByPriority(
      getEventsForDay(events, day),
    );

    const eventAreaTop = gridY + dayHeaderHeight + 8;
    const eventAreaHeight = gridHeight - dayHeaderHeight - 30; // Leave room for overflow indicator
    const eventHeight = Math.floor(eventAreaHeight / 7); // Fit ~7 events (with 2-line titles)
    const maxEventsToShow = 7;
    const dayEvents = dayEventsWithIndicators.slice(0, maxEventsToShow);
    const hasMoreEvents = dayEventsWithIndicators.length > maxEventsToShow;

    dayEvents.forEach(({ event, startsOnDay, endsOnDay }, index) => {
      const eventY = eventAreaTop + index * eventHeight;

      if (!isRed) {
        ctx.fillStyle = COLOR_BLACK;
        ctx.font = "bold 16px Inter";

        // Determine time/indicator string
        const isMultiDay = !isSameDay(event.start, event.end);

        let timeStr = "";
        let endTimeStr = "";

        if (event.allDay) {
          // Draw line with triangle caps for all-day events (centered with 16px icon)
          const lineY = eventY + 8;
          const lineLeft = dayX + 5;
          const lineRight = dayX + dayWidth - 10;
          const triSize = 6;

          // Draw the line
          ctx.beginPath();
          ctx.moveTo(lineLeft + (startsOnDay ? triSize : 0), lineY);
          ctx.lineTo(lineRight - (endsOnDay ? triSize : 0), lineY);
          ctx.strokeStyle = COLOR_BLACK;
          ctx.lineWidth = 2;
          ctx.stroke();

          // Draw start triangle (pointing right) if starts today
          if (startsOnDay) {
            ctx.beginPath();
            ctx.moveTo(lineLeft, lineY - triSize);
            ctx.lineTo(lineLeft + triSize, lineY);
            ctx.lineTo(lineLeft, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }

          // Draw end triangle (pointing left) if ends today
          if (endsOnDay) {
            ctx.beginPath();
            ctx.moveTo(lineRight, lineY - triSize);
            ctx.lineTo(lineRight - triSize, lineY);
            ctx.lineTo(lineRight, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }
        } else if (isMultiDay) {
          // Multi-day timed event
          if (startsOnDay) {
            timeStr = formatTime(event.start) + " ▶";
          } else if (endsOnDay) {
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
      const moreCount = dayEventsWithIndicators.length - maxEventsToShow;
      drawOverflowIndicator({
        ctx,
        x: dayX + 5,
        y: overflowY,
        count: moreCount,
        fontSize: 14,
        language: "fr",
      });
    }
  }
}

function drawUpcomingSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
): void {
  const sectionY = TODAY_SECTION_HEIGHT + WEEK_SECTION_HEIGHT;
  const sectionHeight = UPCOMING_SECTION_HEIGHT;

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 3;
    ctx.strokeRect(
      MARGIN,
      sectionY,
      PORTRAIT_W - 2 * MARGIN,
      sectionHeight - MARGIN,
    );
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

async function drawLandscapeTodaySection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
  allEvents: CalendarEvent[] = [],
): Promise<void> {
  const sectionX = 0;
  const sectionWidth = LANDSCAPE_LEFT_WIDTH;
  const sectionHeight = LANDSCAPE_H;

  // Draw section border
  if (!isRed) {
    ctx.strokeStyle = COLOR_BLACK;
    ctx.lineWidth = 2;
    ctx.strokeRect(
      MARGIN,
      MARGIN,
      sectionWidth - MARGIN,
      sectionHeight - 2 * MARGIN,
    );
  }

  // Draw indicator bar at top if any indicators are present
  let indicatorHeight = 0;
  if (indicators.length > 0) {
    indicatorHeight = drawIndicators(
      ctx,
      indicators,
      MARGIN + 10,
      MARGIN + 10,
      sectionWidth - MARGIN - 20,
      isRed,
    );
  }

  // Header - standardized style matching day columns
  const headerX = MARGIN + 10;
  const headerY = MARGIN + indicatorHeight;
  const headerHeight = 70;
  const isWeekendDay = isWeekend(today);

  // Weekend header background (red layer)
  if (isWeekendDay && isRed) {
    ctx.fillStyle = COLOR_RED;
    ctx.fillRect(
      MARGIN + 1,
      headerY + 1,
      sectionWidth - MARGIN - 2,
      headerHeight - 1,
    );
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
        const highTemp = hasHigh
          ? `${Math.round(todayForecast.tempHigh!)}°`
          : "";
        const lowTemp = hasLow ? `${Math.round(todayForecast.tempLow!)}°` : "";
        const highMetrics = hasHigh ? ctx.measureText(highTemp) : { width: 0 };
        const lowMetrics = hasLow ? ctx.measureText(lowTemp) : { width: 0 };
        tempWidth = Math.max(highMetrics.width, lowMetrics.width);

        // Keep positions stable: high always on top, low always on bottom
        if (hasHigh) {
          ctx.fillText(
            highTemp,
            weatherRightEdge - highMetrics.width,
            headerY + 12,
          );
        }
        if (hasLow) {
          ctx.fillText(
            lowTemp,
            weatherRightEdge - lowMetrics.width,
            headerY + 38,
          );
        }
      }

      // Large weather icon to the left of temps
      ctx.font = "44px Symbola, DejaVu Sans";
      const icon = getWeatherIcon(todayForecast.condition);
      const iconMetrics = ctx.measureText(icon);
      const iconX =
        tempWidth > 0
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
  const legendHeight =
    legend.length > 0 ? legendRows * legendItemHeight + legendHeaderHeight : 0;
  const bottomPadding = 20; // Space at very bottom to avoid cutoff
  // Note: overflow indicator is now placed in the event area (where next event would go)
  // so we don't need to reserve separate space for it
  const reservedBottom = bottomPadding + legendHeight;
  const maxEvents = Math.floor(
    (sectionHeight - eventStartY - reservedBottom) / eventBlockHeight,
  );

  const todayEventsWithIndicators = getEventsForDay(events, today)
    .sort((a, b) => a.event.start.getTime() - b.event.start.getTime())
    .slice(0, maxEvents);

  const maxTitleWidth = eventWidth - 10;

  todayEventsWithIndicators.forEach(
    ({ event, startsOnDay, endsOnDay }, index) => {
      const blockY = eventStartY + index * eventBlockHeight;
      const isMultiDay = !isSameDay(event.start, event.end);

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
          ctx.moveTo(lineLeft + (startsOnDay ? triSize : 0), lineY);
          ctx.lineTo(lineRight - (endsOnDay ? triSize : 0), lineY);
          ctx.strokeStyle = COLOR_BLACK;
          ctx.lineWidth = 2;
          ctx.stroke();

          if (startsOnDay) {
            ctx.beginPath();
            ctx.moveTo(lineLeft, lineY - triSize);
            ctx.lineTo(lineLeft + triSize, lineY);
            ctx.lineTo(lineLeft, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }
          if (endsOnDay) {
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
          if (startsOnDay) {
            timeStr = formatTime(event.start) + " ▶";
          } else if (endsOnDay) {
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
          ctx.fillText(
            endTimeStr,
            headerX + eventWidth - endTimeWidth - 5,
            blockY,
          );

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
    },
  );

  // Calculate legend position (at bottom of section)
  const legendX = headerX;
  const legendTop = sectionHeight - bottomPadding - legendHeight;

  // Overflow indicator - positioned where the next event would go, minus a few pixels
  const totalTodayEvents = getEventsForDay(events, today).length;
  if (totalTodayEvents > maxEvents && isRed) {
    const moreCount = totalTodayEvents - maxEvents;
    const y = eventStartY + maxEvents * eventBlockHeight - 6;
    drawOverflowIndicator({
      ctx,
      x: headerX,
      y,
      count: moreCount,
      fontSize: 18,
      language: "fr",
    });
  }

  // Collection icons above the legend (lower right corner of Today section)
  const collectionIcons = getCollectionIconsForDay(
    allEvents.length > 0 ? allEvents : events,
    today,
    collectionCalendars,
    collectionTypes,
  );
  if (collectionIcons.length > 0) {
    const iconSize = 18;
    const iconSpacing = 4;
    let currentX =
      sectionWidth - MARGIN - collectionIcons.length * (iconSize + iconSpacing);
    const iconY = legendTop - 8; // 8px above legend

    for (const iconName of collectionIcons) {
      await drawCollectionIcon(ctx, iconName, currentX, iconY, iconSize, isRed);
      currentX += iconSize + iconSpacing;
    }
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

async function drawLandscapeWeekSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
  allEvents: CalendarEvent[] = [],
): Promise<void> {
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
      const dayName = format(day, "EEE", { locale: fr })
        .toUpperCase()
        .slice(0, 3);
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
          const highTemp = hasHigh
            ? `${Math.round(dayForecast.tempHigh!)}°`
            : "";
          const lowTemp = hasLow ? `${Math.round(dayForecast.tempLow!)}°` : "";
          const highMetrics = hasHigh
            ? ctx.measureText(highTemp)
            : { width: 0 };
          const lowMetrics = hasLow ? ctx.measureText(lowTemp) : { width: 0 };
          tempWidth = Math.max(highMetrics.width, lowMetrics.width);

          // Keep positions stable: high always on top, low always on bottom
          if (hasHigh) {
            ctx.fillText(
              highTemp,
              rightMargin - highMetrics.width,
              gridTop + 16,
            );
          }
          if (hasLow) {
            ctx.fillText(lowTemp, rightMargin - lowMetrics.width, gridTop + 36);
          }
        }

        // Weather icon to the left of temps
        ctx.font = "32px Symbola, DejaVu Sans";
        const icon = getWeatherIcon(dayForecast.condition);
        const iconMetrics = ctx.measureText(icon);
        const iconX =
          tempWidth > 0
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

    // Draw indicators for this day (if any)
    let indicatorOffset = 0;
    if (indicators.length > 0) {
      const indicatorY = gridTop + dayHeaderHeight + 4;
      const indicatorHeight = 24;

      if (isRed) {
        // Draw red background bar
        ctx.fillStyle = COLOR_RED;
        ctx.fillRect(dayX + 2, indicatorY, dayWidth - 4, indicatorHeight);

        // Draw indicator text in white
        ctx.fillStyle = COLOR_WHITE;
        ctx.font = "bold 14px Inter";

        let textX = dayX + 6;
        indicators.forEach((indicator: IndicatorData) => {
          const text = `${indicator.icon} ${indicator.label}`;
          const textWidth = ctx.measureText(text).width;

          if (textX + textWidth < dayX + dayWidth - 6) {
            ctx.fillText(text, textX, indicatorY + 16);
            textX += textWidth + 8;
          }
        });
      } else {
        // Draw indicator text in black (black layer, no background)
        ctx.fillStyle = COLOR_BLACK;
        ctx.font = "bold 14px Inter";

        let textX = dayX + 6;
        indicators.forEach((indicator: IndicatorData) => {
          const text = `${indicator.icon} ${indicator.label}`;
          const textWidth = ctx.measureText(text).width;

          if (textX + textWidth < dayX + dayWidth - 6) {
            ctx.fillText(text, textX, indicatorY + 16);
            textX += textWidth + 8;
          }
        });
      }

      indicatorOffset = indicatorHeight + 4;
    }

    // Day events
    const dayEventsWithIndicators = sortEventsByPriority(
      getEventsForDay(events, day),
    );

    const eventAreaTop = gridTop + dayHeaderHeight + 8 + indicatorOffset;
    const eventAreaHeight = sectionHeight - gridTop - dayHeaderHeight - 40;
    const eventHeight = Math.floor(eventAreaHeight / 8);
    const maxEventsToShow = 8;
    const dayEvents = dayEventsWithIndicators.slice(0, maxEventsToShow);
    const hasMoreEvents = dayEventsWithIndicators.length > maxEventsToShow;

    dayEvents.forEach(({ event, startsOnDay, endsOnDay }, index) => {
      const eventY = eventAreaTop + index * eventHeight;

      if (!isRed) {
        ctx.fillStyle = COLOR_BLACK;
        ctx.font = "bold 14px Inter";

        const isMultiDay = !isSameDay(event.start, event.end);

        let timeStr = "";
        let endTimeStr = "";

        if (event.allDay) {
          // All-day indicator line (centered with 14px icon)
          const lineY = eventY + 7;
          const lineLeft = dayX + 5;
          const lineRight = dayX + dayWidth - 10;
          const triSize = 5;

          ctx.beginPath();
          ctx.moveTo(lineLeft + (startsOnDay ? triSize : 0), lineY);
          ctx.lineTo(lineRight - (endsOnDay ? triSize : 0), lineY);
          ctx.strokeStyle = COLOR_BLACK;
          ctx.lineWidth = 2;
          ctx.stroke();

          if (startsOnDay) {
            ctx.beginPath();
            ctx.moveTo(lineLeft, lineY - triSize);
            ctx.lineTo(lineLeft + triSize, lineY);
            ctx.lineTo(lineLeft, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }
          if (endsOnDay) {
            ctx.beginPath();
            ctx.moveTo(lineRight, lineY - triSize);
            ctx.lineTo(lineRight - triSize, lineY);
            ctx.lineTo(lineRight, lineY + triSize);
            ctx.closePath();
            ctx.fill();
          }
        } else if (isMultiDay) {
          if (startsOnDay) {
            timeStr = formatTime(event.start) + " ▶";
          } else if (endsOnDay) {
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
            getIconBottomOffset(event.calendarIcon, 14),
          );
          // For all-day events, align icon with the line (lineY = eventY + 7)
          const iconY = event.allDay
            ? eventY + iconOffset + 2
            : eventY + iconOffset;
          ctx.fillText(event.calendarIcon, iconX, iconY);
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
      const moreCount = dayEventsWithIndicators.length - maxEventsToShow;
      drawOverflowIndicator({
        ctx,
        x: dayX + 5,
        y: overflowY,
        count: moreCount,
        fontSize: 14,
        language: "fr",
      });
    }

    // Collection calendar icons (lower right corner of day cell)
    const collectionIcons = getCollectionIconsForDay(
      allEvents.length > 0 ? allEvents : events,
      day,
      collectionCalendars,
      collectionTypes,
    );
    if (collectionIcons.length > 0) {
      const iconSize = 14;
      const iconSpacing = 3;
      let currentX =
        dayX + dayWidth - collectionIcons.length * (iconSize + iconSpacing) - 6;
      const iconY = gridBottom - 6;

      for (const iconName of collectionIcons) {
        await drawCollectionIcon(
          ctx,
          iconName,
          currentX,
          iconY,
          iconSize,
          isRed,
        );
        currentX += iconSize + iconSpacing;
      }
    }
  }
}

function drawLandscapeUpcomingSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
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

export async function renderCalendar(
  events: CalendarEvent[],
  now: Date,
  layout: LayoutMode = "portrait",
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
): Promise<RenderedCalendar> {
  if (layout === "landscape") {
    return await renderCalendarLandscape(
      events,
      now,
      legend,
      weather,
      indicators,
      collectionCalendars,
      collectionTypes,
    );
  }
  return renderCalendarPortrait(
    events,
    now,
    legend,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
  );
}

function renderCalendarPortrait(
  events: CalendarEvent[],
  now: Date,
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
): RenderedCalendar {
  // Create canvas in portrait mode for rendering
  const canvas = createCanvas(PORTRAIT_W, PORTRAIT_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Draw all sections (black layer)
  ctx.textBaseline = "top";
  drawTodaySection(ctx, events, now, false, indicators);
  drawWeekSection(ctx, events, now, false);
  drawUpcomingSection(ctx, events, now, false);

  // Get black layer image data
  const blackImageData = ctx.getImageData(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Clear and draw red layer
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  drawTodaySection(ctx, events, now, true, indicators);
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

async function renderCalendarLandscape(
  events: CalendarEvent[],
  now: Date,
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
): Promise<RenderedCalendar> {
  // Create canvas directly in landscape mode (no rotation needed)
  const canvas = createCanvas(LANDSCAPE_W, LANDSCAPE_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  // Draw all sections (black layer)
  ctx.textBaseline = "top";
  await drawLandscapeTodaySection(
    ctx,
    events,
    now,
    false,
    legend,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
  );
  await drawLandscapeWeekSection(
    ctx,
    events,
    now,
    false,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
  );
  drawLandscapeUpcomingSection(ctx, events, now, false);

  // Get black layer image data
  const blackImageData = ctx.getImageData(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  // Clear and draw red layer
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  await drawLandscapeTodaySection(
    ctx,
    events,
    now,
    true,
    legend,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
  );
  await drawLandscapeWeekSection(
    ctx,
    events,
    now,
    true,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
  );
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
function rotateImageData90CW(imageData: {
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

function imageDataTo1Bit(
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

export function extractChunk(layer: Buffer, chunkIndex: 1 | 2): Buffer {
  // Display is in landscape mode: 1304 wide x 984 tall
  // ESP32 expects two 492-row chunks
  // Chunk 1: rows 0-491, Chunk 2: rows 492-983
  const bytesPerRow = Math.ceil(DISPLAY_W / 8); // 163 bytes
  const halfHeight = Math.ceil(DISPLAY_H / 2); // 492 rows
  const chunkSize = bytesPerRow * halfHeight; // 80196 bytes

  if (chunkIndex === 1) {
    return layer.subarray(0, chunkSize);
  } else {
    return layer.subarray(chunkSize);
  }
}

// For debugging: render to PNG
export async function renderToPng(
  events: CalendarEvent[],
  now: Date,
  layout: LayoutMode = "portrait",
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
  allEvents?: CalendarEvent[], // Full event list including collection events
): Promise<Buffer> {
  // Use allEvents for collection icon matching, or fall back to events if not provided
  const eventsForCollectionIcons = allEvents || events;

  if (layout === "landscape") {
    return await renderToPngLandscape(
      events,
      now,
      legend,
      weather,
      indicators,
      collectionCalendars,
      collectionTypes,
      eventsForCollectionIcons,
    );
  }
  return renderToPngPortrait(
    events,
    now,
    legend,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
    eventsForCollectionIcons,
  );
}

function renderToPngPortrait(
  events: CalendarEvent[],
  now: Date,
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
  allEvents: CalendarEvent[] = [],
): Buffer {
  const canvas = createCanvas(PORTRAIT_W, PORTRAIT_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Draw all sections
  ctx.textBaseline = "top";
  drawTodaySection(ctx, events, now, false, indicators);
  drawWeekSection(ctx, events, now, false);
  drawUpcomingSection(ctx, events, now, false);

  // Draw red elements on top
  drawTodaySection(ctx, events, now, true, indicators);
  drawWeekSection(ctx, events, now, true);
  drawUpcomingSection(ctx, events, now, true);

  // TODO: Add legend and weather support for portrait mode

  return canvas.toBuffer("image/png");
}

async function renderToPngLandscape(
  events: CalendarEvent[],
  now: Date,
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
  allEvents: CalendarEvent[] = [],
): Promise<Buffer> {
  const canvas = createCanvas(LANDSCAPE_W, LANDSCAPE_H);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, LANDSCAPE_W, LANDSCAPE_H);

  // Draw all sections
  ctx.textBaseline = "top";
  await drawLandscapeTodaySection(
    ctx,
    events,
    now,
    false,
    legend,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
    allEvents,
  );
  await drawLandscapeWeekSection(
    ctx,
    events,
    now,
    false,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
    allEvents,
  );
  drawLandscapeUpcomingSection(ctx, events, now, false);

  // Draw red elements on top
  await drawLandscapeTodaySection(
    ctx,
    events,
    now,
    true,
    legend,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
    allEvents,
  );
  await drawLandscapeWeekSection(
    ctx,
    events,
    now,
    true,
    weather,
    indicators,
    collectionCalendars,
    collectionTypes,
    allEvents,
  );
  drawLandscapeUpcomingSection(ctx, events, now, true);

  return canvas.toBuffer("image/png");
}
