/**
 * Event filtering utilities for EPCAL calendar rendering.
 *
 * Provides functions to filter and organize events for specific days.
 */

import { startOfDay, isSameDay } from "date-fns";

/**
 * Calendar event interface
 */
export interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay?: boolean;
  calendarColor?: string;
  calendarIcon?: string; // Icon/letter to identify the calendar
  calendarId?: string; // Entity ID of the calendar this event belongs to
}

/**
 * Event with day-specific indicators
 */
export interface EventForDay {
  event: CalendarEvent;
  startsOnDay: boolean;
  endsOnDay: boolean;
}

/**
 * Collection type configuration
 */
export interface CollectionType {
  name: string;
  icon: string;
}

/**
 * Filters events for a specific day and returns them with indicators
 * showing whether each event starts/ends on that day.
 *
 * Includes:
 * - Events that start on this day
 * - Multi-day events that span across this day (started before, end on/after)
 *
 * @param events - Array of calendar events
 * @param day - Date to filter for
 * @returns Events for the day with start/end indicators
 */
export function getEventsForDay(events: CalendarEvent[], day: Date): EventForDay[] {
  const dayStart = startOfDay(day);

  return events
    .filter((e) => {
      const startsOnDay = isSameDay(e.start, day);
      const spansDay = e.start < dayStart && e.end >= dayStart;
      return startsOnDay || spansDay;
    })
    .map((e) => ({
      event: e,
      startsOnDay: isSameDay(e.start, day),
      endsOnDay: isSameDay(e.end, day),
    }));
}

/**
 * Gets collection calendar icons for a specific day
 * Returns icons for each collection type found in events on this day
 *
 * @param events - Array of calendar events
 * @param day - Date to check for collection events
 * @param collectionCalendars - Array of calendar IDs that are collection calendars
 * @param collectionTypes - Array of collection type configurations with icons
 * @returns Array of icon names for collections on this day
 */
export function getCollectionIconsForDay(
  events: CalendarEvent[],
  day: Date,
  collectionCalendars: string[] = [],
  collectionTypes: CollectionType[] = [],
): string[] {
  if (collectionCalendars.length === 0 || collectionTypes.length === 0)
    return [];

  const icons: string[] = [];
  const foundTypes = new Set<string>();

  // Find all collection events on this day
  const collectionEvents = events.filter(
    (e) =>
      e.calendarId &&
      collectionCalendars.includes(e.calendarId) &&
      e.allDay &&
      isSameDay(e.start, day),
  );

  // Keywords for matching event titles to collection types
  const typeKeywords: { [typeName: string]: string[] } = {
    Garbage: ["garbage", "trash", "waste", "déchet", "ordure", "poubelle"],
    Recycling: ["recycling", "recycle", "recyclage", "récupération"],
    Compost: ["compost", "organic", "organique", "food waste"],
    "Yard Waste": ["yard", "green", "vert", "garden"],
    Glass: ["glass", "verre"],
    Paper: ["paper", "papier"],
    Cardboard: ["cardboard", "carton"],
  };

  // Match each event title against collection types using keywords
  for (const event of collectionEvents) {
    const titleLower = event.title.toLowerCase();

    for (const type of collectionTypes) {
      const keywords = typeKeywords[type.name] || [type.name.toLowerCase()];

      if (
        keywords.some((kw) => titleLower.includes(kw)) &&
        !foundTypes.has(type.name)
      ) {
        icons.push(type.icon);
        foundTypes.add(type.name);
      }
    }
  }

  return icons;
}
