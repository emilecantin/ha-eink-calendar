/**
 * Landscape Today section renderer (full-height left panel)
 */

import { CanvasRenderingContext2D } from "canvas";
import { format, isWeekend, isSameDay } from "date-fns";
import { fr } from "date-fns/locale";
import { DISPLAY, MARGINS, LAYOUT_LANDSCAPE, COLORS } from "../layout-config";
import { capitalize, wrapText } from "../text-utils";
import { getIconCenterOffset, drawCollectionIcon } from "../icon-utils";
import {
  getEventsForDay,
  getCollectionIconsForDay,
  CalendarEvent,
} from "../event-filters";
import { drawIndicators, IndicatorData } from "./indicators";
import {
  DayForecast,
  getWeatherIcon,
  getForecastForDate,
} from "../weather-utils";
import { drawOverflowIndicator } from "../event-renderer";

const LANDSCAPE_H = DISPLAY.LANDSCAPE.height;
const LANDSCAPE_LEFT_WIDTH = LAYOUT_LANDSCAPE.TODAY.width;
const MARGIN = MARGINS.STANDARD;
const COLOR_BLACK = COLORS.BLACK;
const COLOR_WHITE = COLORS.WHITE;
const COLOR_RED = COLORS.RED;

/**
 * Legend item for calendar icons
 */
export interface LegendItem {
  icon: string;
  name: string;
}

/**
 * Collection type configuration
 */
export interface CollectionType {
  name: string;
  icon: string;
}

/**
 * Draw the Today section in landscape layout (full-height left panel)
 */
export async function drawLandscapeTodaySection(
  ctx: CanvasRenderingContext2D,
  events: CalendarEvent[],
  today: Date,
  isRed: boolean,
  legend: LegendItem[] = [],
  weather: DayForecast[] = [],
  indicators: IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: CollectionType[] = [],
  allEvents: CalendarEvent[] = [],
): Promise<void> {
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
            timeStr = format(event.start, "HH:mm") + " ▶";
          } else if (endsOnDay) {
            timeStr = "◀ " + format(event.end, "HH:mm");
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
          ctx.fillText(format(event.start, "HH:mm"), headerX, blockY);

          const endTimeStr = format(event.end, "HH:mm");
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
      const truncatedName =
        ctx.measureText(item.name).width <= maxNameWidth
          ? item.name
          : item.name.slice(0, Math.floor(maxNameWidth / 8)) + "...";
      ctx.fillText(truncatedName, nameX, y);
    });
  }
}
