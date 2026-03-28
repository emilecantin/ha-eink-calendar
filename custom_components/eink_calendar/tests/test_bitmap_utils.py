"""Tests for bitmap_utils module."""

from PIL import Image

from custom_components.eink_calendar.renderer.bitmap_utils import (
    calculate_etag,
    extract_chunk,
    image_to_1bit,
)


def _reference_image_to_1bit(img: Image.Image, is_red_layer: bool = False) -> bytes:
    """Pure-Python reference implementation (original pixel-by-pixel loop).

    Kept as ground truth for verifying the optimized version.
    """
    width, height = img.size
    pixels = img.load()

    bytes_per_row = (width + 7) // 8
    bitmap = bytearray(b"\xff" * (bytes_per_row * height))

    for y in range(height):
        for x in range(width):
            pixel_raw = pixels[x, y]
            if not isinstance(pixel_raw, tuple) or len(pixel_raw) < 3:
                continue
            r, g, b = int(pixel_raw[0]), int(pixel_raw[1]), int(pixel_raw[2])

            is_red_color = r > 150 and g < 100 and b < 100

            if is_red_layer:
                is_colored = is_red_color
            else:
                brightness = (r + g + b) / 3
                is_colored = brightness < 170 and not is_red_color

            if is_colored:
                byte_index = y * bytes_per_row + x // 8
                bit_index = 7 - (x % 8)
                bitmap[byte_index] &= ~(1 << bit_index)

    return bytes(bitmap)


class TestImageTo1bitBlackLayer:
    """Tests for black layer conversion."""

    def test_all_white_image(self):
        """All-white image should produce all 0xFF bytes."""
        img = Image.new("RGB", (16, 2), (255, 255, 255))
        result = image_to_1bit(img, is_red_layer=False)
        assert result == b"\xff" * 4  # 16px = 2 bytes/row * 2 rows

    def test_all_black_image(self):
        """All-black image should produce all 0x00 bytes."""
        img = Image.new("RGB", (16, 2), (0, 0, 0))
        result = image_to_1bit(img, is_red_layer=False)
        assert result == b"\x00" * 4

    def test_single_black_pixel(self):
        """Single black pixel at (0,0) should clear MSB of first byte."""
        img = Image.new("RGB", (8, 1), (255, 255, 255))
        img.putpixel((0, 0), (0, 0, 0))
        result = image_to_1bit(img, is_red_layer=False)
        # Bit 7 cleared: 0xFF & ~0x80 = 0x7F
        assert result == b"\x7f"

    def test_red_pixels_excluded_from_black_layer(self):
        """Red pixels should NOT appear in the black layer."""
        img = Image.new("RGB", (8, 1), (255, 255, 255))
        img.putpixel((0, 0), (200, 50, 50))  # Red pixel
        result = image_to_1bit(img, is_red_layer=False)
        assert result == b"\xff"  # No colored pixels

    def test_brightness_threshold(self):
        """Pixels at brightness boundary should be handled correctly."""
        # brightness = (169+169+169)/3 = 169 < 170 -> colored
        img_dark = Image.new("RGB", (8, 1), (169, 169, 169))
        result_dark = image_to_1bit(img_dark, is_red_layer=False)
        assert result_dark == b"\x00"

        # brightness = (170+170+170)/3 = 170 >= 170 -> white
        img_light = Image.new("RGB", (8, 1), (170, 170, 170))
        result_light = image_to_1bit(img_light, is_red_layer=False)
        assert result_light == b"\xff"


class TestImageTo1bitRedLayer:
    """Tests for red layer conversion."""

    def test_red_pixels_detected(self):
        """Pure red pixels should appear in red layer."""
        img = Image.new("RGB", (8, 1), (255, 255, 255))
        img.putpixel((0, 0), (200, 50, 50))
        result = image_to_1bit(img, is_red_layer=True)
        assert result == b"\x7f"

    def test_black_pixels_excluded_from_red_layer(self):
        """Black pixels should NOT appear in red layer."""
        img = Image.new("RGB", (8, 1), (0, 0, 0))
        result = image_to_1bit(img, is_red_layer=True)
        assert result == b"\xff"

    def test_red_threshold_boundary(self):
        """Pixels at the red detection boundary."""
        # r=151, g=99, b=99 -> red
        img = Image.new("RGB", (8, 1), (151, 99, 99))
        assert image_to_1bit(img, is_red_layer=True) == b"\x00"

        # r=150, g=100, b=100 -> NOT red (r not > 150)
        img2 = Image.new("RGB", (8, 1), (150, 100, 100))
        assert image_to_1bit(img2, is_red_layer=True) == b"\xff"


class TestImageTo1bitMatchesReference:
    """Verify optimized implementation matches the reference pixel-by-pixel version."""

    def test_matches_reference_mixed_image(self):
        """A mixed image with black, red, white, and gray pixels."""
        img = Image.new("RGB", (24, 10), (255, 255, 255))
        # Add some black pixels
        for x in range(0, 8):
            img.putpixel((x, 0), (0, 0, 0))
        # Add some red pixels
        for x in range(8, 16):
            img.putpixel((x, 1), (200, 30, 30))
        # Add gray pixels at various brightnesses
        for x in range(0, 24):
            img.putpixel((x, 5), (128, 128, 128))
        # Add near-boundary pixels
        for x in range(0, 12):
            img.putpixel((x, 8), (169, 169, 169))  # Just below threshold
        for x in range(12, 24):
            img.putpixel((x, 8), (170, 170, 170))  # At threshold

        # Black layer
        result_black = image_to_1bit(img, is_red_layer=False)
        expected_black = _reference_image_to_1bit(img, is_red_layer=False)
        assert result_black == expected_black

        # Red layer
        result_red = image_to_1bit(img, is_red_layer=True)
        expected_red = _reference_image_to_1bit(img, is_red_layer=True)
        assert result_red == expected_red

    def test_matches_reference_full_display_size(self):
        """Test at actual display resolution (1304x984) with varied content."""
        img = Image.new("RGB", (1304, 984), (255, 255, 255))
        # Paint stripes of different colors
        for y in range(0, 200):
            for x in range(0, 1304):
                img.putpixel((x, y), (0, 0, 0))  # black band
        for y in range(200, 400):
            for x in range(0, 1304):
                img.putpixel((x, y), (220, 40, 40))  # red band
        for y in range(400, 600):
            for x in range(0, 1304):
                img.putpixel((x, y), (169, 169, 169))  # dark gray

        result_black = image_to_1bit(img, is_red_layer=False)
        expected_black = _reference_image_to_1bit(img, is_red_layer=False)
        assert result_black == expected_black

        result_red = image_to_1bit(img, is_red_layer=True)
        expected_red = _reference_image_to_1bit(img, is_red_layer=True)
        assert result_red == expected_red

    def test_matches_reference_non_multiple_of_8_width(self):
        """Width not a multiple of 8 (padding bits)."""
        img = Image.new("RGB", (13, 5), (100, 100, 100))  # dark gray
        img.putpixel((12, 4), (255, 0, 0))  # red pixel at last column

        result_black = image_to_1bit(img, is_red_layer=False)
        expected_black = _reference_image_to_1bit(img, is_red_layer=False)
        assert result_black == expected_black

        result_red = image_to_1bit(img, is_red_layer=True)
        expected_red = _reference_image_to_1bit(img, is_red_layer=True)
        assert result_red == expected_red


class TestExtractChunk:
    """Tests for extract_chunk."""

    def test_top_half(self):
        bitmap = bytes(range(16))  # 16 bytes
        # 8px wide = 1 byte/row, 16 rows
        result = extract_chunk(bitmap, 8, 16, top_half=True)
        assert result == bytes(range(8))

    def test_bottom_half(self):
        bitmap = bytes(range(16))
        result = extract_chunk(bitmap, 8, 16, top_half=False)
        assert result == bytes(range(8, 16))


class TestCalculateEtag:
    """Tests for calculate_etag."""

    def test_consistent_hash(self):
        black = b"\x00" * 10
        red = b"\xff" * 10
        etag1 = calculate_etag(black, red)
        etag2 = calculate_etag(black, red)
        assert etag1 == etag2

    def test_different_input_different_hash(self):
        etag1 = calculate_etag(b"\x00", b"\x00")
        etag2 = calculate_etag(b"\xff", b"\xff")
        assert etag1 != etag2
