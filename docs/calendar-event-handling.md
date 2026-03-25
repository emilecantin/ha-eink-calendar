# Calendar Event Handling

## All-day event end dates (iCal exclusive end date rule)

Home Assistant's calendar API follows the iCal/RFC 5545 specification where
**all-day event end dates are EXCLUSIVE** — the end date is the day AFTER the
event actually ends.

### Examples from HA's `calendar.get_events` response

| Event description          | `start`        | `end`          | Actual last day |
|----------------------------|----------------|----------------|-----------------|
| Single day, March 25       | `"2025-03-25"` | `"2025-03-26"` | March 25        |
| Multi-day, March 25–27     | `"2025-03-25"` | `"2025-03-28"` | March 27        |
| Single day, December 31    | `"2025-12-31"` | `"2026-01-01"` | December 31     |

### The fix

Subtract 1 day from the end date of **ALL** all-day events, including
single-day ones. This converts the exclusive end date to an inclusive one.

### Where the fix is applied

The adjustment happens **once**, at the boundary between raw HA data and our
rendering pipeline:

- **Python (custom component)**: `renderer.py:_process_events()` — subtracts
  `timedelta(days=1)` from `end` when `all_day` is true.
- **Node.js (reference server)**: `index.ts` (lines 492–496) — subtracts
  `24 * 60 * 60 * 1000` ms from the end date.

All downstream code (`event_filters.py`, section renderers) receives the
corrected inclusive end date and **must not re-apply** this adjustment.

### How to detect all-day events

All-day events are returned by HA with date-only strings (no `T` time
component):

```
start: "2025-03-25"       ← all-day (no "T")
start: "2025-03-25T09:00" ← timed event (has "T")
```

In `_process_events()`, this is detected with `"T" not in start_str`.

### Why this keeps coming back

This is a subtle bug because:

1. The raw data from HA looks reasonable — `end: "2025-03-26"` for a March 25
   event isn't obviously wrong at first glance.
2. Single-day events are the most common case and the off-by-one makes them
   show on two days, which is easy to mistake for a multi-day event rendering
   issue.
3. The fix (subtract 1 day) feels wrong for single-day events if you don't
   know about the exclusive end date convention.

### Reference

- [RFC 5545 Section 3.6.1](https://datatracker.ietf.org/doc/html/rfc5545#section-3.6.1) — VEVENT definition
- [RFC 5545 Section 3.8.2.2](https://datatracker.ietf.org/doc/html/rfc5545#section-3.8.2.2) — DTEND property
  ("the 'DTEND' property for a 'VEVENT' calendar component [...] is
  non-inclusive")
