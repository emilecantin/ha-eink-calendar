"""Integration tests for the complete renderer."""

import unittest
from datetime import datetime
from io import BytesIO

from PIL import Image

from ..renderer.renderer import (
    _create_legend,
    _process_events,
    render_calendar,
    render_to_png,
)


class TestProcessEvents(unittest.TestCase):
    """Test _process_events function."""

    def test_process_single_event(self):
        """Test processing a single event."""
        raw_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Test Event",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
                "description": "",
                "location": "",
            }
        ]

        result = _process_events(raw_events)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Test Event")
        self.assertEqual(result[0]["start"].year, 2026)
        self.assertEqual(result[0]["start"].month, 1)
        self.assertEqual(result[0]["start"].day, 26)
        self.assertEqual(result[0]["start"].hour, 14)
        self.assertFalse(result[0]["allDay"])
        self.assertEqual(result[0]["calendarIcon"], "●")  # mdi:calendar → ●
        self.assertEqual(result[0]["calendarId"], "calendar.test")

    def test_process_all_day_event(self):
        """Test processing an all-day event."""
        raw_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "All Day Event",
                "start": "2026-01-26",  # No time component
                "end": "2026-01-26",
                "description": "",
                "location": "",
            }
        ]

        result = _process_events(raw_events)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["allDay"])

    def test_process_event_with_emoji_icon(self):
        """Test processing event with emoji icon (waste calendar)."""
        raw_events = [
            {
                "calendar_id": "calendar.waste_garbage",
                "calendar_icon": "🗑️",  # Direct emoji
                "summary": "Garbage Collection",
                "start": "2026-01-26",
                "end": "2026-01-26",
                "description": "",
                "location": "",
            }
        ]

        result = _process_events(raw_events)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["calendarIcon"], "🗑️")  # Emoji preserved

    def test_process_unknown_mdi_icon(self):
        """Test processing event with unknown MDI icon."""
        raw_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:unknown-icon",
                "summary": "Test Event",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
                "description": "",
                "location": "",
            }
        ]

        result = _process_events(raw_events)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["calendarIcon"], "●")  # Falls back to default

    def test_process_invalid_date_skipped(self):
        """Test that events with invalid dates are skipped."""
        raw_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Invalid Event",
                "start": "invalid-date",
                "end": "invalid-date",
                "description": "",
                "location": "",
            },
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Valid Event",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
                "description": "",
                "location": "",
            },
        ]

        result = _process_events(raw_events)  # type: ignore[arg-type]

        # Invalid event should be skipped
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Valid Event")


class TestCreateLegend(unittest.TestCase):
    """Test _create_legend function."""

    def test_create_legend_from_events(self):
        """Test creating legend from calendar events."""
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Event 1",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
            },
            {
                "calendar_id": "calendar.work",
                "calendar_icon": "mdi:briefcase",
                "summary": "Event 2",
                "start": "2026-01-26T16:00:00",
                "end": "2026-01-26T17:00:00",
            },
        ]

        result = _create_legend(calendar_events)  # type: ignore[arg-type]

        self.assertEqual(len(result), 2)

        # Find personal and work in results
        personal = next((item for item in result if item["name"] == "Personal"), None)
        work = next((item for item in result if item["name"] == "Work"), None)

        self.assertIsNotNone(personal)
        self.assertIsNotNone(work)
        assert personal is not None  # Type narrowing for pyright
        assert work is not None  # Type narrowing for pyright
        self.assertEqual(personal["icon"], "●")
        self.assertEqual(work["icon"], "■")

    def test_create_legend_deduplicates_calendars(self):
        """Test legend only includes each calendar once."""
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Event 1",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
            },
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Event 2",
                "start": "2026-01-26T16:00:00",
                "end": "2026-01-26T17:00:00",
            },
        ]

        result = _create_legend(calendar_events)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Personal")


class TestRenderCalendar(unittest.TestCase):
    """Test complete render_calendar function."""

    def test_render_with_simple_event(self):
        """Test rendering calendar with a simple event."""
        calendar_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Test Meeting",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
                "description": "",
                "location": "",
            }
        ]
        waste_events = []
        weather_data = None
        now = datetime(2026, 1, 25, 10, 0, 0)  # Sunday, Jan 25
        options = {}

        result = render_calendar(
            calendar_events, waste_events, weather_data, now, options
        )

        # Check structure
        self.assertIsNotNone(result.black_layer_full)
        self.assertIsNotNone(result.red_layer_full)
        self.assertIsNotNone(result.etag)
        self.assertEqual(result.timestamp, now)

        # Check chunks can be extracted
        black_top = result.get_black_top()
        black_bottom = result.get_black_bottom()
        red_top = result.get_red_top()
        red_bottom = result.get_red_bottom()

        self.assertIsInstance(black_top, bytes)
        self.assertIsInstance(black_bottom, bytes)
        self.assertIsInstance(red_top, bytes)
        self.assertIsInstance(red_bottom, bytes)

    def test_render_to_png_produces_valid_image(self):
        """Test render_to_png produces a valid PNG image."""
        calendar_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Test Meeting",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
                "description": "",
                "location": "",
            }
        ]
        waste_events = []
        weather_data = None
        now = datetime(2026, 1, 25, 10, 0, 0)
        options = {}

        png_data = render_to_png(  # type: ignore[arg-type]
            calendar_events, waste_events, weather_data, now, options
        )

        # Check it's valid PNG data
        self.assertIsInstance(png_data, bytes)
        self.assertGreater(len(png_data), 0)

        # Try to open as image
        img = Image.open(BytesIO(png_data))
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.size, (1304, 984))  # Landscape display size

    def test_render_with_tomorrow_event(self):
        """Test rendering calendar with an event tomorrow."""
        calendar_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Tomorrow's Event",
                "start": "2026-01-26T10:00:00",  # Monday
                "end": "2026-01-26T11:00:00",
                "description": "",
                "location": "",
            }
        ]
        waste_events = []
        weather_data = None
        now = datetime(2026, 1, 25, 20, 0, 0)  # Sunday evening
        options = {}

        result = render_calendar(
            calendar_events, waste_events, weather_data, now, options
        )

        # Should render successfully
        self.assertIsNotNone(result.etag)


class TestEventDebug(unittest.TestCase):
    """Debug tests to identify missing event issue."""

    def test_event_on_tomorrow_appears_in_week_section(self):
        """Test that an event tomorrow should appear in the week section."""
        calendar_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Tomorrow's Meeting",
                "start": "2026-01-26T14:00:00",  # Monday Jan 26
                "end": "2026-01-26T15:00:00",
                "description": "",
                "location": "",
            }
        ]

        # Today is Sunday Jan 25
        _ = datetime(2026, 1, 25, 10, 0, 0)

        # Process events
        processed = _process_events(calendar_events)  # type: ignore[arg-type]

        # Event should be processed
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]["title"], "Tomorrow's Meeting")
        self.assertEqual(processed[0]["start"].day, 26)

        # Check it would appear for tomorrow
        from ..renderer.event_filters import get_events_for_day

        tomorrow = datetime(2026, 1, 26, 10, 0, 0)
        events_for_tomorrow = get_events_for_day(processed, tomorrow)

        # Event should be found for tomorrow
        self.assertEqual(len(events_for_tomorrow), 1)
        self.assertEqual(events_for_tomorrow[0]["event"]["title"], "Tomorrow's Meeting")


if __name__ == "__main__":
    unittest.main()
