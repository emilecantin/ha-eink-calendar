"""Main calendar renderer for E-Paper Calendar integration."""

import locale
import logging
from datetime import datetime
from io import BytesIO

from dateutil import parser
from PIL import Image, ImageDraw

from .bitmap_utils import calculate_etag, extract_chunk, image_to_1bit
from .font_loader import get_fonts
from .layout_config import COLORS, DISPLAY
from .section_renderers.landscape_today import draw_landscape_today_section
from .section_renderers.landscape_upcoming import draw_landscape_upcoming_section
from .section_renderers.landscape_week import draw_landscape_week_section
from .types import CalendarEvent, RenderOptions, WeatherData

_LOGGER = logging.getLogger(__name__)

# Set French locale for date formatting
try:
    locale.setlocale(locale.LC_TIME, "fr_CA.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    except locale.Error:
        _LOGGER.warning("Could not set French locale, dates will be in English")


class RenderedCalendar:
    """Container for rendered calendar data."""

    def __init__(
        self, black_layer: bytes, red_layer: bytes, etag: str, timestamp: datetime
    ):
        self.black_layer_full = black_layer
        self.red_layer_full = red_layer
        self.etag = etag
        self.timestamp = timestamp
        self.width = DISPLAY["LANDSCAPE"]["width"]
        self.height = DISPLAY["LANDSCAPE"]["height"]

    def get_black_top(self) -> bytes:
        """Get top half of black layer."""
        return extract_chunk(self.black_layer_full, self.width, self.height, True)

    def get_black_bottom(self) -> bytes:
        """Get bottom half of black layer."""
        return extract_chunk(self.black_layer_full, self.width, self.height, False)

    def get_red_top(self) -> bytes:
        """Get top half of red layer."""
        return extract_chunk(self.red_layer_full, self.width, self.height, True)

    def get_red_bottom(self) -> bytes:
        """Get bottom half of red layer."""
        return extract_chunk(self.red_layer_full, self.width, self.height, False)


def render_calendar(
    calendar_events: list[CalendarEvent],
    waste_events: list[CalendarEvent],
    weather_data: WeatherData | None,
    now: datetime,
    options: RenderOptions,
) -> RenderedCalendar:
    """Render calendar to bitmap layers.

    Args:
        calendar_events: Regular calendar events
        waste_events: Waste collection events
        weather_data: Weather forecast data
        now: Current date/time
        options: User configuration options

    Returns:
        RenderedCalendar with bitmap layers
    """
    width = DISPLAY["LANDSCAPE"]["width"]
    height = DISPLAY["LANDSCAPE"]["height"]

    # Load fonts
    fonts = get_fonts(options)

    # Process events (parse dates, convert icons)
    processed_events = _process_events(calendar_events + waste_events)

    # Get waste calendar IDs from options
    waste_calendar_ids = options.get("waste_calendars", [])

    # Create legend from regular calendars
    legend = _create_legend(calendar_events)

    # Create black layer
    black_img = Image.new("RGB", (width, height), COLORS["WHITE"])
    black_draw = ImageDraw.Draw(black_img)

    # Create red layer
    red_img = Image.new("RGB", (width, height), COLORS["WHITE"])
    red_draw = ImageDraw.Draw(red_img)

    # Draw black layer sections
    draw_landscape_today_section(
        black_draw,
        fonts,
        processed_events,
        now,
        is_red=False,
        weather_data=weather_data,
        legend=legend,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_week_section(
        black_draw,
        fonts,
        processed_events,
        now,
        is_red=False,
        weather_data=weather_data,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_upcoming_section(
        black_draw, fonts, processed_events, now, is_red=False
    )

    # Draw red layer sections
    draw_landscape_today_section(
        red_draw,
        fonts,
        processed_events,
        now,
        is_red=True,
        weather_data=weather_data,
        legend=legend,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_week_section(
        red_draw,
        fonts,
        processed_events,
        now,
        is_red=True,
        weather_data=weather_data,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_upcoming_section(red_draw, fonts, processed_events, now, is_red=True)

    # Convert to 1-bit bitmaps
    black_layer = image_to_1bit(black_img, is_red_layer=False)
    red_layer = image_to_1bit(red_img, is_red_layer=True)

    # Calculate ETag
    etag = calculate_etag(black_layer, red_layer)

    return RenderedCalendar(black_layer, red_layer, etag, now)


def render_to_png(
    calendar_events: list[CalendarEvent],
    waste_events: list[CalendarEvent],
    weather_data: WeatherData | None,
    now: datetime,
    options: RenderOptions,
) -> bytes:
    """Render calendar to PNG for preview.

    Args:
        calendar_events: Regular calendar events
        waste_events: Waste collection events
        weather_data: Weather forecast data
        now: Current date/time
        options: User configuration options

    Returns:
        PNG image data
    """
    width = DISPLAY["LANDSCAPE"]["width"]
    height = DISPLAY["LANDSCAPE"]["height"]

    # Load fonts
    fonts = get_fonts(options)

    # Process events (parse dates, convert icons)
    processed_events = _process_events(calendar_events + waste_events)

    # Get waste calendar IDs from options
    waste_calendar_ids = options.get("waste_calendars", [])

    # Create legend from regular calendars
    legend = _create_legend(calendar_events)

    # Create composite image
    img = Image.new("RGB", (width, height), COLORS["WHITE"])
    draw = ImageDraw.Draw(img)

    # Draw all sections on the same image for preview
    draw_landscape_today_section(
        draw,
        fonts,
        processed_events,
        now,
        is_red=False,
        weather_data=weather_data,
        legend=legend,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_week_section(
        draw,
        fonts,
        processed_events,
        now,
        is_red=False,
        weather_data=weather_data,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_upcoming_section(draw, fonts, processed_events, now, is_red=False)

    # Draw red layer elements on top
    draw_landscape_today_section(
        draw,
        fonts,
        processed_events,
        now,
        is_red=True,
        weather_data=weather_data,
        legend=legend,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_week_section(
        draw,
        fonts,
        processed_events,
        now,
        is_red=True,
        weather_data=weather_data,
        collection_calendar_ids=waste_calendar_ids,
    )
    draw_landscape_upcoming_section(draw, fonts, processed_events, now, is_red=True)

    # Convert to PNG
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _process_events(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Process raw events from coordinator into rendering format.

    Parses dates, converts MDI icons to Unicode, and adds metadata.

    Args:
        events: Raw events from coordinator

    Returns:
        Processed events ready for rendering
    """
    processed = []

    for index, event in enumerate(events):
        # Parse dates (handle both datetime strings and date strings)
        start_raw = event.get("start")
        end_raw = event.get("end")

        if not start_raw or not end_raw:
            continue

        try:
            # If already datetime, use as-is; otherwise parse string
            if isinstance(start_raw, datetime):
                start = start_raw
                start_str = start.isoformat()
            else:
                start_str = str(start_raw)
                start = parser.parse(start_str)

            if isinstance(end_raw, datetime):
                end = end_raw
                end_str = end.isoformat()
            else:
                end_str = str(end_raw)
                end = parser.parse(end_str)
        except (ValueError, TypeError) as e:
            _LOGGER.warning("Failed to parse event dates: %s", e)
            continue

        # Determine if all-day event (no time component in string)
        all_day = "T" not in start_str

        # Keep MDI icon string for PNG icon lookup
        calendar_icon = event.get("calendar_icon", "")
        # Default to calendar icon if no custom icon specified
        if not calendar_icon:
            calendar_icon = "mdi:calendar"

        # Create processed event
        processed.append(
            {
                "id": f"{event.get('calendar_id', 'unknown')}-{index}",
                "title": event.get("summary", "Untitled"),
                "start": start,
                "end": end,
                "allDay": all_day,
                "calendarIcon": calendar_icon,
                "calendarId": event.get("calendar_id", ""),
            }
        )

    return processed


def _create_legend(calendar_events: list[CalendarEvent]) -> list[dict[str, str]]:
    """Create legend from calendar events.

    Extracts unique calendar icons and names for the legend.

    Args:
        calendar_events: Regular calendar events (not waste)

    Returns:
        List of legend items with icon and name
    """
    seen_calendars = {}

    for event in calendar_events:
        calendar_id = event.get("calendar_id", "")
        if calendar_id and calendar_id not in seen_calendars:
            # Get calendar icon (keep MDI format for PNG lookup)
            icon = event.get("calendar_icon", "")
            if not icon:
                icon = "mdi:calendar"

            # Extract calendar name from ID (e.g., "calendar.personal" -> "Personal")
            name = calendar_id.replace("calendar.", "").replace("_", " ").title()

            seen_calendars[calendar_id] = {"icon": icon, "name": name}

    return list(seen_calendars.values())
