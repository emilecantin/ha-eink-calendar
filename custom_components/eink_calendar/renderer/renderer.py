"""Main calendar renderer for E-Paper Calendar integration.

All-day event end dates from HA are EXCLUSIVE per iCal/RFC 5545.
The adjustment (subtract 1 day) is applied in _process_events().
See docs/calendar-event-handling.md for the full explanation.
"""

import logging
from datetime import date, datetime, timedelta
from io import BytesIO

from dateutil import parser
from PIL import Image, ImageChops, ImageDraw

from .bitmap_utils import calculate_etag, extract_chunk, image_to_1bit
from .font_loader import get_fonts
from .i18n import format_date, format_day_abbr, format_day_name, format_month_abbr
from .layout_config import COLORS, DISPLAY
from .section_renderers.landscape_today import draw_landscape_today_section
from .section_renderers.landscape_upcoming import draw_landscape_upcoming_section
from .section_renderers.landscape_week import draw_landscape_week_section
from .types import CalendarEvent, RenderOptions, WeatherData

_LOGGER = logging.getLogger(__name__)


class RenderedCalendar:
    """Container for rendered calendar data."""

    def __init__(
        self,
        black_layer: bytes,
        red_layer: bytes,
        preview_png: bytes,
        etag: str,
        timestamp: datetime,
    ):
        self.black_layer_full = black_layer
        self.red_layer_full = red_layer
        self.preview_png = preview_png
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
    lang = options.get("language", "fr")

    # Process events separately — waste events are only used for collection icons
    processed_events = _process_events(calendar_events)
    processed_waste = _process_events(waste_events)

    # Create legend from regular calendars
    legend = _create_legend(calendar_events)

    def _draw_all_sections(draw: ImageDraw.ImageDraw, is_red: bool) -> None:
        draw_landscape_today_section(
            draw, fonts, processed_events, now, is_red=is_red,
            weather_data=weather_data, legend=legend,
            waste_events=processed_waste, lang=lang,
        )
        draw_landscape_week_section(
            draw, fonts, processed_events, now, is_red=is_red,
            weather_data=weather_data, waste_events=processed_waste,
            lang=lang,
        )
        draw_landscape_upcoming_section(
            draw, fonts, processed_events, now, is_red=is_red,
            lang=lang,
        )

    # Create black layer
    black_img = Image.new("RGB", (width, height), COLORS["WHITE"])
    _draw_all_sections(ImageDraw.Draw(black_img), is_red=False)

    # Create red layer
    red_img = Image.new("RGB", (width, height), COLORS["WHITE"])
    _draw_all_sections(ImageDraw.Draw(red_img), is_red=True)

    # Composite preview from the already-rendered black and red layers.
    # Start with a copy of the black layer, then overlay non-white red pixels.
    # The mask is binary: 255 where the red layer has any non-white pixel, 0 elsewhere.
    preview_img = black_img.copy()
    white_img = Image.new("RGB", (width, height), COLORS["WHITE"])
    red_diff = ImageChops.difference(red_img, white_img).convert("L")
    red_mask = red_diff.point(lambda p: 255 if p > 0 else 0)
    preview_img.paste(red_img, mask=red_mask)

    preview_buf = BytesIO()
    preview_img.save(preview_buf, format="PNG")
    preview_png = preview_buf.getvalue()

    # Convert to 1-bit bitmaps
    black_layer = image_to_1bit(black_img, is_red_layer=False)
    red_layer = image_to_1bit(red_img, is_red_layer=True)

    # Calculate ETag
    etag = calculate_etag(black_layer, red_layer)

    return RenderedCalendar(black_layer, red_layer, preview_png, etag, now)


def render_to_png(
    calendar_events: list[CalendarEvent],
    waste_events: list[CalendarEvent],
    weather_data: WeatherData | None,
    now: datetime,
    options: RenderOptions,
) -> bytes:
    """Render calendar to PNG for preview. Convenience wrapper around render_calendar."""
    return render_calendar(
        calendar_events, waste_events, weather_data, now, options
    ).preview_png


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

        # Determine if all-day event:
        # - date objects (not datetime): always all-day
        # - datetime objects at midnight (00:00:00) with end also at midnight
        #   on a different day: all-day (HA sometimes sends these)
        # - date strings without "T": all-day
        # - anything else: timed event
        if isinstance(start_raw, date) and not isinstance(start_raw, datetime):
            all_day = True
        elif (
            isinstance(start_raw, datetime)
            and start_raw.hour == 0 and start_raw.minute == 0 and start_raw.second == 0
            and isinstance(end_raw, datetime)
            and end_raw.hour == 0 and end_raw.minute == 0 and end_raw.second == 0
            and start_raw.date() != end_raw.date()
        ):
            all_day = True
        elif isinstance(start_raw, str):
            all_day = "T" not in start_str
        else:
            all_day = False

        # All-day events: HA returns exclusive end dates per iCal/RFC 5545.
        # Subtract one day to get the inclusive last day of the event.
        # See docs/calendar-event-handling.md for full explanation.
        if all_day:
            end = end - timedelta(days=1)

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
                "calendarName": event.get("calendar_name"),
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

            # Use friendly name from coordinator, fall back to entity ID
            name = event.get("calendar_name") or (
                calendar_id.replace("calendar.", "").replace("_", " ").title()
            )

            seen_calendars[calendar_id] = {"icon": icon, "name": name}

    return list(seen_calendars.values())
