"""Resolution of the check-in interval commanded to the device.

Home Assistant tells the ESP32 how long to sleep on every check-in — as the
``X-Refresh-Interval`` header on a 304, or the ``refresh_interval`` field on a
200. This module decides what that value should be.

The policy is deliberately small: a base interval, multiplied during a
configurable quiet-hours window. The base comes from the Number entity (so
automations can drive it); the window and multiplier come from config options.

Kept free of Home Assistant imports so it can be unit-tested in isolation,
in the same spirit as ``device_diagnostics.py``.
"""

from __future__ import annotations

import math
from datetime import datetime, time

# The wire format is integer minutes, and the firmware treats a non-positive
# value as "absent" (see FetchResponse.refresh_interval), so 1 is the floor.
MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 1440  # 24h — matches the options-flow NumberSelector


def parse_time_option(value: str | time | None) -> time | None:
    """Coerce a config-option value into a ``time``, or ``None``.

    Home Assistant's TimeSelector stores "HH:MM:SS" strings, but an option
    may also arrive already parsed, blank, or malformed after a hand-edit of
    the config entry. Anything unusable resolves to ``None``, which disables
    quiet hours — a bad option must never break a device check-in.
    """
    if value is None or isinstance(value, time):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def in_quiet_hours(
    now: datetime, start: time | None, end: time | None
) -> bool:
    """Is ``now`` inside the quiet-hours window?

    ``start`` is inclusive and ``end`` exclusive, so adjacent windows don't
    overlap on the boundary minute. A window whose end is earlier than its
    start wraps around midnight (23:00->07:00 being the expected shape).

    An absent bound disables the window entirely. So does ``start == end``:
    a zero-length window is the safer reading of an ambiguous config than a
    silent 24-hour slowdown.
    """
    if start is None or end is None or start == end:
        return False

    current = now.time()
    if start < end:
        return start <= current < end
    return current >= start or current < end


def resolve_interval(
    now: datetime,
    base_minutes: float,
    quiet_start: time | None,
    quiet_end: time | None,
    quiet_multiplier: float,
) -> int:
    """Minutes the device should sleep before its next check-in.

    ``now`` must already be in local time — quiet hours are a wall-clock
    notion, so the caller resolves the timezone (and therefore DST).

    The multiplier is floored at 1: a quiet period may only slow check-ins
    down, never speed them up. A misconfigured value can't quietly turn into
    a battery-draining fast poll overnight.
    """
    interval = base_minutes
    if in_quiet_hours(now, quiet_start, quiet_end):
        interval = base_minutes * max(quiet_multiplier, 1)

    # Half-up, not round()'s banker's rounding: round(22.5) == 22 is a
    # surprise, and rounding a sleep interval up is the battery-safe direction.
    whole = math.floor(interval + 0.5)
    return max(MIN_INTERVAL_MINUTES, min(MAX_INTERVAL_MINUTES, whole))
