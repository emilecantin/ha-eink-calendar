"""Tests for TypedDict completeness in renderer types."""

import unittest
from typing import get_type_hints

from renderer.types import CalendarEvent, RenderOptions


class TestCalendarEventTypedDict(unittest.TestCase):
    """CalendarEvent should have all fields used in the renderer."""

    def test_has_id_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "id" in hints, "CalendarEvent must have 'id' field"

    def test_has_calendarName_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "calendarName" in hints, "CalendarEvent must have 'calendarName' field"

    def test_has_title_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "title" in hints

    def test_has_start_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "start" in hints

    def test_has_end_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "end" in hints

    def test_has_allDay_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "allDay" in hints

    def test_has_calendarId_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "calendarId" in hints

    def test_has_calendarIcon_field(self):
        hints = get_type_hints(CalendarEvent)
        assert "calendarIcon" in hints


class TestRenderOptionsTypedDict(unittest.TestCase):
    """RenderOptions should have all fields used in font_loader and renderer."""

    def test_has_language_field(self):
        hints = get_type_hints(RenderOptions)
        assert "language" in hints, "RenderOptions must have 'language' field"

    def test_has_font_regular_field(self):
        hints = get_type_hints(RenderOptions)
        assert "font_regular" in hints, "RenderOptions must have 'font_regular' field"

    def test_has_font_medium_field(self):
        hints = get_type_hints(RenderOptions)
        assert "font_medium" in hints, "RenderOptions must have 'font_medium' field"

    def test_has_font_bold_field(self):
        hints = get_type_hints(RenderOptions)
        assert "font_bold" in hints, "RenderOptions must have 'font_bold' field"

    def test_has_waste_calendars_field(self):
        hints = get_type_hints(RenderOptions)
        assert "waste_calendars" in hints

    def test_has_legend_items_field(self):
        hints = get_type_hints(RenderOptions)
        assert "legend_items" in hints


if __name__ == "__main__":
    unittest.main()
