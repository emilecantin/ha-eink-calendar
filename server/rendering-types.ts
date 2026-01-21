/**
 * Type definitions for EPCAL calendar rendering.
 *
 * These types will be used in Phase 4 to consolidate function parameters
 * into context objects, reducing parameter bloat from 9-10 parameters to 1.
 */

import { CanvasRenderingContext2D } from "canvas";

/**
 * Calendar event data structure
 */
export interface CalendarEvent {
  id: string;
  summary: string;
  start: Date;
  end: Date;
  allDay: boolean;
  calendar: string;
}

/**
 * Weather forecast data for a single day
 */
export interface DayForecast {
  date: Date;
  high: number;
  low: number;
  condition: string;
  iconUrl?: string;
}

/**
 * Legend item for calendar color key
 */
export interface LegendItem {
  calendar: string;
  color: string;
  label: string;
}

/**
 * Binary sensor indicator data
 */
export interface IndicatorData {
  entityId: string;
  state: 'on' | 'off';
  label: string;
  icon: string;
  shouldDisplay: boolean;
}

/**
 * Collection calendar type configuration
 */
export interface CollectionType {
  name: string;
  icon: string;
}

/**
 * Layout mode for the calendar display
 */
export type LayoutMode = "portrait" | "landscape";

/**
 * Optional rendering options that can be passed to rendering functions
 */
export interface RenderingOptions {
  legend?: LegendItem[];
  weather?: DayForecast[];
  indicators?: IndicatorData[];
  collectionCalendars?: string[];
  collectionTypes?: CollectionType[];
  allEvents?: CalendarEvent[];
}

/**
 * Complete rendering context for a section
 *
 * This consolidates all the parameters currently passed to rendering functions
 * (9-10 parameters) into a single context object.
 */
export interface RenderingContext {
  ctx: CanvasRenderingContext2D;
  events: CalendarEvent[];
  date: Date;
  isRed: boolean;
  layout: LayoutMode;
  options: RenderingOptions;
}

/**
 * Bounding box for a section of the display
 */
export interface SectionBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Style configuration for event rendering
 */
export interface EventRenderStyle {
  timeFont: string;
  titleFont: string;
  iconSize: number;
  eventHeight: number;
  maxTitleLines: number;
  maxEvents?: number;
}

/**
 * Configuration for a specific section renderer
 */
export interface SectionConfig {
  bounds: SectionBounds;
  style: EventRenderStyle;
  showWeather?: boolean;
  showLegend?: boolean;
  showIndicators?: boolean;
}
