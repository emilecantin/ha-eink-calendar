"""Landscape Upcoming section renderer (lower right panel)."""

from datetime import datetime, timedelta

from PIL import Image, ImageDraw

from ..i18n import format_short_date, format_short_date_range
from ..icon_utils import get_mdi_icon
from ..layout_config import COLORS, LAYOUT_LANDSCAPE, MARGINS
from ..text_utils import truncate_text
from ..types import CalendarEvent, FontDict


def draw_landscape_upcoming_section(
    draw: ImageDraw.ImageDraw,
    fonts: FontDict,
    events: list[CalendarEvent],
    today: datetime,
    is_red: bool,
    img: Image.Image | None = None,
    lang: str = "fr",
) -> None:
    """Draw the Upcoming section in landscape layout (lower right panel).

    Args:
        draw: PIL ImageDraw object
        fonts: Font dictionary from font_loader
        events: List of all calendar events (will be filtered)
        today: Current date
        is_red: Whether drawing on red layer
    """
    # Get image from draw context if not provided (needed for pasting icons)
    if img is None:
        # ImageDraw.Draw stores reference to the image in _image attribute
        img = draw._image

    section_x = LAYOUT_LANDSCAPE["TODAY"]["width"]
    section_y = LAYOUT_LANDSCAPE["WEEK"]["height"]
    section_width = LAYOUT_LANDSCAPE["RIGHT_PANEL"]["width"]
    section_height = LAYOUT_LANDSCAPE["UPCOMING"]["height"]

    margin = MARGINS["STANDARD"]
    grid_right = section_x + section_width - margin
    grid_bottom = section_y + section_height - margin

    # Draw section border (only bottom line)
    # Apply -1 offset to match Canvas behavior
    if not is_red:
        draw.line(
            [(section_x, grid_bottom - 1), (grid_right, grid_bottom - 1)],
            fill=COLORS["BLACK"],
            width=2,
        )

    # Section header
    if not is_red:
        header_font = fonts["bold"][20]
        draw.text(
            (section_x + 10, section_y + 20),
            "À VENIR",
            fill=COLORS["BLACK"],
            font=header_font,
        )

    # Filter upcoming events - beyond the 6-day window
    window_end = (today + timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    upcoming_events = []
    for event in events:
        event_start = event.get("start")
        event_end = event.get("end")
        if not event_start or not event_end:
            continue

        # Check if multi-day or all-day
        days_diff = (event_end.date() - event_start.date()).days
        is_multi_day = days_diff >= 1

        # Normalize timezone awareness for comparison
        compare_start = event_start
        compare_window_end = window_end

        # Convert to naive if there's a mismatch
        if (event_start.tzinfo is None) != (window_end.tzinfo is None):
            compare_start = (
                event_start.replace(tzinfo=None) if event_start.tzinfo else event_start
            )
            compare_window_end = (
                window_end.replace(tzinfo=None) if window_end.tzinfo else window_end
            )

        # Must start after window and be multi-day or all-day
        if (
            is_multi_day or event.get("allDay")
        ) and compare_start >= compare_window_end:
            upcoming_events.append(event)

    # Sort by date (avoids naive vs aware datetime comparison errors)
    upcoming_events.sort(key=lambda e: e["start"].date())
    upcoming_events = upcoming_events[:12]  # Max 12 events

    # Two-column layout
    col_width = (section_width - 30) / 2
    event_line_height = 32
    start_y = section_y + 50
    max_rows = 6

    for index, event in enumerate(upcoming_events):
        col = index // max_rows
        row = index % max_rows
        x = section_x + 10 + col * (col_width + 10)
        y = start_y + row * event_line_height

        if not is_red:
            # Date
            date_font = fonts["bold"][16]
            event_start = event["start"]
            event_end = event["end"]
            days_diff = (event_end.date() - event_start.date()).days
            is_multi_day = days_diff >= 1

            if is_multi_day:
                date_str = format_short_date_range(event_start, event_end, lang)
            else:
                date_str = format_short_date(event_start, lang)

            draw.text((x, y), date_str, fill=COLORS["BLACK"], font=date_font)

            # Calendar icon + title (MDI PNG)
            title_x = x + 110
            if event.get("calendarIcon"):
                icon_size = 16
                icon_img = get_mdi_icon(event["calendarIcon"], size=icon_size)
                if icon_img:
                    # Vertically center icon with text
                    icon_y = y + 2
                    img.paste(icon_img, (int(title_x), int(icon_y)), icon_img)
                    title_x += 18

            # Title
            title_font = fonts["regular"][16]
            max_title_width = int(
                col_width - 120 - (18 if event.get("calendarIcon") else 0)
            )
            event_title = event.get("title", "")
            truncated_title = truncate_text(event_title, max_title_width, title_font)
            draw.text(
                (title_x, y), truncated_title, fill=COLORS["BLACK"], font=title_font
            )

        # Red bar for multi-day events
        days_diff = (event["end"].date() - event["start"].date()).days
        is_multi_day = days_diff >= 1
        if is_red and is_multi_day:
            draw.rectangle(
                [(x - 6, y + 2), (x - 3, y + 16)],
                fill=COLORS["RED"],
            )
