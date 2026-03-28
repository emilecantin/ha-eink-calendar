"""Text utility functions for rendering."""

from PIL import ImageDraw, ImageFont


def capitalize(text: str) -> str:
    """Capitalize first letter of string."""
    return text[0].upper() + text[1:] if text else text


def truncate_text(text: str, max_width: int, font: ImageFont.FreeTypeFont) -> str:
    """Truncate text to fit within max_width pixels."""
    if not text or max_width <= 0:
        return ""

    # Create a temporary draw object for measuring
    from PIL import Image

    img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    if text_width <= max_width:
        return text

    # Progressively shorten the base text and append ellipsis.
    # Strip one character at a time from the base portion until it fits.
    ellipsis = "..."
    for end in range(len(text) - 1, 0, -1):
        candidate = text[:end] + ellipsis
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return candidate

    # Even a single character + ellipsis didn't fit; try ellipsis alone
    bbox = draw.textbbox((0, 0), ellipsis, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return ellipsis

    return ""


def wrap_text(
    text: str, max_width: int, font: ImageFont.FreeTypeFont, max_lines: int = 2
) -> list[str]:
    """Wrap text to fit within max_width, returning up to max_lines."""
    from PIL import Image

    img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(img)

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
                if len(lines) >= max_lines:
                    return lines
            current_line = word

    if current_line and len(lines) < max_lines:
        lines.append(current_line)

    # Truncate last line if needed
    if lines and len(lines) == max_lines:
        lines[-1] = truncate_text(lines[-1], max_width, font)

    return lines
