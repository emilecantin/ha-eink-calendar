"""Unit tests for renderer._process_events and related date handling."""

from datetime import datetime, timezone

from renderer.renderer import _process_events


class TestProcessEvents:
    def test_timed_event(self):
        events = [{
            "summary": "Meeting",
            "start": "2026-01-26T14:00:00-05:00",
            "end": "2026-01-26T15:00:00-05:00",
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
        }]
        result = _process_events(events)
        assert len(result) == 1
        assert result[0]["title"] == "Meeting"
        assert result[0]["allDay"] is False
        assert result[0]["start"].hour == 14

    def test_all_day_event_exclusive_end_date(self):
        """All-day events have exclusive end dates per iCal — subtract 1 day."""
        events = [{
            "summary": "Holiday",
            "start": "2026-01-26",
            "end": "2026-01-27",  # exclusive = event is only on Jan 26
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
        }]
        result = _process_events(events)
        assert len(result) == 1
        assert result[0]["allDay"] is True
        assert result[0]["start"].date().day == 26
        assert result[0]["end"].date().day == 26  # inclusive

    def test_multi_day_all_day_event(self):
        """Multi-day all-day event end date adjusted."""
        events = [{
            "summary": "Conference",
            "start": "2026-01-26",
            "end": "2026-01-29",  # exclusive = Jan 26-28
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
        }]
        result = _process_events(events)
        assert result[0]["start"].date().day == 26
        assert result[0]["end"].date().day == 28

    def test_missing_start_or_end_skipped(self):
        events = [
            {"summary": "No end", "start": "2026-01-26T10:00:00", "end": None,
             "calendar_id": "cal", "calendar_icon": "mdi:calendar"},
            {"summary": "No start", "start": None, "end": "2026-01-26T11:00:00",
             "calendar_id": "cal", "calendar_icon": "mdi:calendar"},
        ]
        result = _process_events(events)
        assert len(result) == 0

    def test_calendar_icon_preserved(self):
        events = [{
            "summary": "Test",
            "start": "2026-01-26T10:00:00",
            "end": "2026-01-26T11:00:00",
            "calendar_id": "calendar.famille",
            "calendar_icon": "mdi:account-group",
        }]
        result = _process_events(events)
        assert result[0]["calendarIcon"] == "mdi:account-group"
        assert result[0]["calendarId"] == "calendar.famille"

    def test_calendar_name_preserved(self):
        events = [{
            "summary": "Test",
            "start": "2026-01-26T10:00:00",
            "end": "2026-01-26T11:00:00",
            "calendar_id": "calendar.famille",
            "calendar_icon": "mdi:calendar",
            "calendar_name": "Famille",
        }]
        result = _process_events(events)
        assert result[0].get("calendarName") == "Famille"

    def test_datetime_objects_passed_through(self):
        """Events with datetime objects (not strings) are handled."""
        events = [{
            "summary": "Test",
            "start": datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2026, 1, 26, 11, 0, tzinfo=timezone.utc),
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
        }]
        result = _process_events(events)
        assert len(result) == 1
        assert result[0]["start"].hour == 10

    def test_sorting_mixed_naive_aware_no_crash(self):
        """Mixing naive all-day and aware timed events should not crash when sorted."""
        events = [
            {
                "summary": "Timed",
                "start": "2026-01-26T14:00:00-05:00",
                "end": "2026-01-26T15:00:00-05:00",
                "calendar_id": "cal", "calendar_icon": "mdi:calendar",
            },
            {
                "summary": "All Day",
                "start": "2026-01-26",
                "end": "2026-01-27",
                "calendar_id": "cal", "calendar_icon": "mdi:calendar",
            },
        ]
        result = _process_events(events)
        assert len(result) == 2
        # Verify we can sort by date without crash
        result.sort(key=lambda e: e["start"].date())
