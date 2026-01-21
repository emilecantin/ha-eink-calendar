import { CanvasRenderingContext2D } from "canvas";
import { CalendarEvent } from "./renderer";

// Color constants (match renderer.ts)
const COLOR_RED = "#FF0000";

/**
 * Configuration for drawing event triangles (all-day event indicators)
 */
export interface TriangleConfig {
  ctx: CanvasRenderingContext2D;
  x: number;
  y: number;
  size: number;
  direction: 'left' | 'right';
}

/**
 * Draw a triangle indicator for all-day events
 * Used to show if an event starts or ends on the current day
 */
export function drawEventTriangle(config: TriangleConfig): void {
  const { ctx, x, y, size, direction } = config;

  ctx.beginPath();
  if (direction === 'left') {
    // Triangle pointing right (event starts on this day)
    ctx.moveTo(x, y - size);
    ctx.lineTo(x + size, y);
    ctx.lineTo(x, y + size);
  } else {
    // Triangle pointing left (event ends on this day)
    ctx.moveTo(x, y - size);
    ctx.lineTo(x - size, y);
    ctx.lineTo(x, y + size);
  }
  ctx.closePath();
  ctx.fill();
}

/**
 * Configuration for formatting multi-day event times
 */
export interface MultiDayTimeConfig {
  event: CalendarEvent;
  dayIndicators: { startsOnDay: boolean; endsOnDay: boolean };
}

/**
 * Format time display for multi-day events with directional arrows
 * Returns empty string for all-day events
 */
export function formatMultiDayTime(config: MultiDayTimeConfig): string {
  const { event, dayIndicators } = config;
  const { startsOnDay, endsOnDay } = dayIndicators;

  // All-day events don't show times
  if (event.allDay) return '';

  // Format time helper
  const formatTime = (date: Date): string => {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  if (startsOnDay) {
    // Event starts on this day - show start time with right arrow
    return formatTime(event.start) + " ▶";
  } else if (endsOnDay) {
    // Event ends on this day - show end time with left arrow
    return "◀ " + formatTime(event.end);
  } else {
    // Event continues through this day - show both arrows
    return "◀ ▶";
  }
}

/**
 * Configuration for drawing event overflow indicators
 */
export interface OverflowIndicatorConfig {
  ctx: CanvasRenderingContext2D;
  x: number;
  y: number;
  count: number;
  fontSize: number;
  language?: 'fr' | 'en';
}

/**
 * Draw "+X more events" indicator when there are too many events to display
 */
export function drawOverflowIndicator(config: OverflowIndicatorConfig): void {
  const { ctx, x, y, count, fontSize, language = 'fr' } = config;

  // Format text based on language
  const text = language === 'fr'
    ? `+${count} autre${count > 1 ? 's' : ''} événement${count > 1 ? 's' : ''}`
    : `+${count} more`;

  ctx.fillStyle = COLOR_RED;
  ctx.font = `bold ${fontSize}px Inter`;
  ctx.fillText(text, x, y);
}

/**
 * Event with day indicators (whether it starts/ends on the day being rendered)
 */
export interface EventWithIndicators {
  event: CalendarEvent;
  startsOnDay: boolean;
  endsOnDay: boolean;
}

/**
 * Sort events by priority: all-day events first, then by start time
 * This ensures consistent event ordering across all sections
 */
export function sortEventsByPriority(
  eventsWithIndicators: EventWithIndicators[]
): EventWithIndicators[] {
  return eventsWithIndicators.sort((a, b) => {
    // All-day events always come first
    if (a.event.allDay && !b.event.allDay) return -1;
    if (!a.event.allDay && b.event.allDay) return 1;

    // Then sort by start time
    return a.event.start.getTime() - b.event.start.getTime();
  });
}
