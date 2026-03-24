"""Landscape Today section renderer (full-height left panel)."""

from datetime import datetime

from PIL import Image, ImageChops, ImageDraw, ImageOps

from ..event_filters import get_collection_icons_for_day, get_events_for_day
from ..event_renderer import draw_event_triangle, draw_overflow_indicator
from ..icon_utils import get_mdi_icon
from ..layout_config import COLORS, DISPLAY, LAYOUT_LANDSCAPE, MARGINS
from ..text_utils import wrap_text
from ..types import CalendarEvent, FontDict, WeatherData
from ..weather_utils import get_forecast_for_date, get_weather_icon


def draw_landscape_today_section(
    draw: ImageDraw.ImageDraw,
    fonts: FontDict,
    events: list[CalendarEvent],
    today: datetime,
    is_red: bool,
    weather_data: WeatherData | None = None,
    legend: list[dict[str, str]] | None = None,
    collection_calendar_ids: list[str] | None = None,
    img: Image.Image | None = None,
) -> None:
    """Draw the Today section in landscape layout (full-height left panel).

    Args:
        draw: PIL ImageDraw object
        fonts: Font dictionary from font_loader
        events: List of all calendar events
        today: Current date
        is_red: Whether drawing on red layer
        weather_data: Weather data from coordinator (optional)
        legend: List of legend items with icon/name (optional)
        collection_calendar_ids: List of waste collection calendar IDs
    """
    if legend is None:
        legend = []
    if collection_calendar_ids is None:
        collection_calendar_ids = []

    # Get image from draw context if not provided (needed for pasting icons)
    if img is None:
        # ImageDraw.Draw stores reference to the image in _image attribute
        img = draw._image

    section_width = LAYOUT_LANDSCAPE["TODAY"]["width"]
    section_height = DISPLAY["LANDSCAPE"]["height"]
    margin = MARGINS["STANDARD"]

    # Draw section border
    # PIL rectangle() with width=2 draws borders INSIDE at (coord-1, coord)
    # Top-left: (15, 15) → border at 15-16 ✓
    # Right: section_width=400 → border at 399-400 ✓
    # Bottom: need border at 967-968, so coordinate should be 968
    if not is_red:
        draw.rectangle(
            [
                (margin - 1, margin - 1),
                (section_width, section_height - margin),
            ],
            outline=COLORS["BLACK"],
            width=2,
        )

    # Header
    header_x = margin + 10
    header_y = margin
    header_height = 70
    is_weekend_day = today.weekday() >= 5

    # Weekend header background (red layer)
    # TypeScript: fillRect(margin+1, headerY+1, sectionWidth-margin-2, headerHeight-1)
    # Stop at x=398 to avoid covering right border at x=399-400
    # Stop at y=84 to avoid covering bottom border of header area
    if is_weekend_day and is_red:
        draw.rectangle(
            [
                (margin + 1, header_y + 1),
                (section_width - 2, header_y + header_height - 2),
            ],
            fill=COLORS["RED"],
        )

    # Header text
    draw_condition = (is_weekend_day and is_red) or (not is_weekend_day and not is_red)
    if draw_condition:
        text_color = COLORS["WHITE"] if is_weekend_day else COLORS["BLACK"]

        # Day name
        day_name_font = fonts["bold"][22]
        day_name = today.strftime("%A").capitalize()
        draw.text(
            (header_x, header_y + 8), day_name, fill=text_color, font=day_name_font
        )

        # Full date
        date_font = fonts["bold"][28]
        date_text = today.strftime("%d %B %Y")
        draw.text((header_x, header_y + 36), date_text, fill=text_color, font=date_font)

        # Weather info on the right
        today_forecast = get_forecast_for_date(weather_data, today)
        if today_forecast:
            weather_right_edge = section_width - 15
            temp_font = fonts["bold"][20]

            # Temps
            has_high = today_forecast.get("temperature") is not None
            has_low = today_forecast.get("templow") is not None

            temp_width = 0
            if has_high or has_low:
                temp_val = today_forecast.get("temperature", 0)
                templow_val = today_forecast.get("templow", 0)
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
                temp_width = max(high_bbox[2] - high_bbox[0], low_bbox[2] - low_bbox[0])

                # Draw temps (right-aligned)
                if has_high:
                    high_width = high_bbox[2] - high_bbox[0]
                    draw.text(
                        (weather_right_edge - high_width, header_y + 12),
                        high_temp,
                        fill=text_color,
                        font=temp_font,
                    )
                if has_low:
                    low_width = low_bbox[2] - low_bbox[0]
                    draw.text(
                        (weather_right_edge - low_width, header_y + 38),
                        low_temp,
                        fill=text_color,
                        font=temp_font,
                    )

            # Weather icon (MDI PNG)
            condition = today_forecast.get("condition", "")
            icon_size = 44
            icon = get_weather_icon(condition, size=icon_size)
            if icon:
                icon_width = icon_size
                icon_x = int(
                    weather_right_edge - temp_width - 8 - icon_width
                    if temp_width > 0
                    else weather_right_edge - icon_width
                )

                # On red layer, create white version with opacity-based anti-aliasing
                if is_red:
                    # Get the original alpha and RGB channels
                    r, g, b, a = icon.split()

                    # Convert RGB to grayscale (icon is black/gray on transparent background)
                    gray = icon.convert("L")

                    # Invert grayscale: black (0) → white (255), white (255) → black (0)
                    # This gives us opacity map: icon parts are bright, background is dark
                    inverted_gray = ImageOps.invert(gray)

                    # Multiply with original alpha to respect transparency
                    # This ensures transparent areas stay transparent
                    combined_alpha = ImageChops.multiply(inverted_gray, a)

                    # Create pure white image with combined alpha
                    white_icon = Image.new("RGBA", icon.size, (255, 255, 255, 255))
                    white_icon.putalpha(combined_alpha)
                    img.paste(white_icon, (icon_x, int(header_y + 10)), white_icon)
                else:
                    img.paste(icon, (icon_x, int(header_y + 10)), icon)

    # Separator line at bottom of header
    # PIL line() with width=2 needs -1 offset to match Canvas lineWidth=2 behavior
    if not is_red:
        draw.line(
            [
                (margin, header_y + header_height - 1),
                (section_width, header_y + header_height - 1),
            ],
            fill=COLORS["BLACK"],
            width=2,
        )

    # Event list - 3 lines per event
    event_start_y = header_y + header_height + 8
    line_height = 22
    event_block_height = line_height * 3 + 10
    event_width = section_width - margin - header_x

    # Calculate legend height
    legend_item_height = 18
    legend_header_height = 20
    legend_rows = (len(legend) + 1) // 2 if legend else 0
    legend_height = (
        legend_rows * legend_item_height + legend_header_height if legend else 0
    )
    bottom_padding = 20
    reserved_bottom = bottom_padding + legend_height
    max_events = int(
        (section_height - event_start_y - reserved_bottom) / event_block_height
    )

    # Get today's events
    today_events_with_indicators = get_events_for_day(events, today)
    today_events_with_indicators.sort(
        key=lambda e: e["event"].get("start") or datetime.min
    )
    today_events_with_indicators = today_events_with_indicators[:max_events]

    max_title_width = event_width - 10

    for index, event_for_day in enumerate(today_events_with_indicators):
        event = event_for_day["event"]
        starts_on_day = event_for_day["startsOnDay"]
        ends_on_day = event_for_day["endsOnDay"]
        block_y = event_start_y + index * event_block_height

        event_start = event.get("start")
        event_end = event.get("end")
        if not event_start or not event_end:
            continue
        is_multi_day = event_start.date() != event_end.date()

        if not is_red:
            time_font = fonts["bold"][18]

            if event.get("allDay"):
                # All-day: horizontal line with triangles
                line_y = block_y + 8
                line_left = header_x
                line_right = section_width - 10
                tri_size = 6

                # Main horizontal line
                # PIL line() with width=2 needs -1 offset to match Canvas
                line_start_x = line_left + (tri_size if starts_on_day else 0)
                line_end_x = line_right - (tri_size if ends_on_day else 0)
                draw.line(
                    [(line_start_x, line_y - 1), (line_end_x, line_y - 1)],
                    fill=COLORS["BLACK"],
                    width=2,
                )

                # Triangles
                if starts_on_day:
                    draw_event_triangle(
                        draw, line_left, line_y, tri_size, "right", is_red=False
                    )
                if ends_on_day:
                    draw_event_triangle(
                        draw, line_right, line_y, tri_size, "left", is_red=False
                    )

                # Icon centered on line (MDI PNG)
                calendar_icon = event.get("calendarIcon")
                if calendar_icon:
                    icon_size = 18
                    icon_img = get_mdi_icon(calendar_icon, size=icon_size)
                    if icon_img:
                        icon_x = line_left + (line_right - line_left - icon_size) / 2
                        # Vertically center icon in the all-day event bar
                        icon_y = block_y + 4
                        img.paste(icon_img, (int(icon_x), int(icon_y)), icon_img)

            elif is_multi_day:
                # Multi-day: time with arrows
                if starts_on_day and event_start:
                    time_str = event_start.strftime("%H:%M") + " ▶"
                elif ends_on_day and event_end:
                    time_str = "◀ " + event_end.strftime("%H:%M")
                else:
                    time_str = "◀ ▶"

                draw.text(
                    (header_x, block_y), time_str, fill=COLORS["BLACK"], font=time_font
                )

                # Icon centered (MDI PNG)
                calendar_icon = event.get("calendarIcon")
                if calendar_icon:
                    icon_size = 18
                    icon_img = get_mdi_icon(calendar_icon, size=icon_size)
                    if icon_img:
                        icon_x = header_x + (event_width - icon_size) / 2
                        # Vertically center icon
                        icon_y = block_y + 2
                        img.paste(icon_img, (int(icon_x), int(icon_y)), icon_img)

            else:
                # Regular event: start left, end right, icon centered
                start_time = event_start.strftime("%H:%M")
                end_time = event_end.strftime("%H:%M")

                draw.text(
                    (header_x, block_y),
                    start_time,
                    fill=COLORS["BLACK"],
                    font=time_font,
                )

                end_bbox = draw.textbbox((0, 0), end_time, font=time_font)
                end_width = end_bbox[2] - end_bbox[0]
                draw.text(
                    (header_x + event_width - end_width - 5, block_y),
                    end_time,
                    fill=COLORS["BLACK"],
                    font=time_font,
                )

                # Icon centered (MDI PNG)
                calendar_icon = event.get("calendarIcon")
                if calendar_icon:
                    icon_size = 18
                    icon_img = get_mdi_icon(calendar_icon, size=icon_size)
                    if icon_img:
                        icon_x = header_x + (event_width - icon_size) / 2
                        # Vertically center icon
                        icon_y = block_y + 2
                        img.paste(icon_img, (int(icon_x), int(icon_y)), icon_img)

            # Title (wrapped to 2 lines)
            title_font = fonts["regular"][20]
            event_title = event.get("title", "")
            title_lines = wrap_text(
                event_title, max_title_width, title_font, max_lines=2
            )
            for line_index, line in enumerate(title_lines):
                draw.text(
                    (header_x, block_y + (line_index + 1) * line_height),
                    line,
                    fill=COLORS["BLACK"],
                    font=title_font,
                )

    # Calculate legend position
    legend_x = header_x
    legend_top = section_height - bottom_padding - legend_height

    # Overflow indicator
    total_today_events = len(get_events_for_day(events, today))
    if total_today_events > max_events and is_red:
        more_count = total_today_events - max_events
        y = event_start_y + max_events * event_block_height - 6
        overflow_font = fonts["bold"][18]
        draw_overflow_indicator(
            draw, overflow_font, header_x, y, more_count, language="fr"
        )

    # Collection icons above legend
    collection_icons = get_collection_icons_for_day(
        events, today, collection_calendar_ids
    )
    if collection_icons and is_red:
        icon_size = 18
        icon_spacing = 4
        current_x = (
            section_width - margin - len(collection_icons) * (icon_size + icon_spacing)
        )
        icon_y = legend_top - 8

        for icon_str in collection_icons:
            # Get MDI icon PNG
            icon_img = get_mdi_icon(icon_str, size=icon_size)
            if icon_img:
                # Create red version
                red_icon = Image.new("RGBA", icon_img.size, COLORS["RED"] + (255,))
                red_icon.putalpha(icon_img.split()[3])  # Use original alpha
                img.paste(red_icon, (int(current_x), int(icon_y)), red_icon)
            current_x += icon_size + icon_spacing

    # Legend at bottom
    if legend and not is_red:
        # "Légende" header
        legend_header_font = fonts["bold"][14]
        draw.text(
            (legend_x, legend_top),
            "Légende",
            fill=COLORS["BLACK"],
            font=legend_header_font,
        )

        # Two-column layout
        legend_font = fonts["regular"][14]
        col_width = (section_width - margin - header_x) / 2

        for index, item in enumerate(legend):
            col = index % 2
            row = index // 2
            x = legend_x + col * col_width
            y = legend_top + legend_header_height + row * legend_item_height

            # Icon (MDI PNG)
            icon_size = 14
            icon_img = get_mdi_icon(item["icon"], size=icon_size)
            if icon_img:
                # Vertically center icon with text
                # Offset icon down slightly to align with visual center of text
                icon_y = y + 2
                img.paste(icon_img, (int(x), int(icon_y)), icon_img)

            # Name (truncated if needed)
            name_x = x + 20
            max_name_width = col_width - 25
            name_bbox = draw.textbbox((0, 0), item["name"], font=legend_font)
            name_width = name_bbox[2] - name_bbox[0]

            if name_width <= max_name_width:
                truncated_name = item["name"]
            else:
                # Simple truncation
                truncated_name = item["name"][: int(max_name_width / 8)] + "..."

            draw.text(
                (name_x, y), truncated_name, fill=COLORS["BLACK"], font=legend_font
            )
