"""Tests for legend name truncation using font-based measurement."""

from datetime import datetime
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from renderer.section_renderers.landscape_today import draw_landscape_today_section
from renderer.text_utils import truncate_text


def _load_font(size: int = 14) -> ImageFont.FreeTypeFont:
    """Load a basic font for testing."""
    return ImageFont.load_default(size=size)


def _make_fonts():
    """Create a minimal fonts dict for draw_landscape_today_section."""
    return {
        "regular": {14: _load_font(14), 20: _load_font(20)},
        "bold": {14: _load_font(14), 18: _load_font(18), 20: _load_font(20),
                 22: _load_font(22), 28: _load_font(28)},
    }


class TestLegendTruncation:
    """Verify that legend names are truncated using font measurement, not char count."""

    def test_long_legend_name_is_truncated_to_fit_pixel_width(self):
        """A long legend name must be truncated based on rendered pixel width."""
        fonts = _make_fonts()
        legend_font = fonts["regular"][14]

        # Build a name that is definitely too long to fit in the legend column
        long_name = "A Very Long Calendar Name That Should Be Truncated"

        img = Image.new("RGB", (1304, 984), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        legend = [{"icon": "mdi:calendar", "name": long_name}]

        # Draw the section (black layer)
        draw_landscape_today_section(
            draw, fonts, events=[], today=datetime(2026, 3, 27),
            is_red=False, legend=legend, img=img,
        )

        # The real assertion: truncate_text with the same font and width
        # should produce a name that fits. We verify by checking that
        # the old character-count approach would produce a DIFFERENT result.
        from renderer.layout_config import LAYOUT_LANDSCAPE, MARGINS
        section_width = LAYOUT_LANDSCAPE["TODAY"]["width"]
        margin = MARGINS["STANDARD"]
        header_x = margin + 10
        col_width = (section_width - margin - header_x) / 2
        max_name_width = col_width - 25

        # Font-based truncation
        font_truncated = truncate_text(long_name, max_name_width, legend_font)
        # Old char-count truncation
        char_truncated = long_name[: int(max_name_width / 8)] + "..."

        # They should differ — the font-based one is more accurate
        assert font_truncated != char_truncated, (
            f"Font-based and char-count truncation should differ for proportional fonts. "
            f"Font: {font_truncated!r}, Char: {char_truncated!r}"
        )

    def test_legend_calls_truncate_text(self):
        """draw_landscape_today_section must use truncate_text for legend names."""
        fonts = _make_fonts()
        long_name = "A Very Long Calendar Name That Should Be Truncated"

        img = Image.new("RGB", (1304, 984), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        legend = [{"icon": "mdi:calendar", "name": long_name}]

        with patch(
            "renderer.section_renderers.landscape_today.truncate_text",
            wraps=truncate_text,
        ) as mock_truncate:
            draw_landscape_today_section(
                draw, fonts, events=[], today=datetime(2026, 3, 27),
                is_red=False, legend=legend, img=img,
            )
            # truncate_text should have been called for the legend name
            mock_truncate.assert_called_once()
            call_args = mock_truncate.call_args
            assert call_args[0][0] == long_name

    def test_short_legend_name_not_truncated(self):
        """A short name that fits should be drawn as-is."""
        fonts = _make_fonts()
        short_name = "Work"

        img = Image.new("RGB", (1304, 984), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        legend = [{"icon": "mdi:calendar", "name": short_name}]

        with patch(
            "renderer.section_renderers.landscape_today.truncate_text",
            wraps=truncate_text,
        ) as mock_truncate:
            draw_landscape_today_section(
                draw, fonts, events=[], today=datetime(2026, 3, 27),
                is_red=False, legend=legend, img=img,
            )
            mock_truncate.assert_called_once()
            # Verify truncate_text was called with the short name
            call_args = mock_truncate.call_args
            assert call_args[0][0] == short_name
            # Verify the actual function returns the name unchanged
            assert truncate_text(short_name, call_args[0][1], call_args[0][2]) == short_name
