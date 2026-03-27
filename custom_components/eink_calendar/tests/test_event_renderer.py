"""Unit tests for event_renderer module."""

from datetime import datetime

from renderer.event_renderer import (
    format_multi_day_time,
    sort_events_by_priority,
)


class TestFormatMultiDayTime:
    def test_all_day_event(self):
        event = {
            "start": datetime(2026, 1, 26, 0, 0),
            "end": datetime(2026, 1, 28, 23, 59),
            "allDay": True,
        }
        result = format_multi_day_time(event, starts_on_day=False, ends_on_day=False)
        assert result == ""

    def test_event_starts_on_day(self):
        event = {
            "start": datetime(2026, 1, 26, 14, 30),
            "end": datetime(2026, 1, 28, 16, 0),
            "allDay": False,
        }
        result = format_multi_day_time(event, starts_on_day=True, ends_on_day=False)
        assert result == "14:30 ▶"

    def test_event_ends_on_day(self):
        event = {
            "start": datetime(2026, 1, 24, 9, 0),
            "end": datetime(2026, 1, 26, 17, 30),
            "allDay": False,
        }
        result = format_multi_day_time(event, starts_on_day=False, ends_on_day=True)
        assert result == "◀ 17:30"

    def test_event_spans_day(self):
        event = {
            "start": datetime(2026, 1, 25, 9, 0),
            "end": datetime(2026, 1, 27, 17, 0),
            "allDay": False,
        }
        result = format_multi_day_time(event, starts_on_day=False, ends_on_day=False)
        assert result == "◀ ▶"

    def test_time_formatting_with_leading_zeros(self):
        event = {
            "start": datetime(2026, 1, 26, 9, 5),
            "end": datetime(2026, 1, 28, 16, 0),
            "allDay": False,
        }
        result = format_multi_day_time(event, starts_on_day=True, ends_on_day=False)
        assert result == "09:05 ▶"


class TestSortEventsByPriority:
    def test_all_day_events_come_first(self):
        events_for_day = [
            {
                "event": {"title": "Timed Event", "start": datetime(2026, 1, 26, 10, 0), "allDay": False},
                "startsOnDay": True, "endsOnDay": True,
            },
            {
                "event": {"title": "All-Day Event", "start": datetime(2026, 1, 26, 0, 0), "allDay": True},
                "startsOnDay": True, "endsOnDay": True,
            },
        ]
        result = sort_events_by_priority(events_for_day)
        assert result[0]["event"]["title"] == "All-Day Event"
        assert result[1]["event"]["title"] == "Timed Event"

    def test_timed_events_sorted_by_start_time(self):
        events_for_day = [
            {
                "event": {"title": "Afternoon", "start": datetime(2026, 1, 26, 15, 0), "allDay": False},
                "startsOnDay": True, "endsOnDay": True,
            },
            {
                "event": {"title": "Morning", "start": datetime(2026, 1, 26, 9, 0), "allDay": False},
                "startsOnDay": True, "endsOnDay": True,
            },
            {
                "event": {"title": "Lunch", "start": datetime(2026, 1, 26, 12, 0), "allDay": False},
                "startsOnDay": True, "endsOnDay": True,
            },
        ]
        result = sort_events_by_priority(events_for_day)
        assert result[0]["event"]["title"] == "Morning"
        assert result[1]["event"]["title"] == "Lunch"
        assert result[2]["event"]["title"] == "Afternoon"

    def test_all_day_then_timed(self):
        events_for_day = [
            {
                "event": {"title": "Afternoon", "start": datetime(2026, 1, 26, 15, 0), "allDay": False},
                "startsOnDay": True, "endsOnDay": True,
            },
            {
                "event": {"title": "Holiday", "start": datetime(2026, 1, 26, 0, 0), "allDay": True},
                "startsOnDay": True, "endsOnDay": True,
            },
            {
                "event": {"title": "Morning", "start": datetime(2026, 1, 26, 9, 0), "allDay": False},
                "startsOnDay": True, "endsOnDay": True,
            },
            {
                "event": {"title": "Birthday", "start": datetime(2026, 1, 26, 0, 0), "allDay": True},
                "startsOnDay": True, "endsOnDay": True,
            },
        ]
        result = sort_events_by_priority(events_for_day)
        assert result[0]["event"]["allDay"] is True
        assert result[1]["event"]["allDay"] is True
        assert result[2]["event"]["title"] == "Morning"
        assert result[3]["event"]["title"] == "Afternoon"

    def test_empty_list(self):
        assert sort_events_by_priority([]) == []

    def test_single_event(self):
        events_for_day = [
            {
                "event": {"title": "Single", "start": datetime(2026, 1, 26, 10, 0), "allDay": False},
                "startsOnDay": True, "endsOnDay": True,
            }
        ]
        result = sort_events_by_priority(events_for_day)
        assert len(result) == 1
        assert result[0]["event"]["title"] == "Single"
