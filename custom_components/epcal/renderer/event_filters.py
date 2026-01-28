"""Event filtering utilities for EPCAL calendar rendering.

Provides functions to filter and organize events for specific days.
"""

from datetime import datetime, time
from typing import TypedDict

from .types import CalendarEvent


class EventForDay(TypedDict):
    """Event with day-specific indicators."""

    event: CalendarEvent
    startsOnDay: bool
    endsOnDay: bool


def get_events_for_day(events: list[CalendarEvent], day: datetime) -> list[EventForDay]:
    """Filter events for a specific day with start/end indicators.

    Includes:
    - Events that start on this day
    - Multi-day events that span across this day (started before, end on/after)

    Args:
        events: Array of calendar events (with parsed datetime objects)
        day: Date to filter for

    Returns:
        Events for the day with start/end indicators
    """
    # Ensure day_start has the same timezone awareness as the events
    day_start = datetime.combine(day.date(), time.min)

    # If day is naive but events might be aware, use first event's timezone
    if day.tzinfo is None and events:
        # Check if events have timezone info
        for event in events:
            start = event.get("start")
            if start and hasattr(start, "tzinfo") and start.tzinfo is not None:
                day_start = day_start.replace(tzinfo=start.tzinfo)
                break
    elif day.tzinfo is not None:
        day_start = day_start.replace(tzinfo=day.tzinfo)

    result = []
    for event in events:
        event_start = event.get("start")
        event_end = event.get("end")

        # Skip events without start/end times
        if not event_start or not event_end:
            continue

        # Normalize timezone awareness for comparison
        # If one is aware and the other is naive, make both naive for comparison
        compare_start = event_start
        compare_end = event_end
        compare_day_start = day_start

        # Convert all to naive if there's a mismatch
        if (event_start.tzinfo is None) != (day_start.tzinfo is None):
            compare_start = (
                event_start.replace(tzinfo=None) if event_start.tzinfo else event_start
            )
            compare_end = (
                event_end.replace(tzinfo=None) if event_end.tzinfo else event_end
            )
            compare_day_start = (
                day_start.replace(tzinfo=None) if day_start.tzinfo else day_start
            )

        # Check if event starts on this day
        starts_on_day = event_start.date() == day.date()

        # Check if event spans this day (started before, ends on/after)
        spans_day = (
            compare_start < compare_day_start and compare_end >= compare_day_start
        )

        if starts_on_day or spans_day:
            result.append(
                {
                    "event": event,
                    "startsOnDay": event_start.date() == day.date(),
                    "endsOnDay": event_end.date() == day.date(),
                }
            )

    return result


def get_collection_icons_for_day(
    events: list[CalendarEvent], day: datetime, collection_calendar_ids: list[str]
) -> list[str]:
    """Get collection calendar icons for a specific day.

    Returns icons from collection calendar entities for events on this day.
    Uses the calendar entity's icon directly (no keyword matching).

    Args:
        events: Array of calendar events
        day: Date to check for collection events
        collection_calendar_ids: Array of calendar IDs that are waste collection calendars

    Returns:
        Array of icons for collections on this day (deduplicated)
    """
    if not collection_calendar_ids:
        return []

    icons = []
    seen_icons = set()

    # Find all collection events on this day
    for event in events:
        calendar_id = event.get("calendarId")
        if not calendar_id or calendar_id not in collection_calendar_ids:
            continue

        # Check if event is on this day (all-day events only)
        if not event.get("allDay"):
            continue

        start = event.get("start")
        if not start or start.date() != day.date():
            continue

        # Use the calendar's icon directly
        icon = event.get("calendarIcon")
        if icon and icon not in seen_icons:
            icons.append(icon)
            seen_icons.add(icon)

    return icons
