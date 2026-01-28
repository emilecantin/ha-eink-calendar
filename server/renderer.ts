/**
 * Main calendar renderer for EPCAL e-paper display.
 *
 * Orchestrates the rendering pipeline:
 * 1. Creates canvas in appropriate orientation
 * 2. Renders black and red layers using section renderers
 * 3. Converts to 1-bit bitmaps for e-paper display
 * 4. Generates ETag for caching
 */

import { createCanvas } from "canvas";
import crypto from "crypto";

// Import font configuration (registers fonts on import)
import "./font-config";

// Import layout constants
import { DISPLAY, COLORS } from "./layout-config";

// Import utilities
import { rotateImageData90CW, imageDataTo1Bit } from "./bitmap-utils";

// Import types
export type { CalendarEvent } from "./event-filters";
export type { DayForecast } from "./weather-utils";
export type { IndicatorData } from "./section-renderers/indicators";

// Import section renderers
import { drawTodaySection as drawPortraitTodaySection } from "./section-renderers/portrait-today";
import { drawWeekSection as drawPortraitWeekSection } from "./section-renderers/portrait-week";
import { drawUpcomingSection as drawPortraitUpcomingSection } from "./section-renderers/portrait-upcoming";
import { drawLandscapeTodaySection } from "./section-renderers/landscape-today";
import { drawLandscapeWeekSection } from "./section-renderers/landscape-week";
import { drawLandscapeUpcomingSection } from "./section-renderers/landscape-upcoming";

// Re-export utilities for external use
export { formatTime, capitalize, truncateText, wrapText } from "./text-utils";
export { getWeatherIcon, getForecastForDate } from "./weather-utils";
export { getIconCenterOffset, getIconBottomOffset } from "./icon-utils";
export { getEventsForDay } from "./event-filters";
export {
  rotateImageData90CW,
  imageDataTo1Bit,
  extractChunk,
} from "./bitmap-utils";

// Display dimensions
const PORTRAIT_W = DISPLAY.PORTRAIT.width;
const PORTRAIT_H = DISPLAY.PORTRAIT.height;
const LANDSCAPE_W = DISPLAY.LANDSCAPE.width;
const LANDSCAPE_H = DISPLAY.LANDSCAPE.height;

// Colors
const COLOR_WHITE = COLORS.WHITE;

/**
 * Layout mode for calendar rendering
 */
export type LayoutMode = "portrait" | "landscape";

/**
 * Legend item for calendar icons
 */
export interface LegendItem {
  icon: string;
  name: string;
}

/**
 * Rendered calendar with separate black and red layers
 */
export interface RenderedCalendar {
  blackLayer: Buffer;
  redLayer: Buffer;
  etag: string;
  timestamp: Date;
}

/**
 * Render calendar for e-paper display
 *
 * @param events - Calendar events to render
 * @param now - Current date/time
 * @param layout - Layout mode (portrait or landscape)
 * @param legend - Legend items for calendar icons
 * @param weather - Weather forecast data
 * @param indicators - Binary sensor indicators
 * @param collectionCalendars - Calendar IDs for collection calendars
 * @param collectionTypes - Collection type configurations
 * @returns Rendered calendar with black/red layers and ETag
 */
export async function renderCalendar(
  events: import("./event-filters").CalendarEvent[],
  now: Date,
  layout: LayoutMode = "portrait",
  legend: LegendItem[] = [],
  weather: import("./weather-utils").DayForecast[] = [],
  indicators: import("./section-renderers/indicators").IndicatorData[] = [],
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

/**
 * Render calendar in portrait mode (rotated to landscape for display)
 */
function renderCalendarPortrait(
  events: import("./event-filters").CalendarEvent[],
  now: Date,
  _legend: LegendItem[] = [],
  _weather: import("./weather-utils").DayForecast[] = [],
  indicators: import("./section-renderers/indicators").IndicatorData[] = [],
  _collectionCalendars: string[] = [],
  _collectionTypes: Array<{ name: string; icon: string }> = [],
): RenderedCalendar {
  // Create canvas in portrait mode for rendering
  const canvas = createCanvas(PORTRAIT_W, PORTRAIT_H);
  const ctx = canvas.getContext("2d");

  // Disable antialiasing to match Python PIL rendering
  ctx.antialias = "none";
  ctx.imageSmoothingEnabled = false;

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Draw all sections (black layer)
  ctx.textBaseline = "top";
  drawPortraitTodaySection(ctx, events, now, false, indicators);
  drawPortraitWeekSection(ctx, events, now, false);
  drawPortraitUpcomingSection(ctx, events, now, false);

  // Get black layer image data
  const blackImageData = ctx.getImageData(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Clear and draw red layer
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  drawPortraitTodaySection(ctx, events, now, true, indicators);
  drawPortraitWeekSection(ctx, events, now, true);
  drawPortraitUpcomingSection(ctx, events, now, true);

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

/**
 * Render calendar in landscape mode (native orientation)
 */
async function renderCalendarLandscape(
  events: import("./event-filters").CalendarEvent[],
  now: Date,
  legend: LegendItem[] = [],
  weather: import("./weather-utils").DayForecast[] = [],
  indicators: import("./section-renderers/indicators").IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
): Promise<RenderedCalendar> {
  // Create canvas directly in landscape mode (no rotation needed)
  const canvas = createCanvas(LANDSCAPE_W, LANDSCAPE_H);
  const ctx = canvas.getContext("2d");

  // Disable antialiasing to match Python PIL rendering
  ctx.antialias = "none";
  ctx.imageSmoothingEnabled = false;

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
    events, // allEvents
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
    events, // allEvents
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
    events, // allEvents
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
    events, // allEvents
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

/**
 * Render calendar to PNG for debugging/preview
 *
 * @param events - Calendar events to render
 * @param now - Current date/time
 * @param layout - Layout mode (portrait or landscape)
 * @param legend - Legend items for calendar icons
 * @param weather - Weather forecast data
 * @param indicators - Binary sensor indicators
 * @param collectionCalendars - Calendar IDs for collection calendars
 * @param collectionTypes - Collection type configurations
 * @param allEvents - Full event list including collection events
 * @returns PNG buffer
 */
export async function renderToPng(
  events: import("./event-filters").CalendarEvent[],
  now: Date,
  layout: LayoutMode = "portrait",
  legend: LegendItem[] = [],
  weather: import("./weather-utils").DayForecast[] = [],
  indicators: import("./section-renderers/indicators").IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
  allEvents?: import("./event-filters").CalendarEvent[],
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

/**
 * Render portrait calendar to PNG
 */
function renderToPngPortrait(
  events: import("./event-filters").CalendarEvent[],
  now: Date,
  _legend: LegendItem[] = [],
  _weather: import("./weather-utils").DayForecast[] = [],
  indicators: import("./section-renderers/indicators").IndicatorData[] = [],
  _collectionCalendars: string[] = [],
  _collectionTypes: Array<{ name: string; icon: string }> = [],
  _allEvents: import("./event-filters").CalendarEvent[] = [],
): Buffer {
  const canvas = createCanvas(PORTRAIT_W, PORTRAIT_H);
  const ctx = canvas.getContext("2d");

  // Disable antialiasing to match Python PIL rendering
  ctx.antialias = "none";
  ctx.imageSmoothingEnabled = false;

  // White background
  ctx.fillStyle = COLOR_WHITE;
  ctx.fillRect(0, 0, PORTRAIT_W, PORTRAIT_H);

  // Draw all sections
  ctx.textBaseline = "top";
  drawPortraitTodaySection(ctx, events, now, false, indicators);
  drawPortraitWeekSection(ctx, events, now, false);
  drawPortraitUpcomingSection(ctx, events, now, false);

  // Draw red elements on top
  drawPortraitTodaySection(ctx, events, now, true, indicators);
  drawPortraitWeekSection(ctx, events, now, true);
  drawPortraitUpcomingSection(ctx, events, now, true);

  // TODO: Add legend and weather support for portrait mode

  return canvas.toBuffer("image/png");
}

/**
 * Render landscape calendar to PNG
 */
async function renderToPngLandscape(
  events: import("./event-filters").CalendarEvent[],
  now: Date,
  legend: LegendItem[] = [],
  weather: import("./weather-utils").DayForecast[] = [],
  indicators: import("./section-renderers/indicators").IndicatorData[] = [],
  collectionCalendars: string[] = [],
  collectionTypes: Array<{ name: string; icon: string }> = [],
  allEvents: import("./event-filters").CalendarEvent[] = [],
): Promise<Buffer> {
  const canvas = createCanvas(LANDSCAPE_W, LANDSCAPE_H);
  const ctx = canvas.getContext("2d");

  // Disable antialiasing to match Python PIL rendering
  ctx.antialias = "none";
  ctx.imageSmoothingEnabled = false;

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
