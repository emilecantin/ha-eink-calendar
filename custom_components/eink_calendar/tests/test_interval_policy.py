"""Tests for the check-in interval resolution policy."""

from datetime import datetime, time

import pytest

from custom_components.eink_calendar.interval_policy import (
    MAX_INTERVAL_MINUTES,
    MIN_INTERVAL_MINUTES,
    in_quiet_hours,
    parse_time_option,
    resolve_interval,
)


def at(hour: int, minute: int = 0) -> datetime:
    """A local datetime on an arbitrary fixed day."""
    return datetime(2026, 8, 30, hour, minute)


class TestQuietHoursWindow:
    """Window membership, including the wrapping case."""

    @pytest.mark.parametrize(
        "now,expected",
        [
            (at(23, 0), True),   # start is inclusive
            (at(23, 30), True),
            (at(2, 0), True),    # after midnight, still inside
            (at(6, 59), True),
            (at(7, 0), False),   # end is exclusive
            (at(12, 0), False),
            (at(22, 59), False),
        ],
    )
    def test_wrapping_window(self, now, expected):
        """A 23:00->07:00 window spans midnight."""
        assert in_quiet_hours(now, time(23, 0), time(7, 0)) is expected

    @pytest.mark.parametrize(
        "now,expected",
        [
            (at(12, 59), False),
            (at(13, 0), True),
            (at(13, 30), True),
            (at(14, 0), False),
            (at(2, 0), False),
        ],
    )
    def test_non_wrapping_window(self, now, expected):
        """A 13:00->14:00 window sits inside a single day."""
        assert in_quiet_hours(now, time(13, 0), time(14, 0)) is expected

    def test_equal_bounds_is_disabled_not_all_day(self):
        """start == end means zero-length, never a silent 24h slowdown."""
        for hour in (0, 6, 12, 23):
            assert in_quiet_hours(at(hour), time(9, 0), time(9, 0)) is False

    def test_missing_bounds_disable_the_window(self):
        assert in_quiet_hours(at(3), None, time(7, 0)) is False
        assert in_quiet_hours(at(3), time(23, 0), None) is False
        assert in_quiet_hours(at(3), None, None) is False


class TestResolveInterval:
    """Base interval times the quiet-hours multiplier."""

    def test_outside_quiet_hours_returns_base(self):
        assert resolve_interval(at(12), 15, time(23, 0), time(7, 0), 8) == 15

    def test_inside_quiet_hours_applies_multiplier(self):
        assert resolve_interval(at(2), 15, time(23, 0), time(7, 0), 8) == 120

    def test_multiplier_of_one_is_a_no_op(self):
        assert resolve_interval(at(2), 15, time(23, 0), time(7, 0), 1) == 15

    def test_disabled_quiet_hours_returns_base(self):
        assert resolve_interval(at(2), 15, None, None, 8) == 15

    def test_fractional_multiplier_rounds_to_whole_minutes(self):
        """The wire format is integer minutes, so the result must be an int."""
        result = resolve_interval(at(2), 15, time(23, 0), time(7, 0), 1.5)
        assert result == 23  # 22.5 rounds to 23
        assert isinstance(result, int)


class TestClamping:
    """The resolved value must always be a legal wire value."""

    def test_result_never_exceeds_max(self):
        assert resolve_interval(at(2), 1000, time(23, 0), time(7, 0), 8) == MAX_INTERVAL_MINUTES

    def test_result_never_drops_below_min(self):
        assert resolve_interval(at(12), 0, None, None, 1) == MIN_INTERVAL_MINUTES

    def test_negative_base_is_clamped_not_propagated(self):
        assert resolve_interval(at(12), -5, None, None, 1) == MIN_INTERVAL_MINUTES

    def test_multiplier_below_one_cannot_shorten_the_interval(self):
        """A quiet period must never make the device check in *more* often."""
        assert resolve_interval(at(2), 15, time(23, 0), time(7, 0), 0.1) == 15


class TestParseTimeOption:
    """HA's TimeSelector hands back strings; the policy needs `time` objects."""

    def test_parses_hh_mm_ss(self):
        assert parse_time_option("23:00:00") == time(23, 0)

    def test_parses_hh_mm(self):
        assert parse_time_option("07:30") == time(7, 30)

    def test_none_passes_through(self):
        assert parse_time_option(None) is None

    def test_empty_string_is_none(self):
        assert parse_time_option("") is None
        assert parse_time_option("   ") is None

    def test_time_object_passes_through(self):
        assert parse_time_option(time(6, 15)) == time(6, 15)

    @pytest.mark.parametrize("bad", ["not a time", "25:00", "12:60", "12", "::"])
    def test_malformed_input_is_none_not_an_exception(self, bad):
        """A bad option must disable quiet hours, never break the check-in."""
        assert parse_time_option(bad) is None
