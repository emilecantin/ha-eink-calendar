"""Unit tests for event_filters module."""

from datetime import datetime, timedelta, timezone

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

    def test_utc_event_near_midnight_appears_on_correct_local_day(self):
        """Event at 23:00 UTC on Jan 25 is 18:00 EST on Jan 25 (same day).

        But event at 02:00 UTC on Jan 26 is 21:00 EST on Jan 25 (previous day).
        The filter should convert to local time, not just strip tzinfo.
        """
        utc_minus_5 = timezone(timedelta(hours=-5))
        day_jan25 = datetime(2026, 1, 25, 10, 0, tzinfo=utc_minus_5)

        events = [
            make_event(
                title="Late UTC event",
                start=datetime(2026, 1, 26, 2, 0, tzinfo=timezone.utc),  # 21:00 EST Jan 25
                end=datetime(2026, 1, 26, 3, 0, tzinfo=timezone.utc),    # 22:00 EST Jan 25
            ),
        ]
        result = get_events_for_day(events, day_jan25)
        # This event is on Jan 25 in local time (UTC-5), should be included
        assert len(result) == 1
        assert result[0]["startsOnDay"] is True
        assert result[0]["endsOnDay"] is True

    def test_utc_event_not_on_local_day_excluded(self):
        """Event at 03:00 UTC on Jan 26 is 22:00 EST on Jan 25.

        But event at 10:00 UTC on Jan 26 is 05:00 EST on Jan 26 — not Jan 25.
        """
        utc_minus_5 = timezone(timedelta(hours=-5))
        day_jan25 = datetime(2026, 1, 25, 10, 0, tzinfo=utc_minus_5)

        events = [
            make_event(
                title="Next day in local time",
                start=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),  # 05:00 EST Jan 26
                end=datetime(2026, 1, 26, 11, 0, tzinfo=timezone.utc),    # 06:00 EST Jan 26
            ),
        ]
        result = get_events_for_day(events, day_jan25)
        assert len(result) == 0

    def test_timezone_conversion_spans_day_boundary(self):
        """Multi-day event spanning across timezone conversion boundary."""
        utc_plus_9 = timezone(timedelta(hours=9))
        # In UTC+9, Jan 26 00:00 is Jan 25 15:00 UTC
        day_jan26 = datetime(2026, 1, 26, 10, 0, tzinfo=utc_plus_9)

        events = [
            make_event(
                title="Spans in UTC+9",
                start=datetime(2026, 1, 25, 20, 0, tzinfo=timezone.utc),  # Jan 26 05:00 UTC+9
                end=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),    # Jan 26 19:00 UTC+9
            ),
        ]
        result = get_events_for_day(events, day_jan26)
        assert len(result) == 1
        assert result[0]["startsOnDay"] is True
        assert result[0]["endsOnDay"] is True

    def test_naive_day_with_aware_events_converts_to_event_tz(self):
        """When day is naive but events are aware, convert events for comparison."""
        utc_minus_5 = timezone(timedelta(hours=-5))
        naive_day = datetime(2026, 1, 25, 10, 0)  # naive

        events = [
            make_event(
                title="Late UTC",
                start=datetime(2026, 1, 26, 2, 0, tzinfo=utc_minus_5),  # Jan 26 in UTC-5
                end=datetime(2026, 1, 26, 3, 0, tzinfo=utc_minus_5),
            ),
        ]
        # Event is on Jan 26 in its own timezone, not Jan 25
        result = get_events_for_day(events, naive_day)
        assert len(result) == 0

    def test_event_missing_start_or_end_skipped(self):
        events = [
            make_event(start=None, end=datetime(2026, 1, 26, 15, 0)),
            make_event(start=datetime(2026, 1, 26, 14, 0), end=None),
        ]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 0

    def test_timed_event_ending_at_midnight_excluded_from_next_day(self):
        """A timed event from 22:00–00:00 should NOT appear on the next day.

        The event ends exactly at midnight (00:00:00) on Jan 27, which means
        it does not actually occupy any time on Jan 27.
        """
        jan27 = datetime(2026, 1, 27, 10, 0, 0)
        events = [make_event(
            title="Late Night Meeting",
            start=datetime(2026, 1, 26, 22, 0),
            end=datetime(2026, 1, 27, 0, 0),  # midnight = start of Jan 27
        )]
        result = get_events_for_day(events, jan27)
        assert len(result) == 0, (
            "Timed event ending at midnight should not appear on the next day"
        )

    def test_timed_event_ending_at_midnight_included_on_start_day(self):
        """A timed event from 22:00–00:00 DOES appear on its start day."""
        events = [make_event(
            title="Late Night Meeting",
            start=datetime(2026, 1, 26, 22, 0),
            end=datetime(2026, 1, 27, 0, 0),
        )]
        result = get_events_for_day(events, TODAY)
        assert len(result) == 1
        assert result[0]["event"]["title"] == "Late Night Meeting"
        assert result[0]["startsOnDay"] is True

    def test_allday_multiday_event_spans_correctly(self):
        """An all-day event spanning multiple days still appears on middle days.

        All-day events use >= for the spans_day check (inclusive end),
        while timed events use > (exclusive at midnight boundary).
        """
        # All-day event from Jan 25 to Jan 27 (inclusive, already adjusted)
        events = [make_event(
            title="Multi-day Holiday",
            start=datetime(2026, 1, 25),
            end=datetime(2026, 1, 27),
            allDay=True,
        )]
        # Should appear on Jan 26 (middle day)
        result = get_events_for_day(events, TODAY)
        assert len(result) == 1
        assert result[0]["startsOnDay"] is False
        assert result[0]["endsOnDay"] is False


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
