/**
 * Portrait Today section renderer
 */

import { CanvasRenderingContext2D } from "canvas";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { DISPLAY, MARGINS, LAYOUT_PORTRAIT, COLORS } from "../layout-config";
import { capitalize, formatTime, truncateText } from "../text-utils";
import { getIconCenterOffset } from "../icon-utils";
import { getEventsForDay, CalendarEvent } from "../event-filters";
import { drawIndicators, IndicatorData } from "./indicators";

const PORTRAIT_W = DISPLAY.PORTRAIT.width;
const TODAY_SECTION_HEIGHT = LAYOUT_PORTRAIT.TODAY.height;
const MARGIN = MARGINS.STANDARD;
const COLOR_BLACK = COLORS.BLACK;

/**
 * Draw the Today section in portrait layout
 */
export function drawTodaySection(
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
