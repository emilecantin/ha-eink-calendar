/**
 * Landscape Upcoming section renderer (lower right panel)
 */

import { CanvasRenderingContext2D } from "canvas";
import { format, addDays, startOfDay, differenceInDays } from "date-fns";
import { fr } from "date-fns/locale";
import { LAYOUT_LANDSCAPE, MARGINS, COLORS } from "../layout-config";
import { truncateText } from "../text-utils";
import { getIconCenterOffset } from "../icon-utils";
import { CalendarEvent } from "../event-filters";

const LANDSCAPE_LEFT_WIDTH = LAYOUT_LANDSCAPE.TODAY.width;
const LANDSCAPE_RIGHT_WIDTH = LAYOUT_LANDSCAPE.RIGHT_PANEL.width;
const LANDSCAPE_WEEK_HEIGHT = LAYOUT_LANDSCAPE.WEEK.height;
const LANDSCAPE_UPCOMING_HEIGHT = LAYOUT_LANDSCAPE.UPCOMING.height;
const MARGIN = MARGINS.STANDARD;
const COLOR_BLACK = COLORS.BLACK;
const COLOR_RED = COLORS.RED;

/**
 * Draw the Upcoming section in landscape layout (lower right panel)
 */
export function drawLandscapeUpcomingSection(
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
