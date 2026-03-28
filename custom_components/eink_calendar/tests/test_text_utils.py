"""Unit tests for text_utils module."""

from PIL import ImageFont

from renderer.text_utils import truncate_text


def _load_font(size: int = 20) -> ImageFont.FreeTypeFont:
    """Load a basic font for testing."""
    return ImageFont.load_default(size=size)


class TestTruncateText:
    """Tests for the truncate_text function."""

    def test_empty_string_returns_empty(self):
        font = _load_font()
        result = truncate_text("", 100, font)
        assert result == ""

    def test_short_string_returns_unchanged(self):
        """A string that already fits should be returned as-is."""
        font = _load_font()
        result = truncate_text("Hi", 500, font)
        assert result == "Hi"

    def test_single_char_does_not_loop(self):
        """A single character with a very narrow max_width must not infinite loop."""
        font = _load_font()
        # max_width=1 is too narrow for any character; must terminate
        result = truncate_text("X", 1, font)
        # Should return something (empty or ellipsis), but must not hang
        assert isinstance(result, str)

    def test_short_string_narrower_than_ellipsis(self):
        """A short string that doesn't fit but is shorter than '...' must not loop."""
        font = _load_font()
        # max_width=5 is too narrow for "AB" and also too narrow for "..."
        result = truncate_text("AB", 5, font)
        assert isinstance(result, str)

    def test_long_string_gets_truncated_with_ellipsis(self):
        """A long string that exceeds max_width should be truncated with '...'."""
        font = _load_font()
        long_text = "This is a very long event title that should be truncated"
        result = truncate_text(long_text, 100, font)
        assert result.endswith("...")
        assert len(result) < len(long_text)

    def test_zero_width_does_not_loop(self):
        """Zero max_width must not cause an infinite loop."""
        font = _load_font()
        result = truncate_text("Hello", 0, font)
        assert isinstance(result, str)

    def test_string_that_fits_exactly(self):
        """A string whose rendered width equals max_width should not be truncated."""
        font = _load_font()
        text = "Test"
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), text, font=font)
        exact_width = bbox[2] - bbox[0]

        result = truncate_text(text, exact_width, font)
        assert result == text
