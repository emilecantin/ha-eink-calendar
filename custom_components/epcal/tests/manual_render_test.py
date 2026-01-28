#!/usr/bin/env python3
"""Manual test script to verify rendering with sample data.

This script can be run outside of Home Assistant to test the rendering pipeline
with realistic sample data.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from ..renderer.types import CalendarEvent, RenderOptions, WeatherData

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ..renderer.renderer import render_to_png


def create_sample_data():
    """Create sample calendar and weather data for testing."""
    now = datetime(2026, 1, 25, 20, 0, 0)  # Sunday evening, Jan 25, 2026

    # Sample calendar events
    calendar_events = cast(
        list[CalendarEvent],
        [
            # Event tomorrow (Monday) - this should appear in the week section
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Team Meeting",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:30:00",
                "description": "Weekly team sync",
                "location": "Conference Room A",
            },
            # Event on Tuesday
            {
                "calendar_id": "calendar.work",
                "calendar_icon": "mdi:briefcase",
                "summary": "Client Presentation",
                "start": "2026-01-27T10:00:00",
                "end": "2026-01-27T11:00:00",
                "description": "",
                "location": "",
            },
            # All-day event on Wednesday
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Conference Day 1",
                "start": "2026-01-28",
                "end": "2026-01-28",
                "description": "",
                "location": "",
            },
            # Multi-day event starting Thursday
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Vacation",
                "start": "2026-01-29T00:00:00",
                "end": "2026-01-31T23:59:59",
                "description": "",
                "location": "",
            },
            # Event next week (for upcoming section)
            {
                "calendar_id": "calendar.work",
                "calendar_icon": "mdi:briefcase",
                "summary": "Board Meeting",
                "start": "2026-02-02",
                "end": "2026-02-02",
                "description": "",
                "location": "",
            },
        ],
    )

    # Sample waste collection events
    waste_events = cast(
        list[CalendarEvent],
        [
            {
                "calendar_id": "calendar.waste_garbage",
                "calendar_icon": "🗑️",
                "summary": "Garbage Collection",
                "start": "2026-01-27",
                "end": "2026-01-27",
                "description": "",
                "location": "",
            },
            {
                "calendar_id": "calendar.waste_recycling",
                "calendar_icon": "♻️",
                "summary": "Recycling Collection",
                "start": "2026-01-30",
                "end": "2026-01-30",
                "description": "",
                "location": "",
            },
        ],
    )

    # Sample weather data
    weather_data = cast(
        WeatherData,
        {
            "condition": "sunny",
            "temperature": 20,
            "forecast": [
                {
                    "datetime": "2026-01-25T00:00:00",
                    "condition": "sunny",
                    "temperature": 22,
                    "templow": 15,
                },
                {
                    "datetime": "2026-01-26T00:00:00",
                    "condition": "partlycloudy",
                    "temperature": 20,
                    "templow": 14,
                },
                {
                    "datetime": "2026-01-27T00:00:00",
                    "condition": "cloudy",
                    "temperature": 18,
                    "templow": 12,
                },
                {
                    "datetime": "2026-01-28T00:00:00",
                    "condition": "rainy",
                    "temperature": 16,
                    "templow": 11,
                },
                {
                    "datetime": "2026-01-29T00:00:00",
                    "condition": "rainy",
                    "temperature": 15,
                    "templow": 10,
                },
                {
                    "datetime": "2026-01-30T00:00:00",
                    "condition": "cloudy",
                    "temperature": 17,
                    "templow": 11,
                },
                {
                    "datetime": "2026-01-31T00:00:00",
                    "condition": "sunny",
                    "temperature": 19,
                    "templow": 13,
                },
            ],
        },
    )

    options = cast(
        RenderOptions,
        {
            "waste_calendars": ["calendar.waste_garbage", "calendar.waste_recycling"],
        },
    )

    return calendar_events, waste_events, weather_data, now, options


def main():
    """Run the test."""
    print("EPCAL Rendering Manual Test")
    print("=" * 60)

    # Create sample data
    calendar_events, waste_events, weather_data, now, options = create_sample_data()

    print(f"\nTest Date: {now.strftime('%A, %B %d, %Y at %H:%M')}")
    print(f"Calendar Events: {len(calendar_events)}")
    print(f"Waste Events: {len(waste_events)}")
    print(f"Weather Forecasts: {len(weather_data['forecast'])}")

    print("\nCalendar Events:")
    for event in calendar_events:
        start = event["start"]  # type: ignore[typeddict-item]
        print(f"  - {event['summary']}: {start}")  # type: ignore[typeddict-item]

    # Render to PNG
    print("\nRendering calendar to PNG...")
    try:
        png_data = render_to_png(
            calendar_events, waste_events, weather_data, now, options
        )

        # Save to file
        output_file = Path(__file__).parent / "test_render.png"
        with open(output_file, "wb") as f:
            f.write(png_data)

        print(f"✓ Successfully rendered {len(png_data):,} bytes")
        print(f"✓ Saved to: {output_file}")
        print("\nYou can now open test_render.png to view the rendered calendar.")
        print("The event 'Team Meeting' should appear in the first column (Monday).")

    except Exception as e:
        print(f"✗ Error during rendering: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
