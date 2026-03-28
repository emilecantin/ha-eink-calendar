"""Landscape Week section renderer (6-day columns in upper right)."""

from datetime import datetime, timedelta

from PIL import Image, ImageDraw

from ..event_filters import get_collection_icons_for_day, get_events_for_day
from ..event_renderer import draw_overflow_indicator, sort_events_by_priority
from ..i18n import format_day_abbr
from ..icon_utils import create_inverted_icon, get_mdi_icon
from ..layout_config import COLORS, DISPLAY, LAYOUT_LANDSCAPE, MARGINS
from ..text_utils import wrap_text
from ..types import CalendarEvent, FontDict, WeatherData
from ..weather_utils import get_forecast_for_date, get_weather_icon


def draw_landscape_week_section(
    draw: ImageDraw.ImageDraw,
    fonts: FontDict,
    events: list[CalendarEvent],
    today: datetime,
    is_red: bool,
    weather_data: WeatherData | None = None,
    waste_events: list[CalendarEvent] | None = None,
    *,
    img: Image.Image,
    lang: str = "fr",
) -> None:
    """Draw the Week section in landscape layout (6-day columns).

    Args:
        draw: PIL ImageDraw object
        fonts: Font dictionary from font_loader
        events: List of regular calendar events (no waste)
        today: Current date
        is_red: Whether drawing on red layer
        weather_data: Weather data from coordinator (optional)
        waste_events: Processed waste collection events
        img: PIL Image object for pasting icons
    """
    if waste_events is None:
        waste_events = []

    section_x = LAYOUT_LANDSCAPE["TODAY"]["width"]
    section_width = LAYOUT_LANDSCAPE["RIGHT_PANEL"]["width"]
    section_height = LAYOUT_LANDSCAPE["WEEK"]["height"]
    tomorrow = today + timedelta(days=1)

    # Grid dimensions
    margin = MARGINS["STANDARD"]
    landscape_h = DISPLAY["LANDSCAPE"]["height"]
    grid_left = section_x
    grid_top = margin
    grid_right = section_x + section_width - margin
    grid_bottom = section_height  # Vertical dividers stop at Week section bottom
    display_bottom = landscape_h - margin  # But bottom border extends to display bottom
    day_width = (grid_right - grid_left) / 6
    day_header_height = 70

    # Draw section borders and shared lines (black layer only)
    # PIL line() draws borders offset by 1px compared to Canvas. For width=2,
    # PIL draws at y=N and y=N+1, while Canvas draws centered at y=N-1 and y=N.
    # We offset by -1 to match Canvas behavior.
    if not is_red:
        # Top line
        draw.line(
            [(grid_left, grid_top - 1), (grid_right, grid_top - 1)],
            fill=COLORS["BLACK"],
            width=2,
        )

        # Right line (full height to display bottom)
        draw.line(
            [
                (grid_right - 1, grid_top - 1),
                (grid_right - 1, display_bottom - 1),
            ],
            fill=COLORS["BLACK"],
            width=2,
        )

        # Header separator
        header_line_y = grid_top + day_header_height
        draw.line(
            [(grid_left, header_line_y - 1), (grid_right, header_line_y - 1)],
            fill=COLORS["BLACK"],
            width=2,
        )

        # Vertical dividers between columns
        for d in range(1, 6):
            divider_x = grid_left + d * day_width
            draw.line(
                [(divider_x - 1, grid_top - 1), (divider_x - 1, grid_bottom - 1)],
                fill=COLORS["BLACK"],
                width=2,
            )

        # Bottom line separating Week from À venir section
        draw.line(
            [(grid_left, grid_bottom - 1), (grid_right, grid_bottom - 1)],
            fill=COLORS["BLACK"],
            width=2,
        )

        # Note: The À venir section draws its own bottom border at display_bottom
        # for the right panel area (x=400-1288)

    # Draw each day column
    for d in range(6):
        day = tomorrow + timedelta(days=d)
        is_weekend_day = day.weekday() >= 5  # Saturday=5, Sunday=6
        day_x = grid_left + d * day_width

        # Weekend background (red layer)
        # Border with width=2 at grid_top-1 spans y=(grid_top-1) to y=grid_top
        # Fill should start at grid_top+1 to avoid covering the border
        # For the last column, stop 2 pixels before to avoid covering right border
        if is_weekend_day and is_red:
            right_edge = day_x + day_width - 1
            if d == 5:  # Last column - avoid covering right border at x=1287-1288
                right_edge = day_x + day_width - 2
            draw.rectangle(
                [
                    (day_x + 1, grid_top + 1),
                    (right_edge, grid_top + day_header_height - 1),
                ],
                fill=COLORS["RED"],
            )

        # Get forecast for this day
        day_forecast = get_forecast_for_date(weather_data, day)

        # Draw day header
        text_color = COLORS["WHITE"] if (is_red and is_weekend_day) else COLORS["BLACK"]
        draw_condition = (is_red and is_weekend_day) or (
            not is_red and not is_weekend_day
        )

        if draw_condition:
            left_margin = day_x + 8
            right_margin = day_x + day_width - 8

            # 3-letter day name
            day_name_font = fonts["bold"][18]
            day_name = format_day_abbr(day, lang)
            draw.text(
                (left_margin, grid_top + 10),
                day_name,
                fill=text_color,
                font=day_name_font,
            )

            # Day number
            day_num_font = fonts["bold"][32]
            day_num = day.strftime("%d").lstrip("0")
            draw.text(
                (left_margin, grid_top + 34),
                day_num,
                fill=text_color,
                font=day_num_font,
            )

            # Weather on the right side
            if day_forecast:
                temp_font = fonts["bold"][16]
                has_high = day_forecast.get("temperature") is not None
                has_low = day_forecast.get("templow") is not None

                # Calculate temp width for positioning
                temp_width = 0
                if has_high or has_low:
                    temp_val = day_forecast.get("temperature", 0)
                    templow_val = day_forecast.get("templow", 0)
                    high_temp = f"{round(temp_val)}°" if has_high else ""
                    low_temp = f"{round(templow_val)}°" if has_low else ""

                    high_bbox = (
                        draw.textbbox((0, 0), high_temp, font=temp_font)
                        if has_high
                        else (0, 0, 0, 0)
                    )
                    low_bbox = (
                        draw.textbbox((0, 0), low_temp, font=temp_font)
                        if has_low
                        else (0, 0, 0, 0)
                    )
                    temp_width = max(
                        high_bbox[2] - high_bbox[0], low_bbox[2] - low_bbox[0]
                    )

                    # Draw temps (right-aligned)
                    if has_high:
                        high_width = high_bbox[2] - high_bbox[0]
                        draw.text(
                            (right_margin - high_width, grid_top + 16),
                            high_temp,
                            fill=text_color,
                            font=temp_font,
                        )
                    if has_low:
                        low_width = low_bbox[2] - low_bbox[0]
                        draw.text(
                            (right_margin - low_width, grid_top + 36),
                            low_temp,
                            fill=text_color,
                            font=temp_font,
                        )

                # Weather icon (MDI PNG)
                condition = day_forecast.get("condition", "")
                icon_size = 32
                icon = get_weather_icon(condition, size=icon_size)
                if icon:
                    icon_width = icon_size
                    icon_x = int(
                        right_margin - temp_width - 6 - icon_width
                        if temp_width > 0
                        else right_margin - icon_width
                    )

                    # On red layer, create white version with opacity-based anti-aliasing
                    if is_red:
                        white_icon = create_inverted_icon(icon)
                        img.paste(
                            white_icon, (int(icon_x), int(grid_top + 18)), white_icon
                        )
                    else:
                        img.paste(icon, (int(icon_x), int(grid_top + 18)), icon)

        # Day events
        day_events_with_indicators = sort_events_by_priority(
            get_events_for_day(events, day)
        )

        event_area_top = grid_top + day_header_height + 8
        event_area_height = section_height - grid_top - day_header_height - 40
        event_height = event_area_height // 8
        max_events_to_show = 8
        day_events = day_events_with_indicators[:max_events_to_show]
        has_more_events = len(day_events_with_indicators) > max_events_to_show

        for index, event_for_day in enumerate(day_events):
            event = event_for_day["event"]
            starts_on_day = event_for_day["startsOnDay"]
            ends_on_day = event_for_day["endsOnDay"]
            event_y = event_area_top + index * event_height

            event_start = event.get("start")
            event_end = event.get("end")
            if not event_start or not event_end:
                continue

            if not is_red:
                time_font = fonts["bold"][14]
                is_multi_day = event_start.date() != event_end.date()

                time_str = ""
                end_time_str = ""

                if event.get("allDay"):
                    # All-day indicator line
                    line_y = event_y + 7
                    line_left = day_x + 5
                    line_right = day_x + day_width - 10
                    tri_size = 5

                    # Main horizontal line
                    line_start_x = line_left + (tri_size if starts_on_day else 0)
                    line_end_x = line_right - (tri_size if ends_on_day else 0)
                    draw.line(
                        [(line_start_x, line_y), (line_end_x, line_y)],
                        fill=COLORS["BLACK"],
                        width=2,
                    )

                    # Start triangle
                    if starts_on_day:
                        draw.polygon(
                            [
                                (line_left, line_y - tri_size),
                                (line_left + tri_size, line_y),
                                (line_left, line_y + tri_size),
                            ],
                            fill=COLORS["BLACK"],
                        )

                    # End triangle
                    if ends_on_day:
                        draw.polygon(
                            [
                                (line_right, line_y - tri_size),
                                (line_right - tri_size, line_y),
                                (line_right, line_y + tri_size),
                            ],
                            fill=COLORS["BLACK"],
                        )

                elif is_multi_day:
                    # Multi-day timed event
                    if starts_on_day and event_start:
                        time_str = event_start.strftime("%H:%M") + " ▶"
                    elif ends_on_day and event_end:
                        time_str = "◀ " + event_end.strftime("%H:%M")
                    else:
                        time_str = "◀ ▶"

                else:
                    # Regular single-day event
                    time_str = event_start.strftime("%H:%M")
                    end_time_str = event_end.strftime("%H:%M")

                # Draw times
                if time_str:
                    draw.text(
                        (day_x + 5, event_y),
                        time_str,
                        fill=COLORS["BLACK"],
                        font=time_font,
                    )
                if end_time_str:
                    end_bbox = draw.textbbox((0, 0), end_time_str, font=time_font)
                    end_width = end_bbox[2] - end_bbox[0]
                    draw.text(
                        (day_x + day_width - end_width - 8, event_y),
                        end_time_str,
                        fill=COLORS["BLACK"],
                        font=time_font,
                    )

                # Calendar icon (MDI PNG)
                calendar_icon = event.get("calendarIcon")
                if calendar_icon:
                    icon_size = 14
                    icon_img = get_mdi_icon(calendar_icon, size=icon_size)
                    if icon_img:
                        icon_x = day_x + (day_width - icon_size) / 2
                        # Vertically center icon: add offset for all-day events, or align with text
                        icon_y = event_y + (2 if event.get("allDay") else 0)
                        img.paste(icon_img, (int(icon_x), int(icon_y)), icon_img)

                # Title (2 lines max)
                title_font = fonts["regular"][16]
                title_max_width = int(day_width - 12)
                event_title = event.get("title", "")
                title_lines = wrap_text(
                    event_title, title_max_width, title_font, max_lines=2
                )
                for line_index, line in enumerate(title_lines):
                    draw.text(
                        (day_x + 5, event_y + 17 + line_index * 18),
                        line,
                        fill=COLORS["BLACK"],
                        font=title_font,
                    )

        # Overflow indicator
        if has_more_events and is_red:
            overflow_y = event_area_top + max_events_to_show * event_height
            more_count = len(day_events_with_indicators) - max_events_to_show
            overflow_font = fonts["bold"][14]
            draw_overflow_indicator(
                draw, overflow_font, day_x + 5, overflow_y, more_count, language=lang
            )

        # Collection icons (lower right corner)
        collection_icons = get_collection_icons_for_day(waste_events, day)
        if collection_icons and is_red:
            icon_size = 14
            icon_spacing = 3
            current_x = (
                day_x
                + day_width
                - len(collection_icons) * (icon_size + icon_spacing)
                - 6
            )
            icon_y = grid_bottom - icon_size - 4

            for icon_str in collection_icons:
                # Get MDI icon PNG
                icon_img = get_mdi_icon(icon_str, size=icon_size)
                if icon_img:
                    # Create red version
                    red_icon = Image.new("RGBA", icon_img.size, COLORS["RED"] + (255,))
                    red_icon.putalpha(icon_img.split()[3])  # Use original alpha
                    img.paste(red_icon, (int(current_x), int(icon_y)), red_icon)
                current_x += icon_size + icon_spacing
