"""Unit tests for i18n date formatting."""

from datetime import datetime

from renderer.i18n import format_short_date, format_short_date_range, get_section_title


class TestFormatShortDate:
    """Test locale-aware short date formatting (e.g., 'JAN 27' vs '27 JAN')."""

    def test_english_format(self):
        dt = datetime(2026, 3, 27)
        assert format_short_date(dt, "en") == "MAR 27"

    def test_french_format(self):
        dt = datetime(2026, 3, 27)
        assert format_short_date(dt, "fr") == "27 MAR"

    def test_french_february(self):
        dt = datetime(2026, 2, 14)
        assert format_short_date(dt, "fr") == "14 FÉV"

    def test_english_january(self):
        dt = datetime(2026, 1, 1)
        assert format_short_date(dt, "en") == "JAN 1"

    def test_unknown_lang_falls_back_to_french(self):
        dt = datetime(2026, 6, 15)
        assert format_short_date(dt, "de") == "15 JUN"


class TestFormatShortDateRange:
    """Test locale-aware short date range formatting for multi-day events."""

    def test_english_range_same_month(self):
        start = datetime(2026, 1, 25)
        end = datetime(2026, 1, 27)
        assert format_short_date_range(start, end, "en") == "JAN 25-27"

    def test_french_range_same_month(self):
        start = datetime(2026, 1, 25)
        end = datetime(2026, 1, 27)
        assert format_short_date_range(start, end, "fr") == "25-27 JAN"

    def test_english_range_cross_month(self):
        start = datetime(2026, 1, 30)
        end = datetime(2026, 2, 2)
        assert format_short_date_range(start, end, "en") == "JAN 30-FEB 2"

    def test_french_range_cross_month(self):
        start = datetime(2026, 1, 30)
        end = datetime(2026, 2, 2)
        assert format_short_date_range(start, end, "fr") == "30 JAN-2 FÉV"


class TestGetSectionTitle:
    """Test locale-aware section title strings."""

    def test_legend_french(self):
        assert get_section_title("legend", "fr") == "Légende"

    def test_legend_english(self):
        assert get_section_title("legend", "en") == "Legend"

    def test_upcoming_french(self):
        assert get_section_title("upcoming", "fr") == "À VENIR"

    def test_upcoming_english(self):
        assert get_section_title("upcoming", "en") == "UPCOMING"

    def test_unknown_lang_falls_back_to_french(self):
        assert get_section_title("legend", "de") == "Légende"
        assert get_section_title("upcoming", "de") == "À VENIR"
