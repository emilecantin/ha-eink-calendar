/**
 * Portrait Upcoming section renderer (multi-day and all-day events beyond 7-day window)
 */

import { CanvasRenderingContext2D } from "canvas";
import { format, addDays, startOfDay, differenceInDays } from "date-fns";
import { fr } from "date-fns/locale";
import { DISPLAY, MARGINS, LAYOUT_PORTRAIT, COLORS } from "../layout-config";
import { truncateText } from "../text-utils";
import { getIconCenterOffset } from "../icon-utils";
import { CalendarEvent } from "../event-filters";

const PORTRAIT_W = DISPLAY.PORTRAIT.width;
const TODAY_SECTION_HEIGHT = LAYOUT_PORTRAIT.TODAY.height;
const WEEK_SECTION_HEIGHT = LAYOUT_PORTRAIT.WEEK.height;
const UPCOMING_SECTION_HEIGHT = LAYOUT_PORTRAIT.UPCOMING.height;
const MARGIN = MARGINS.STANDARD;
const COLOR_BLACK = COLORS.BLACK;
const COLOR_RED = COLORS.RED;

/**
 * Draw the Upcoming section in portrait layout
 * Shows multi-day and all-day events beyond the 7-day rolling window
 */
export function drawUpcomingSection(
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
