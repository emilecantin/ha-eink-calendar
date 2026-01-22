/**
 * Indicator bar renderer for binary sensor displays (e.g., garbage day reminders)
 */

import { CanvasRenderingContext2D } from "canvas";
import { COLORS } from "../layout-config";

/**
 * Indicator data structure for binary sensor display
 */
export interface IndicatorData {
  entityId: string;
  state: "on" | "off";
  label: string;
  icon: string;
  shouldDisplay: boolean;
}

/**
 * Draw indicator bar (for binary sensors like garbage day reminders)
 *
 * @param ctx - Canvas rendering context
 * @param indicators - Array of indicator data
 * @param x - Left edge of indicator bar
 * @param y - Top edge of indicator bar
 * @param maxWidth - Maximum width of indicator bar
 * @param isRed - Whether this is the red layer
 * @returns Height of the indicator bar (including padding)
 */
export function drawIndicators(
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
    ctx.fillStyle = COLORS.RED;
    ctx.fillRect(x, y, maxWidth, indicatorHeight);

    // White text on red background (like weekend headers)
    ctx.fillStyle = COLORS.WHITE;
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
    ctx.fillStyle = COLORS.BLACK;
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
