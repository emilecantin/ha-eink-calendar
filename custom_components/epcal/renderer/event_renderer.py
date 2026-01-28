"""Event rendering utilities for EPCAL calendar rendering.

Provides helper functions for drawing event-related elements.
"""

from datetime import datetime

from PIL import ImageDraw, ImageFont

from .event_filters import EventForDay
from .layout_config import COLORS
from .types import CalendarEvent


def draw_event_triangle(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    direction: str,
    is_red: bool = False,
) -> None:
    """Draw a triangle indicator for all-day events.

    Used to show if an event starts or ends on the current day.

    Args:
        draw: PIL ImageDraw object
        x: X coordinate (point location)
        y: Y coordinate (vertical center of triangle)
        size: Size of triangle
        direction: 'left' or 'right'
        is_red: Whether to draw in red layer
    """
    color = COLORS["RED"] if is_red else COLORS["BLACK"]

    if direction == "right":
        # Triangle pointing right (event starts on this day)
        points = [(x, y - size), (x + size, y), (x, y + size)]
    else:
        # Triangle pointing left (event ends on this day)
        points = [(x, y - size), (x - size, y), (x, y + size)]

    draw.polygon(points, fill=color)


def format_multi_day_time(
    event: CalendarEvent, starts_on_day: bool, ends_on_day: bool
) -> str:
    """Format time display for multi-day events with directional arrows.

    Returns empty string for all-day events.

    Args:
        event: Event dictionary with start/end datetime objects
        starts_on_day: Whether event starts on the day being rendered
        ends_on_day: Whether event ends on the day being rendered

    Returns:
        Formatted time string with arrows
    """
    # All-day events don't show times
    if event.get("allDay"):
        return ""

    # Format time helper
    def format_time(dt: datetime) -> str:
        return dt.strftime("%H:%M")

    start = event.get("start")
    end = event.get("end")

    if starts_on_day and start:
        # Event starts on this day - show start time with right arrow
        return format_time(start) + " ▶"
    elif ends_on_day and end:
        # Event ends on this day - show end time with left arrow
        return "◀ " + format_time(end)
    else:
        # Event continues through this day - show both arrows
        return "◀ ▶"


def draw_overflow_indicator(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
    x: float,
    y: float,
    count: int,
    language: str = "fr",
) -> None:
    """Draw "+X more events" indicator when there are too many events to display.

    Args:
        draw: PIL ImageDraw object
        font: Font to use (should be bold)
        x: X coordinate
        y: Y coordinate (baseline)
        count: Number of additional events
        language: 'fr' or 'en'
    """
    # Format text based on language
    if language == "fr":
        plural = count > 1
        text = f"+{count} autre{'s' if plural else ''} événement{'s' if plural else ''}"
    else:
        text = f"+{count} more"

    draw.text((x, y), text, fill=COLORS["RED"], font=font)


def sort_events_by_priority(
    events_for_day: list[EventForDay],
) -> list[EventForDay]:
    """Sort events by priority: all-day events first, then by start time.

    This ensures consistent event ordering across all sections.

    Args:
        events_for_day: List of EventForDay dicts with event/startsOnDay/endsOnDay

    Returns:
        Sorted list
    """

    def sort_key(event_for_day: EventForDay) -> tuple[int, float]:
        event = event_for_day["event"]
        # All-day events first (return 0), timed events second (return 1)
        # Then sort by start time
        all_day_priority = 0 if event.get("allDay") else 1
        event_start = event.get("start")
        start_timestamp = event_start.timestamp() if event_start else 0.0
        return (all_day_priority, start_timestamp)

    return sorted(events_for_day, key=sort_key)
