/**
 * Landscape Week section renderer (6-day columns in upper right)
 */

import { CanvasRenderingContext2D } from "canvas";
import { format, addDays, isSameDay, isWeekend } from "date-fns";
import { fr } from "date-fns/locale";
import { DISPLAY, MARGINS, LAYOUT_LANDSCAPE, COLORS } from "../layout-config";
import { wrapText } from "../text-utils";
import { getIconCenterOffset, getIconBottomOffset, drawCollectionIcon } from "../icon-utils";
import { getEventsForDay, getCollectionIconsForDay, CalendarEvent } from "../event-filters";
import { sortEventsByPriority } from "../event-renderer";
import { drawOverflowIndicator } from "../event-renderer";
import { DayForecast, getWeatherIcon, getForecastForDate } from "../weather-utils";
import { IndicatorData, drawIndicators } from "./indicators";

const LANDSCAPE_H = DISPLAY.LANDSCAPE.height;
const LANDSCAPE_LEFT_WIDTH = LAYOUT_LANDSCAPE.TODAY.width;
const LANDSCAPE_RIGHT_WIDTH = LAYOUT_LANDSCAPE.RIGHT_PANEL.width;
const LANDSCAPE_WEEK_HEIGHT = LAYOUT_LANDSCAPE.WEEK.height;
const MARGIN = MARGINS.STANDARD;
const COLOR_BLACK = COLORS.BLACK;
const COLOR_WHITE = COLORS.WHITE;
const COLOR_RED = COLORS.RED;

/**
 * Collection type configuration
 */
export interface CollectionType {
  name: string;
  icon: string;
}

/**
 * Draw the Week section in landscape layout (6-day columns)
 */
export async function drawLandscapeWeekSection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: CollectionType[] = [],
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
            timeStr = format(event.start, "HH:mm") + " ▶";
          } else if (endsOnDay) {
            timeStr = "◀ " + format(event.end, "HH:mm");
          } else {
            timeStr = "◀ ▶";
          }
        } else {
          timeStr = format(event.start, "HH:mm");
          endTimeStr = format(event.end, "HH:mm");
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
