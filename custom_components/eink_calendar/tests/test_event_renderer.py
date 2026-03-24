"""Unit tests for event_renderer module."""

import unittest
from datetime import datetime

from ..renderer.event_renderer import (
    format_multi_day_time,
    sort_events_by_priority,
)


class TestFormatMultiDayTime(unittest.TestCase):
    """Test format_multi_day_time function."""

    def test_all_day_event(self):
        """Test all-day event returns empty string."""
        event = {
            "start": datetime(2026, 1, 26, 0, 0),
            "end": datetime(2026, 1, 28, 23, 59),
            "allDay": True,
        }

        result = format_multi_day_time(event, starts_on_day=False, ends_on_day=False)  # type: ignore[arg-type]

        self.assertEqual(result, "")

    def test_event_starts_on_day(self):
        """Test multi-day event that starts on the day."""
        event = {
            "start": datetime(2026, 1, 26, 14, 30),
            "end": datetime(2026, 1, 28, 16, 0),
            "allDay": False,
        }

        result = format_multi_day_time(event, starts_on_day=True, ends_on_day=False)  # type: ignore[arg-type]

        self.assertEqual(result, "14:30 ▶")

    def test_event_ends_on_day(self):
        """Test multi-day event that ends on the day."""
        event = {
            "start": datetime(2026, 1, 24, 9, 0),
            "end": datetime(2026, 1, 26, 17, 30),
            "allDay": False,
        }

        result = format_multi_day_time(event, starts_on_day=False, ends_on_day=True)  # type: ignore[arg-type]

        self.assertEqual(result, "◀ 17:30")

    def test_event_spans_day(self):
        """Test multi-day event that spans across the day (middle day)."""
        event = {
            "start": datetime(2026, 1, 25, 9, 0),
            "end": datetime(2026, 1, 27, 17, 0),
            "allDay": False,
        }

        result = format_multi_day_time(event, starts_on_day=False, ends_on_day=False)  # type: ignore[arg-type]

        self.assertEqual(result, "◀ ▶")

    def test_time_formatting_with_leading_zeros(self):
        """Test time formatting preserves leading zeros."""
        event = {
            "start": datetime(2026, 1, 26, 9, 5),
            "end": datetime(2026, 1, 28, 16, 0),
            "allDay": False,
        }

        result = format_multi_day_time(event, starts_on_day=True, ends_on_day=False)  # type: ignore[arg-type]

        self.assertEqual(result, "09:05 ▶")


class TestSortEventsByPriority(unittest.TestCase):
    """Test sort_events_by_priority function."""

    def test_all_day_events_come_first(self):
        """Test all-day events are sorted before timed events."""
        events_for_day = [
            {
                "event": {
                    "title": "Timed Event",
                    "start": datetime(2026, 1, 26, 10, 0),
                    "allDay": False,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
            {
                "event": {
                    "title": "All-Day Event",
                    "start": datetime(2026, 1, 26, 0, 0),
                    "allDay": True,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
        ]

        result = sort_events_by_priority(events_for_day)  # type: ignore[arg-type]

        self.assertEqual(result[0]["event"]["title"], "All-Day Event")
        self.assertEqual(result[1]["event"]["title"], "Timed Event")

    def test_timed_events_sorted_by_start_time(self):
        """Test timed events are sorted by start time."""
        events_for_day = [
            {
                "event": {
                    "title": "Afternoon Meeting",
                    "start": datetime(2026, 1, 26, 15, 0),
                    "allDay": False,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
            {
                "event": {
                    "title": "Morning Meeting",
                    "start": datetime(2026, 1, 26, 9, 0),
                    "allDay": False,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
            {
                "event": {
                    "title": "Lunch",
                    "start": datetime(2026, 1, 26, 12, 0),
                    "allDay": False,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
        ]

        result = sort_events_by_priority(events_for_day)  # type: ignore[arg-type]

        self.assertEqual(result[0]["event"]["title"], "Morning Meeting")
        self.assertEqual(result[1]["event"]["title"], "Lunch")
        self.assertEqual(result[2]["event"]["title"], "Afternoon Meeting")

    def test_all_day_then_timed_sorted_by_time(self):
        """Test combined sorting: all-day first, then timed by start time."""
        events_for_day = [
            {
                "event": {
                    "title": "Afternoon Meeting",
                    "start": datetime(2026, 1, 26, 15, 0),
                    "allDay": False,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
            {
                "event": {
                    "title": "Holiday",
                    "start": datetime(2026, 1, 26, 0, 0),
                    "allDay": True,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
            {
                "event": {
                    "title": "Morning Meeting",
                    "start": datetime(2026, 1, 26, 9, 0),
                    "allDay": False,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
            {
                "event": {
                    "title": "Birthday",
                    "start": datetime(2026, 1, 26, 0, 0),
                    "allDay": True,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            },
        ]

        result = sort_events_by_priority(events_for_day)  # type: ignore[arg-type]

        # All-day events come first (order among them based on start time, which is same)
        self.assertTrue(result[0]["event"]["allDay"])
        self.assertTrue(result[1]["event"]["allDay"])

        # Then timed events sorted by start time
        self.assertEqual(result[2]["event"]["title"], "Morning Meeting")
        self.assertEqual(result[3]["event"]["title"], "Afternoon Meeting")

    def test_empty_list(self):
        """Test sorting empty list returns empty list."""
        result = sort_events_by_priority([])  # type: ignore[arg-type]
        self.assertEqual(result, [])

    def test_single_event(self):
        """Test sorting single event returns same event."""
        events_for_day = [
            {
                "event": {
                    "title": "Single Event",
                    "start": datetime(2026, 1, 26, 10, 0),
                    "allDay": False,
                },
                "startsOnDay": True,
                "endsOnDay": True,
            }
        ]

        result = sort_events_by_priority(events_for_day)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["event"]["title"], "Single Event")


if __name__ == "__main__":
    unittest.main()
