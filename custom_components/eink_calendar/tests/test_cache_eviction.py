"""Tests for cache eviction in font_loader and icon_utils."""

import unittest

from renderer.font_loader import load_font
from renderer import icon_utils


class TestFontLoaderCache(unittest.TestCase):
    """Test that font_loader uses lru_cache with bounded size."""

    def test_load_font_uses_lru_cache(self):
        """load_font should be decorated with lru_cache."""
        assert hasattr(
            load_font, "cache_info"
        ), "load_font must be wrapped with functools.lru_cache"

    def test_load_font_cache_has_maxsize(self):
        """lru_cache should have a reasonable maxsize (not unlimited)."""
        info = load_font.cache_info()
        assert info.maxsize is not None, "load_font cache must have a finite maxsize"
        assert info.maxsize >= 32, "maxsize should be at least 32"

    def test_load_font_caches_results(self):
        """Calling load_font with same args should return cached result."""
        load_font.cache_clear()
        result1 = load_font(None, 16, "Regular")
        result2 = load_font(None, 16, "Regular")
        assert result1 is result2
        info = load_font.cache_info()
        assert info.hits >= 1


class TestIconUtilsCache(unittest.TestCase):
    """Test that icon_utils uses lru_cache with bounded size."""

    def test_get_font_uses_lru_cache(self):
        """_get_font should be decorated with lru_cache."""
        assert hasattr(
            icon_utils._get_font, "cache_info"
        ), "_get_font must be wrapped with functools.lru_cache"

    def test_get_font_cache_has_maxsize(self):
        """_get_font lru_cache should have a reasonable maxsize."""
        info = icon_utils._get_font.cache_info()
        assert info.maxsize is not None, "_get_font cache must have a finite maxsize"

    def test_get_icon_uses_lru_cache(self):
        """get_icon should be decorated with lru_cache."""
        assert hasattr(
            icon_utils.get_icon, "cache_info"
        ), "get_icon must be wrapped with functools.lru_cache"

    def test_get_icon_cache_has_maxsize(self):
        """get_icon lru_cache should have a reasonable maxsize."""
        info = icon_utils.get_icon.cache_info()
        assert info.maxsize is not None, "get_icon cache must have a finite maxsize"
        assert info.maxsize >= 64, "icon cache maxsize should be at least 64"

    def test_get_icon_caches_results(self):
        """Calling get_icon with same args should return cached result."""
        icon_utils.get_icon.cache_clear()
        result1 = icon_utils.get_icon("calendar", 24, (0, 0, 0, 255))
        result2 = icon_utils.get_icon("calendar", 24, (0, 0, 0, 255))
        assert result1 is result2
        info = icon_utils.get_icon.cache_info()
        assert info.hits >= 1


if __name__ == "__main__":
    unittest.main()
