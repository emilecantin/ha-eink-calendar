/**
 * Portrait Week section renderer (7-day rolling window)
 */

import { CanvasRenderingContext2D } from "canvas";
import { format, addDays, isSameDay, isWeekend, differenceInDays } from "date-fns";
import { fr } from "date-fns/locale";
import { DISPLAY, MARGINS, LAYOUT_PORTRAIT, COLORS } from "../layout-config";
import { capitalize, formatTime, wrapText } from "../text-utils";
import { getIconCenterOffset, getIconBottomOffset } from "../icon-utils";
import { getEventsForDay, CalendarEvent } from "../event-filters";
import { sortEventsByPriority } from "../event-renderer";
import { drawOverflowIndicator } from "../event-renderer";

const PORTRAIT_W = DISPLAY.PORTRAIT.width;
const TODAY_SECTION_HEIGHT = LAYOUT_PORTRAIT.TODAY.height;
const WEEK_SECTION_HEIGHT = LAYOUT_PORTRAIT.WEEK.height;
const MARGIN = MARGINS.STANDARD;
const COLOR_BLACK = COLORS.BLACK;
const COLOR_WHITE = COLORS.WHITE;
const COLOR_RED = COLORS.RED;

/**
 * Draw the Week section in portrait layout (7-day rolling window)
 */
export function drawWeekSection(
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
