"""Visual regression tests - compare Python rendering with TypeScript reference.

These tests help identify visual differences between the Python and TypeScript implementations.
"""

import unittest
from datetime import datetime
from pathlib import Path

from PIL import Image

from ..renderer.renderer import render_to_png


class TestVisualRegression(unittest.TestCase):
    """Visual regression tests comparing Python output with TypeScript reference."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_dir = Path(__file__).parent / "visual_output"
        self.output_dir.mkdir(exist_ok=True)

        # Reference date: Sunday Jan 25, 2026 at 8pm
        self.now = datetime(2026, 1, 25, 20, 0, 0)

    def _create_sample_calendar_events(self):
        """Create comprehensive sample events covering all edge cases."""
        return [
            # Single-day event tomorrow morning
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Team Meeting",
                "start": "2026-01-26T09:00:00",
                "end": "2026-01-26T10:30:00",
                "description": "",
                "location": "Conference Room A",
            },
            # Single-day event tomorrow afternoon
            {
                "calendar_id": "calendar.work",
                "calendar_icon": "mdi:briefcase",
                "summary": "Client Presentation",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
                "description": "",
                "location": "",
            },
            # All-day event on Tuesday
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Company Holiday",
                "start": "2026-01-27",
                "end": "2026-01-27",
                "description": "",
                "location": "",
            },
            # Multi-day event Wed-Fri
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Tech Conference",
                "start": "2026-01-28T09:00:00",
                "end": "2026-01-30T17:00:00",
                "description": "",
                "location": "Convention Center",
            },
            # Weekend event (Saturday)
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Weekend Workshop",
                "start": "2026-01-31T10:00:00",
                "end": "2026-01-31T16:00:00",
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
            # Long title event (test wrapping)
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Very Long Event Title That Should Wrap Across Multiple Lines To Test Text Wrapping",
                "start": "2026-01-29T11:00:00",
                "end": "2026-01-29T12:00:00",
                "description": "",
                "location": "",
            },
        ]

    def _create_sample_waste_events(self):
        """Create waste collection events."""
        return [
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
        ]

    def _create_sample_weather(self):
        """Create sample weather data."""
        return {
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
        }

    def test_full_calendar_render(self):
        """Test complete calendar render with all features."""
        calendar_events = self._create_sample_calendar_events()
        waste_events = self._create_sample_waste_events()
        weather = self._create_sample_weather()
        options = {
            "waste_calendars": ["calendar.waste_garbage", "calendar.waste_recycling"],
        }

        # Render
        png_data = render_to_png(
            calendar_events, waste_events, weather, self.now, options
        )

        # Save output
        output_path = self.output_dir / "full_calendar.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"\n✓ Full calendar render saved to: {output_path}")
        print(f"  Size: {len(png_data):,} bytes")

        # Basic validation
        img = Image.open(output_path)
        self.assertEqual(img.size, (1304, 984))  # Landscape size
        self.assertEqual(img.format, "PNG")

    def test_today_section_with_events(self):
        """Test Today section rendering with various event types."""
        # Events for today (Sunday Jan 25)
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Morning Event",
                "start": "2026-01-25T09:00:00",
                "end": "2026-01-25T10:00:00",
                "description": "",
                "location": "",
            },
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "All-Day Event Today",
                "start": "2026-01-25",
                "end": "2026-01-25",
                "description": "",
                "location": "",
            },
            {
                "calendar_id": "calendar.work",
                "calendar_icon": "mdi:briefcase",
                "summary": "Multi-Day Starting Today",
                "start": "2026-01-25T14:00:00",
                "end": "2026-01-27T16:00:00",
                "description": "",
                "location": "",
            },
        ]

        png_data = render_to_png(calendar_events, [], None, self.now, {})
        output_path = self.output_dir / "today_section.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Today section render saved to: {output_path}")

    def test_week_section_with_all_day_events(self):
        """Test Week section with all-day events."""
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "All-Day Monday",
                "start": "2026-01-26",
                "end": "2026-01-26",
                "description": "",
                "location": "",
            },
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "All-Day Tuesday",
                "start": "2026-01-27",
                "end": "2026-01-27",
                "description": "",
                "location": "",
            },
        ]

        png_data = render_to_png(calendar_events, [], None, self.now, {})
        output_path = self.output_dir / "week_all_day_events.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Week all-day events render saved to: {output_path}")

    def test_week_section_with_multi_day_events(self):
        """Test Week section with multi-day events."""
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Multi-Day Event",
                "start": "2026-01-27T09:00:00",
                "end": "2026-01-29T17:00:00",
                "description": "",
                "location": "",
            },
        ]

        png_data = render_to_png(calendar_events, [], None, self.now, {})
        output_path = self.output_dir / "week_multi_day_event.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Week multi-day event render saved to: {output_path}")

    def test_weekend_highlighting(self):
        """Test weekend day highlighting (red background)."""
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Saturday Event",
                "start": "2026-01-31T10:00:00",
                "end": "2026-01-31T12:00:00",
                "description": "",
                "location": "",
            },
        ]

        png_data = render_to_png(calendar_events, [], None, self.now, {})
        output_path = self.output_dir / "weekend_highlighting.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Weekend highlighting render saved to: {output_path}")

    def test_waste_collection_icons(self):
        """Test waste collection icon positioning."""
        waste_events = self._create_sample_waste_events()
        options = {
            "waste_calendars": ["calendar.waste_garbage", "calendar.waste_recycling"],
        }

        png_data = render_to_png([], waste_events, None, self.now, options)
        output_path = self.output_dir / "waste_collection_icons.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Waste collection icons render saved to: {output_path}")

    def test_weather_display(self):
        """Test weather icon and temperature display."""
        weather = self._create_sample_weather()

        png_data = render_to_png([], [], weather, self.now, {})
        output_path = self.output_dir / "weather_display.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Weather display render saved to: {output_path}")

    def test_text_wrapping(self):
        """Test long event title wrapping."""
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "This Is A Very Long Event Title That Should Definitely Wrap Across Multiple Lines To Test The Text Wrapping Functionality",
                "start": "2026-01-26T10:00:00",
                "end": "2026-01-26T11:00:00",
                "description": "",
                "location": "",
            },
        ]

        png_data = render_to_png(calendar_events, [], None, self.now, {})
        output_path = self.output_dir / "text_wrapping.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Text wrapping render saved to: {output_path}")

    def test_overflow_indicator(self):
        """Test +X more indicator when too many events."""
        # Create 15 events for tomorrow (should show overflow)
        calendar_events = []
        for i in range(15):
            calendar_events.append(
                {
                    "calendar_id": "calendar.personal",
                    "calendar_icon": "mdi:calendar",
                    "summary": f"Event {i + 1}",
                    "start": f"2026-01-26T{(9 + i) % 24:02d}:00:00",
                    "end": f"2026-01-26T{(10 + i) % 24:02d}:00:00",
                    "description": "",
                    "location": "",
                }
            )

        png_data = render_to_png(calendar_events, [], None, self.now, {})
        output_path = self.output_dir / "overflow_indicator.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Overflow indicator render saved to: {output_path}")

    def test_empty_calendar(self):
        """Test rendering with no events."""
        png_data = render_to_png([], [], None, self.now, {})
        output_path = self.output_dir / "empty_calendar.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Empty calendar render saved to: {output_path}")

    def test_upcoming_section(self):
        """Test upcoming events section (beyond 6-day view)."""
        calendar_events = [
            {
                "calendar_id": "calendar.personal",
                "calendar_icon": "mdi:calendar",
                "summary": "Event Next Week",
                "start": "2026-02-02",
                "end": "2026-02-02",
                "description": "",
                "location": "",
            },
            {
                "calendar_id": "calendar.work",
                "calendar_icon": "mdi:briefcase",
                "summary": "Multi-Day Next Week",
                "start": "2026-02-03",
                "end": "2026-02-05",
                "description": "",
                "location": "",
            },
        ]

        png_data = render_to_png(calendar_events, [], None, self.now, {})
        output_path = self.output_dir / "upcoming_section.png"
        with open(output_path, "wb") as f:
            f.write(png_data)

        print(f"✓ Upcoming section render saved to: {output_path}")

    def test_generate_comparison_report(self):
        """Generate an HTML report comparing all outputs."""
        # Get all generated PNGs
        png_files = sorted(self.output_dir.glob("*.png"))

        if not png_files:
            self.skipTest("No PNG files generated yet")

        html_content = (
            """<!DOCTYPE html>
<html>
<head>
    <title>E-Ink Calendar Visual Regression Test Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        .test-case {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .test-name {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2196F3;
        }
        .image-container {
            margin: 10px 0;
        }
        img {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .info {
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }
        .header {
            background: #2196F3;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>E-Ink Calendar Visual Regression Test Report</h1>
        <p>Python Implementation Rendering Tests</p>
        <p>Generated: """
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + """</p>
    </div>
"""
        )

        for png_file in png_files:
            test_name = png_file.stem.replace("_", " ").title()
            html_content += f"""
    <div class="test-case">
        <div class="test-name">{test_name}</div>
        <div class="image-container">
            <img src="{png_file.name}" alt="{test_name}">
        </div>
        <div class="info">
            File: {png_file.name}<br>
            Size: {png_file.stat().st_size:,} bytes
        </div>
    </div>
"""

        html_content += """
    <div class="test-case">
        <div class="test-name">Testing Instructions</div>
        <p>Compare these Python-generated images with the TypeScript reference outputs.</p>
        <p>Look for differences in:</p>
        <ul>
            <li>Font rendering and spacing</li>
            <li>Text alignment and positioning</li>
            <li>Icon placement</li>
            <li>Line widths and colors</li>
            <li>Section boundaries</li>
            <li>Multi-day event indicators (arrows, triangles)</li>
            <li>Weather icons and temperatures</li>
            <li>Waste collection icon positioning</li>
            <li>Overflow indicators (+X more)</li>
        </ul>
    </div>
</body>
</html>
"""

        report_path = self.output_dir / "visual_regression_report.html"
        with open(report_path, "w") as f:
            f.write(html_content)

        print(f"\n{'=' * 60}")
        print("✓ Visual regression report generated:")
        print(f"  {report_path}")
        print("  Open this file in your browser to review all test renders")
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
