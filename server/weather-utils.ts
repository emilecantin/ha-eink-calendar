/**
 * Weather utilities for EPCAL calendar rendering.
 *
 * Handles weather condition icons and forecast lookups.
 */

import { isSameDay } from "date-fns";

/**
 * Weather forecast for a single day
 */
export interface DayForecast {
  date: Date;
  condition: string; // sunny, cloudy, snowy, rainy, etc.
  tempHigh: number | null;
  tempLow: number | null;
}

/**
 * Weather icon mapping (condition -> Unicode symbol)
 * These render with Symbola or DejaVu Sans fonts
 */
const WEATHER_ICONS: { [condition: string]: string } = {
  sunny: "☀", // U+2600
  clear: "☀",
  "clear-night": "☽", // U+263D
  partlycloudy: "⛅", // U+26C5
  cloudy: "☁", // U+2601
  fog: "▒", // U+2592 (medium shade)
  hail: "☁",
  lightning: "⚡", // U+26A1
  "lightning-rainy": "⛈", // U+26C8
  pouring: "☔", // U+2614
  rainy: "☂", // U+2602
  snowy: "❄", // U+2744
  "snowy-rainy": "❄",
  windy: "≋", // U+224B
  "windy-variant": "≋",
  exceptional: "⚠", // U+26A0
};

/**
 * Get weather icon for a condition
 *
 * @param condition - Weather condition string (e.g., "sunny", "rainy")
 * @returns Unicode weather symbol, or "?" if unknown
 */
export function getWeatherIcon(condition: string): string {
  return WEATHER_ICONS[condition.toLowerCase()] || "?";
}

/**
 * Get forecast for a specific date from forecast array
 *
 * @param forecasts - Array of daily forecasts
 * @param date - Date to find forecast for
 * @returns Forecast for the date, or undefined if not found
 */
export function getForecastForDate(
  forecasts: DayForecast[],
  date: Date,
): DayForecast | undefined {
  return forecasts.find((f) => isSameDay(f.date, date));
}
