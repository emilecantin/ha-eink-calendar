"""Unit tests for upcoming section event filtering — including 'important' events.

Events marked as important (with '!' prefix in title) should appear in the
upcoming section regardless of whether they are multi-day/all-day.
"""

from datetime import datetime, timedelta

from renderer.section_renderers.landscape_upcoming import filter_upcoming_events


TODAY = datetime(2026, 3, 27, 10, 0, 0)
WINDOW_END = (TODAY + timedelta(days=7)).replace(
    hour=0, minute=0, second=0, microsecond=0
)


def make_event(**kwargs):
    """Create a test event with defaults."""
    defaults = {
        "title": "Some Event",
        "start": WINDOW_END + timedelta(days=1),
        "end": WINDOW_END + timedelta(days=2),
        "allDay": False,
        "calendarId": "calendar.test",
        "calendarIcon": "mdi:calendar",
    }
    return {**defaults, **kwargs}


class TestUpcomingFilter:
    """Test the upcoming section event filter logic."""

    def test_allday_event_after_window_included(self):
        """All-day events beyond the 7-day window should appear (existing behavior)."""
        events = [make_event(
            title="Vacation",
            start=WINDOW_END + timedelta(days=2),
            end=WINDOW_END + timedelta(days=5),
            allDay=True,
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 1
        assert result[0]["title"] == "Vacation"

    def test_multiday_event_after_window_included(self):
        """Multi-day events beyond the 7-day window should appear (existing behavior)."""
        events = [make_event(
            title="Conference",
            start=WINDOW_END + timedelta(days=1),
            end=WINDOW_END + timedelta(days=3),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 1
        assert result[0]["title"] == "Conference"

    def test_normal_timed_event_excluded(self):
        """Normal single-day timed events should still be excluded."""
        events = [make_event(
            title="Regular Meeting",
            start=WINDOW_END + timedelta(days=1, hours=14),
            end=WINDOW_END + timedelta(days=1, hours=15),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 0

    def test_important_timed_event_included(self):
        """Events with '!' prefix should bypass the multi-day/all-day filter."""
        events = [make_event(
            title="! Doctor Appointment",
            start=WINDOW_END + timedelta(days=3, hours=10),
            end=WINDOW_END + timedelta(days=3, hours=11),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 1

    def test_important_prefix_stripped_from_title(self):
        """The '!' prefix should be stripped from the displayed title."""
        events = [make_event(
            title="! Doctor Appointment",
            start=WINDOW_END + timedelta(days=3, hours=10),
            end=WINDOW_END + timedelta(days=3, hours=11),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert result[0]["title"] == "Doctor Appointment"

    def test_important_prefix_with_no_space(self):
        """'!Title' (no space) should also work."""
        events = [make_event(
            title="!Urgent Task",
            start=WINDOW_END + timedelta(days=3, hours=10),
            end=WINDOW_END + timedelta(days=3, hours=11),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 1
        assert result[0]["title"] == "Urgent Task"

    def test_important_allday_event_still_included(self):
        """An important all-day event should still appear (it already qualified)."""
        events = [make_event(
            title="! Holiday",
            start=WINDOW_END + timedelta(days=2),
            end=WINDOW_END + timedelta(days=2, hours=23, minutes=59),
            allDay=True,
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 1
        assert result[0]["title"] == "Holiday"

    def test_important_flag_set_on_important_events(self):
        """Important events should have an 'important' flag set to True."""
        events = [make_event(
            title="! Dentist",
            start=WINDOW_END + timedelta(days=3, hours=10),
            end=WINDOW_END + timedelta(days=3, hours=11),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert result[0].get("important") is True

    def test_normal_events_no_important_flag(self):
        """Non-important events should not have the important flag."""
        events = [make_event(
            title="Vacation",
            start=WINDOW_END + timedelta(days=2),
            end=WINDOW_END + timedelta(days=5),
            allDay=True,
        )]
        result = filter_upcoming_events(events, TODAY)
        assert result[0].get("important") is not True

    def test_event_before_window_excluded(self):
        """Events before the window end should not appear (even if important)."""
        events = [make_event(
            title="! Tomorrow Meeting",
            start=TODAY + timedelta(days=1, hours=10),
            end=TODAY + timedelta(days=1, hours=11),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 0

    def test_max_12_events(self):
        """At most 12 events should be returned."""
        events = [
            make_event(
                title=f"! Event {i}",
                start=WINDOW_END + timedelta(days=i, hours=10),
                end=WINDOW_END + timedelta(days=i, hours=11),
            )
            for i in range(1, 20)
        ]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 12

    def test_exclamation_in_middle_not_treated_as_important(self):
        """An '!' in the middle of the title should NOT mark the event as important."""
        events = [make_event(
            title="Wow! Great event",
            start=WINDOW_END + timedelta(days=3, hours=10),
            end=WINDOW_END + timedelta(days=3, hours=11),
        )]
        result = filter_upcoming_events(events, TODAY)
        assert len(result) == 0
