"""Unit tests for event_filters module."""

import unittest
from datetime import datetime
from typing import cast

from ..renderer.event_filters import (
    get_collection_icons_for_day,
    get_events_for_day,
)
from ..renderer.types import CalendarEvent


def create_event(**kwargs) -> CalendarEvent:
    """Create a test event with default values for required fields."""
    defaults: CalendarEvent = {
        "title": "",
        "start": datetime(2026, 1, 1, 0, 0),
        "end": datetime(2026, 1, 1, 0, 0),
        "allDay": False,
        "calendarId": "calendar.test",
        "calendarIcon": "●",
    }
    return cast(CalendarEvent, {**defaults, **kwargs})


class TestGetEventsForDay(unittest.TestCase):
    """Test get_events_for_day function."""

    def setUp(self):
        """Set up test fixtures."""
        self.today = datetime(2026, 1, 26, 10, 0, 0)  # Monday, Jan 26, 2026 at 10:00

    def test_single_day_event_on_target_day(self):
        """Test single-day event on the target day."""
        events = cast(
            list[CalendarEvent],
            [
                {
                    "id": "1",
                    "title": "Meeting",
                    "start": datetime(2026, 1, 26, 14, 0),
                    "end": datetime(2026, 1, 26, 15, 0),
                    "allDay": False,
                    "calendarId": "calendar.personal",
                    "calendarIcon": "●",
                }
            ],
        )

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["event"]["title"], "Meeting")
        self.assertTrue(result[0]["startsOnDay"])
        self.assertTrue(result[0]["endsOnDay"])

    def test_all_day_event_on_target_day(self):
        """Test all-day event on the target day."""
        events = [
            {
                "id": "1",
                "title": "Holiday",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
            }
        ]

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["startsOnDay"])

    def test_multi_day_event_starting_on_target_day(self):
        """Test multi-day event that starts on target day."""
        events = [
            {
                "id": "1",
                "title": "Conference",
                "start": datetime(2026, 1, 26, 9, 0),
                "end": datetime(2026, 1, 28, 17, 0),
                "allDay": False,
            }
        ]

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["startsOnDay"])
        self.assertFalse(result[0]["endsOnDay"])

    def test_multi_day_event_ending_on_target_day(self):
        """Test multi-day event that ends on target day."""
        events = [
            {
                "id": "1",
                "title": "Conference",
                "start": datetime(2026, 1, 24, 9, 0),
                "end": datetime(2026, 1, 26, 17, 0),
                "allDay": False,
            }
        ]

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["startsOnDay"])
        self.assertTrue(result[0]["endsOnDay"])

    def test_multi_day_event_spanning_target_day(self):
        """Test multi-day event that spans across target day (middle day)."""
        events = [
            {
                "id": "1",
                "title": "Conference",
                "start": datetime(2026, 1, 25, 9, 0),
                "end": datetime(2026, 1, 27, 17, 0),
                "allDay": False,
            }
        ]

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["startsOnDay"])
        self.assertFalse(result[0]["endsOnDay"])

    def test_event_on_different_day(self):
        """Test event on a different day is not included."""
        events = [
            {
                "id": "1",
                "title": "Meeting",
                "start": datetime(2026, 1, 27, 14, 0),
                "end": datetime(2026, 1, 27, 15, 0),
                "allDay": False,
            }
        ]

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 0)

    def test_event_ended_before_target_day(self):
        """Test event that ended before target day is not included."""
        events = [
            {
                "id": "1",
                "title": "Past Event",
                "start": datetime(2026, 1, 24, 14, 0),
                "end": datetime(2026, 1, 25, 15, 0),
                "allDay": False,
            }
        ]

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 0)

    def test_multiple_events_on_same_day(self):
        """Test multiple events on the same day."""
        events = [
            {
                "id": "1",
                "title": "Morning Meeting",
                "start": datetime(2026, 1, 26, 9, 0),
                "end": datetime(2026, 1, 26, 10, 0),
                "allDay": False,
            },
            {
                "id": "2",
                "title": "Lunch",
                "start": datetime(2026, 1, 26, 12, 0),
                "end": datetime(2026, 1, 26, 13, 0),
                "allDay": False,
            },
            {
                "id": "3",
                "title": "Afternoon Meeting",
                "start": datetime(2026, 1, 26, 15, 0),
                "end": datetime(2026, 1, 26, 16, 0),
                "allDay": False,
            },
        ]

        result = get_events_for_day(events, self.today)  # type: ignore[arg-type]

        self.assertEqual(len(result), 3)


class TestGetCollectionIconsForDay(unittest.TestCase):
    """Test get_collection_icons_for_day function."""

    def setUp(self):
        """Set up test fixtures."""
        self.today = datetime(2026, 1, 26, 10, 0, 0)

    def test_collection_event_on_target_day(self):
        """Test waste collection event on target day."""
        events = [
            {
                "id": "1",
                "title": "Garbage Collection",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            }
        ]
        collection_calendar_ids = ["calendar.waste_garbage"]

        result = get_collection_icons_for_day(  # type: ignore[arg-type]
            events, self.today, collection_calendar_ids
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "🗑️")

    def test_multiple_collection_types_on_same_day(self):
        """Test multiple collection types on the same day."""
        events = [
            {
                "id": "1",
                "title": "Garbage",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            },
            {
                "id": "2",
                "title": "Recycling",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_recycling",
                "calendarIcon": "♻️",
            },
        ]
        collection_calendar_ids = ["calendar.waste_garbage", "calendar.waste_recycling"]

        result = get_collection_icons_for_day(  # type: ignore[arg-type]
            events, self.today, collection_calendar_ids
        )

        self.assertEqual(len(result), 2)
        self.assertIn("🗑️", result)
        self.assertIn("♻️", result)

    def test_duplicate_icons_are_deduplicated(self):
        """Test duplicate icons from same calendar are deduplicated."""
        events = [
            {
                "id": "1",
                "title": "Garbage AM",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            },
            {
                "id": "2",
                "title": "Garbage PM",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            },
        ]
        collection_calendar_ids = ["calendar.waste_garbage"]

        result = get_collection_icons_for_day(  # type: ignore[arg-type]
            events, self.today, collection_calendar_ids
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "🗑️")

    def test_non_collection_calendars_ignored(self):
        """Test non-collection calendars are ignored."""
        events = [
            {
                "id": "1",
                "title": "Regular Event",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.personal",
                "calendarIcon": "●",
            },
            {
                "id": "2",
                "title": "Garbage",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            },
        ]
        collection_calendar_ids = ["calendar.waste_garbage"]

        result = get_collection_icons_for_day(  # type: ignore[arg-type]
            events, self.today, collection_calendar_ids
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "🗑️")

    def test_timed_collection_events_ignored(self):
        """Test timed (non-all-day) collection events are ignored."""
        events = [
            {
                "id": "1",
                "title": "Garbage",
                "start": datetime(2026, 1, 26, 8, 0),
                "end": datetime(2026, 1, 26, 9, 0),
                "allDay": False,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            }
        ]
        collection_calendar_ids = ["calendar.waste_garbage"]

        result = get_collection_icons_for_day(  # type: ignore[arg-type]
            events, self.today, collection_calendar_ids
        )

        self.assertEqual(len(result), 0)

    def test_collection_on_different_day_ignored(self):
        """Test collection events on different days are ignored."""
        events = [
            {
                "id": "1",
                "title": "Garbage",
                "start": datetime(2026, 1, 27, 0, 0),
                "end": datetime(2026, 1, 27, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            }
        ]
        collection_calendar_ids = ["calendar.waste_garbage"]

        result = get_collection_icons_for_day(  # type: ignore[arg-type]
            events, self.today, collection_calendar_ids
        )

        self.assertEqual(len(result), 0)

    def test_empty_collection_calendar_list(self):
        """Test with empty collection calendar list."""
        events = [
            {
                "id": "1",
                "title": "Garbage",
                "start": datetime(2026, 1, 26, 0, 0),
                "end": datetime(2026, 1, 26, 23, 59),
                "allDay": True,
                "calendarId": "calendar.waste_garbage",
                "calendarIcon": "🗑️",
            }
        ]

        result = get_collection_icons_for_day(events, self.today, [])  # type: ignore[arg-type]

        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
