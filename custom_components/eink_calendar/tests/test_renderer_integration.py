"""Integration tests for the complete renderer."""

from datetime import datetime
from io import BytesIO

from PIL import Image

from renderer.renderer import (
    _create_legend,
    _process_events,
    render_calendar,
    render_to_png,
)


class TestProcessEventsIntegration:
    def test_process_single_event(self):
        raw_events = [{
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
            "summary": "Test Event",
            "start": "2026-01-26T14:00:00",
            "end": "2026-01-26T15:00:00",
        }]
        result = _process_events(raw_events)
        assert len(result) == 1
        assert result[0]["title"] == "Test Event"
        assert result[0]["start"].hour == 14
        assert result[0]["allDay"] is False
        assert result[0]["calendarIcon"] == "mdi:calendar"
        assert result[0]["calendarId"] == "calendar.test"

    def test_process_all_day_event(self):
        raw_events = [{
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
            "summary": "All Day Event",
            "start": "2026-01-26",
            "end": "2026-01-27",  # exclusive
        }]
        result = _process_events(raw_events)
        assert len(result) == 1
        assert result[0]["allDay"] is True
        assert result[0]["end"].day == 26  # adjusted to inclusive

    def test_process_event_with_emoji_icon(self):
        raw_events = [{
            "calendar_id": "calendar.waste",
            "calendar_icon": "🗑️",
            "summary": "Garbage",
            "start": "2026-01-26",
            "end": "2026-01-27",
        }]
        result = _process_events(raw_events)
        assert result[0]["calendarIcon"] == "🗑️"

    def test_process_invalid_date_skipped(self):
        raw_events = [
            {"calendar_id": "cal", "calendar_icon": "mdi:calendar",
             "summary": "Invalid", "start": "invalid", "end": "invalid"},
            {"calendar_id": "cal", "calendar_icon": "mdi:calendar",
             "summary": "Valid", "start": "2026-01-26T14:00:00", "end": "2026-01-26T15:00:00"},
        ]
        result = _process_events(raw_events)
        assert len(result) == 1
        assert result[0]["title"] == "Valid"


class TestCreateLegend:
    def test_create_legend_from_events(self):
        calendar_events = [
            {"calendar_id": "calendar.personal", "calendar_icon": "mdi:calendar",
             "summary": "E1", "start": "2026-01-26T14:00:00", "end": "2026-01-26T15:00:00"},
            {"calendar_id": "calendar.work", "calendar_icon": "mdi:briefcase",
             "summary": "E2", "start": "2026-01-26T16:00:00", "end": "2026-01-26T17:00:00"},
        ]
        result = _create_legend(calendar_events)
        assert len(result) == 2
        names = [item["name"] for item in result]
        assert "Personal" in names
        assert "Work" in names

    def test_create_legend_deduplicates(self):
        calendar_events = [
            {"calendar_id": "calendar.personal", "calendar_icon": "mdi:calendar",
             "summary": "E1", "start": "2026-01-26T14:00:00", "end": "2026-01-26T15:00:00"},
            {"calendar_id": "calendar.personal", "calendar_icon": "mdi:calendar",
             "summary": "E2", "start": "2026-01-26T16:00:00", "end": "2026-01-26T17:00:00"},
        ]
        result = _create_legend(calendar_events)
        assert len(result) == 1
        assert result[0]["name"] == "Personal"

    def test_create_legend_uses_calendar_name(self):
        calendar_events = [
            {"calendar_id": "calendar.famille", "calendar_icon": "mdi:calendar",
             "calendar_name": "Famille", "summary": "E1",
             "start": "2026-01-26T14:00:00", "end": "2026-01-26T15:00:00"},
        ]
        result = _create_legend(calendar_events)
        assert result[0]["name"] == "Famille"


class TestRenderCalendar:
    def test_render_with_simple_event(self):
        calendar_events = [{
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
            "summary": "Test Meeting",
            "start": "2026-01-26T14:00:00",
            "end": "2026-01-26T15:00:00",
        }]
        now = datetime(2026, 1, 25, 10, 0, 0)
        result = render_calendar(calendar_events, [], None, now, {})

        assert result.black_layer_full is not None
        assert result.red_layer_full is not None
        assert result.etag is not None
        assert result.timestamp == now

        assert isinstance(result.get_black_top(), bytes)
        assert isinstance(result.get_black_bottom(), bytes)
        assert isinstance(result.get_red_top(), bytes)
        assert isinstance(result.get_red_bottom(), bytes)

    def test_render_to_png_produces_valid_image(self):
        calendar_events = [{
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
            "summary": "Test Meeting",
            "start": "2026-01-26T14:00:00",
            "end": "2026-01-26T15:00:00",
        }]
        now = datetime(2026, 1, 25, 10, 0, 0)
        png_data = render_to_png(calendar_events, [], None, now, {})

        assert isinstance(png_data, bytes)
        assert len(png_data) > 0

        img = Image.open(BytesIO(png_data))
        assert img.format == "PNG"
        assert img.size == (1304, 984)

    def test_render_with_weather(self):
        calendar_events = [{
            "calendar_id": "calendar.test",
            "calendar_icon": "mdi:calendar",
            "summary": "Meeting",
            "start": "2026-01-25T14:00:00",
            "end": "2026-01-25T15:00:00",
        }]
        weather_data = {
            "condition": "sunny",
            "temperature": 22,
            "forecast": [
                {"datetime": "2026-01-25T00:00:00", "condition": "sunny",
                 "temperature": 22, "templow": 15},
            ],
        }
        now = datetime(2026, 1, 25, 10, 0, 0)
        result = render_calendar(calendar_events, [], weather_data, now, {})
        assert result.etag is not None
