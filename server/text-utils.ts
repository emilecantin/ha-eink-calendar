/**
 * Text formatting utilities for EPCAL calendar rendering.
 *
 * Provides functions for text manipulation: truncation, wrapping, capitalization, and time formatting.
 */

import { CanvasRenderingContext2D } from "canvas";
import { format } from "date-fns";

/**
 * Capitalize the first letter of a string
 */
export function capitalize(text: string): string {
  return text.replace(/^(\w)/, (s) => s.toLocaleUpperCase());
}

/**
 * Format a date as HH:mm time string
 */
export function formatTime(date: Date): string {
  return format(date, "HH:mm");
}

/**
 * Truncate text to fit within maxWidth, adding ellipsis if needed
 *
 * @param ctx - Canvas rendering context (for measuring text)
 * @param text - Text to truncate
 * @param maxWidth - Maximum width in pixels
 * @returns Truncated text with "..." if it doesn't fit
 */
export function truncateText(
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

/**
 * Wrap text to fit within maxWidth, breaking at word boundaries
 *
 * @param ctx - Canvas rendering context (for measuring text)
 * @param text - Text to wrap
 * @param maxWidth - Maximum width in pixels per line
 * @param maxLines - Maximum number of lines to return
 * @returns Array of text lines, with ellipsis on last line if text doesn't fit
 */
export function wrapText(
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
