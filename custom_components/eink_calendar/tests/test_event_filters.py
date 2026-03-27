"""Unit tests for event_filters module."""

from datetime import datetime, timezone

from renderer.event_filters import get_collection_icons_for_day, get_events_for_day


def make_event(**kwargs):
    """Create a test event with defaults."""
    defaults = {
        "title": "",
        "start": datetime(2026, 1, 1),
        "end": datetime(2026, 1, 1),
        "allDay": False,
        "calendarId": "calendar.test",
        "calendarIcon": "mdi:calendar",
    }
    return {**defaults, **kwargs}


TODAY = datetime(2026, 1, 26, 10, 0, 0)


# --- get_events_for_day ---


class TestGetEventsForDay:
    def test_single_day_event(self):
        events = [make_event(
            title="Meeting",
            start=datetime(2026, 1, 26, 14, 0),
            end=datetime(2026, 1, 26, 15, 0),
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 1
        assert result[0]["event"]["title"] == "Meeting"
        assert result[0]["startsOnDay"] is True
        assert result[0]["endsOnDay"] is True

    def test_all_day_event(self):
        events = [make_event(
            title="Holiday",
            start=datetime(2026, 1, 26),
            end=datetime(2026, 1, 26, 23, 59),
            allDay=True,
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 1
        assert result[0]["startsOnDay"] is True

    def test_multi_day_starts_on_day(self):
        events = [make_event(
            start=datetime(2026, 1, 26, 9, 0),
            end=datetime(2026, 1, 28, 17, 0),
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 1
        assert result[0]["startsOnDay"] is True
        assert result[0]["endsOnDay"] is False

    def test_multi_day_ends_on_day(self):
        events = [make_event(
            start=datetime(2026, 1, 24, 9, 0),
            end=datetime(2026, 1, 26, 17, 0),
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 1
        assert result[0]["startsOnDay"] is False
        assert result[0]["endsOnDay"] is True

    def test_multi_day_spans_day(self):
        events = [make_event(
            start=datetime(2026, 1, 25, 9, 0),
            end=datetime(2026, 1, 27, 17, 0),
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 1
        assert result[0]["startsOnDay"] is False
        assert result[0]["endsOnDay"] is False

    def test_event_on_different_day_excluded(self):
        events = [make_event(
            start=datetime(2026, 1, 27, 14, 0),
            end=datetime(2026, 1, 27, 15, 0),
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 0

    def test_past_event_excluded(self):
        events = [make_event(
            start=datetime(2026, 1, 24, 14, 0),
            end=datetime(2026, 1, 25, 15, 0),
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 0

    def test_multiple_events(self):
        events = [
            make_event(start=datetime(2026, 1, 26, 9, 0), end=datetime(2026, 1, 26, 10, 0)),
            make_event(start=datetime(2026, 1, 26, 12, 0), end=datetime(2026, 1, 26, 13, 0)),
            make_event(start=datetime(2026, 1, 26, 15, 0), end=datetime(2026, 1, 26, 16, 0)),
        ]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 3

    def test_mixed_naive_aware_datetimes(self):
        """Mixing naive all-day and aware timed events should not crash."""
        aware_today = datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)
        events = [
            make_event(
                title="All Day",
                start=datetime(2026, 1, 26),  # naive
                end=datetime(2026, 1, 26, 23, 59),
                allDay=True,
            ),
            make_event(
                title="Timed",
                start=datetime(2026, 1, 26, 14, 0, tzinfo=timezone.utc),  # aware
                end=datetime(2026, 1, 26, 15, 0, tzinfo=timezone.utc),
            ),
        ]
        result = get_events_for_day(events, aware_today)
        assert len(result) == 2

    def test_event_missing_start_or_end_skipped(self):
        events = [
            make_event(start=None, end=datetime(2026, 1, 26, 15, 0)),
            make_event(start=datetime(2026, 1, 26, 14, 0), end=None),
        ]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 0


# --- get_collection_icons_for_day ---


class TestGetCollectionIconsForDay:
    def test_waste_event_on_day(self):
        events = [make_event(
            start=datetime(2026, 1, 26),
            end=datetime(2026, 1, 26, 23, 59),
            allDay=True,
            calendarIcon="mdi:trash-can",
        )]
        result = get_collection_icons_for_day(events, TODAY)
        assert result == ["mdi:trash-can"]

    def test_multiple_types(self):
        events = [
            make_event(start=datetime(2026, 1, 26), end=datetime(2026, 1, 26, 23, 59),
                       allDay=True, calendarIcon="mdi:trash-can"),
            make_event(start=datetime(2026, 1, 26), end=datetime(2026, 1, 26, 23, 59),
                       allDay=True, calendarIcon="mdi:recycle"),
        ]
        result = get_collection_icons_for_day(events, TODAY)
        assert len(result) == 2
        assert "mdi:trash-can" in result
        assert "mdi:recycle" in result

    def test_duplicate_icons_deduplicated(self):
        events = [
            make_event(start=datetime(2026, 1, 26), end=datetime(2026, 1, 26, 23, 59),
                       allDay=True, calendarIcon="mdi:trash-can"),
            make_event(start=datetime(2026, 1, 26), end=datetime(2026, 1, 26, 23, 59),
                       allDay=True, calendarIcon="mdi:trash-can"),
        ]
        result = get_collection_icons_for_day(events, TODAY)
        assert len(result) == 1

    def test_timed_events_ignored(self):
        events = [make_event(
            start=datetime(2026, 1, 26, 8, 0),
            end=datetime(2026, 1, 26, 9, 0),
            allDay=False,
            calendarIcon="mdi:trash-can",
        )]
        result = get_collection_icons_for_day(events, TODAY)
        assert len(result) == 0

    def test_different_day_ignored(self):
        events = [make_event(
            start=datetime(2026, 1, 27),
            end=datetime(2026, 1, 27, 23, 59),
            allDay=True,
            calendarIcon="mdi:trash-can",
        )]
        result = get_collection_icons_for_day(events, TODAY)
        assert len(result) == 0

    def test_empty_list(self):
        result = get_collection_icons_for_day([], TODAY)
        assert result == []
