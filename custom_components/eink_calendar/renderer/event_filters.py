"""Event filtering utilities for E-Ink Calendar calendar rendering.

Provides functions to filter and organize events for specific days.

IMPORTANT: These functions expect events with INCLUSIVE end dates.
All-day event end dates must be adjusted before reaching this module.
See docs/calendar-event-handling.md for the iCal exclusive end date rule.
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
    # Determine the target timezone from the day parameter
    target_tz = day.tzinfo

    # If day is naive but events are aware, find the first event's timezone
    # to use as the reference (for backward compatibility)
    if target_tz is None and events:
        for event in events:
            start = event.get("start")
            if start and hasattr(start, "tzinfo") and start.tzinfo is not None:
                target_tz = start.tzinfo
                break

    day_start = datetime.combine(day.date(), time.min)
    if target_tz is not None:
        day_start = day_start.replace(tzinfo=target_tz)

    result = []
    for event in events:
        event_start = event.get("start")
        event_end = event.get("end")

        # Skip events without start/end times
        if not event_start or not event_end:
            continue

        # Convert event times to the target timezone for proper comparison
        # instead of stripping tzinfo (which loses time offset information)
        if target_tz is not None and event_start.tzinfo is not None:
            # Both aware: convert event to target timezone
            local_start = event_start.astimezone(target_tz)
            local_end = event_end.astimezone(target_tz)
        elif target_tz is None and event_start.tzinfo is not None:
            # Day is naive, event is aware: strip tz (no target to convert to)
            local_start = event_start.replace(tzinfo=None)
            local_end = event_end.replace(tzinfo=None)
        elif target_tz is not None and event_start.tzinfo is None:
            # Day is aware, event is naive (e.g., all-day events): treat as target tz
            local_start = event_start.replace(tzinfo=target_tz)
            local_end = event_end.replace(tzinfo=target_tz)
        else:
            # Both naive: use as-is
            local_start = event_start
            local_end = event_end

        # Check if event starts on this day (using converted local times)
        starts_on_day = local_start.date() == day.date()

        # Check if event spans this day (started before, ends on/after)
        spans_day = local_start < day_start and local_end >= day_start

        if starts_on_day or spans_day:
            result.append(
                {
                    "event": event,
                    "startsOnDay": local_start.date() == day.date(),
                    "endsOnDay": local_end.date() == day.date(),
                }
            )

    return result


def get_collection_icons_for_day(
    waste_events: list[CalendarEvent], day: datetime,
) -> list[str]:
    """Get collection calendar icons for a specific day.

    Args:
        waste_events: Waste collection events only (already separated from regular events)
        day: Date to check for collection events

    Returns:
        Array of icons for collections on this day (deduplicated)
    """
    if not waste_events:
        return []

    icons = []
    seen_icons = set()

    for event in waste_events:
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
