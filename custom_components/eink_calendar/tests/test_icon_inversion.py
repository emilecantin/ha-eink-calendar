"""Unit tests for create_inverted_icon helper."""

from PIL import Image

from renderer.icon_utils import create_inverted_icon


class TestCreateInvertedIcon:
    """Test the icon inversion helper for white-on-colored-background icons."""

    def test_black_opaque_pixel_becomes_white_opaque(self):
        """A fully black, fully opaque pixel should become fully white and opaque."""
        icon = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        # Set one pixel to solid black
        icon.putpixel((1, 1), (0, 0, 0, 255))

        result = create_inverted_icon(icon)

        r, g, b, a = result.getpixel((1, 1))
        assert (r, g, b) == (255, 255, 255), f"Expected white RGB, got ({r}, {g}, {b})"
        assert a == 255, f"Expected full opacity, got {a}"

    def test_transparent_pixel_stays_transparent(self):
        """Fully transparent pixels should remain transparent."""
        icon = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        # Leave all pixels transparent

        result = create_inverted_icon(icon)

        for x in range(4):
            for y in range(4):
                _, _, _, a = result.getpixel((x, y))
                assert a == 0, f"Pixel ({x},{y}) should be transparent, got alpha={a}"

    def test_output_is_rgba(self):
        """Output should always be RGBA mode."""
        icon = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        result = create_inverted_icon(icon)
        assert result.mode == "RGBA"

    def test_output_size_matches_input(self):
        """Output image size should match the input."""
        icon = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
        result = create_inverted_icon(icon)
        assert result.size == (16, 32)

    def test_gray_pixel_produces_partial_opacity(self):
        """A gray pixel (128) should produce a white pixel with reduced opacity.

        The logic inverts grayscale (128 -> 127) and multiplies with alpha (255),
        giving combined_alpha ~= 127.
        """
        icon = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        icon.putpixel((2, 2), (128, 128, 128, 255))

        result = create_inverted_icon(icon)

        r, g, b, a = result.getpixel((2, 2))
        assert (r, g, b) == (255, 255, 255), "RGB should be white"
        # Inverted gray: 255 - 128 = 127, multiplied with alpha 255 -> ~127
        assert 120 <= a <= 135, f"Expected alpha ~127, got {a}"
