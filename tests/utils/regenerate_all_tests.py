#!/usr/bin/env python3
"""Generate Python test renders from shared JSON test scenarios."""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add custom_components/eink_calendar to path to make renderer importable as a package
# This avoids importing the HA integration's __init__.py
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "custom_components" / "eink_calendar")
)

# Now we can import renderer as a relative package
from renderer.renderer import render_to_png

# Load shared test scenarios
test_scenarios_path = Path(__file__).parent.parent / "fixtures" / "test_scenarios.json"
with open(test_scenarios_path) as f:
    test_data = json.load(f)

NOW = datetime.fromisoformat(test_data["NOW"])
TEST_SCENARIOS = test_data["scenarios"]

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "comparison_tests"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_tests():
    """Generate all test renders."""
    print("\n" + "=" * 70)
    print("Python Renderer - Comparison Tests")
    print("=" * 70 + "\n")

    passed = 0
    failed = 0

    for scenario_id, scenario in TEST_SCENARIOS.items():
        print(f"Testing: {scenario['name']}")
        print(f"  Description: {scenario['description']}")

        try:
            # Convert to format expected by Python renderer (_process_events)
            # It expects string dates and Home Assistant field names
            # For all-day events, it expects dates WITHOUT time (no "T")
            events = []
            for e in scenario["events"]:
                start = e["start"]
                end = e["end"]

                # If all-day event, remove time part (Python checks for "T" to determine all-day)
                if e.get("allDay", False):
                    start = start.split("T")[0]
                    end = end.split("T")[0]

                events.append(
                    {
                        "id": e["id"],
                        "summary": e["title"],  # Python uses "summary"
                        "start": start,  # String date - parsed by renderer
                        "end": end,  # String date - parsed by renderer
                        "calendar_icon": e[
                            "calendarIcon"
                        ],  # Python uses "calendar_icon"
                        "calendar_id": e["calendarId"],  # Python uses "calendar_id"
                    }
                )

            # Parse weather data
            weather_data = None
            if scenario["weather"]:
                weather_data = {
                    "forecast": [  # Python renderer expects "forecast" not "forecasts"
                        {
                            "datetime": f[
                                "date"
                            ],  # Keep as string - Python parser expects string
                            "condition": f["condition"],
                            "temperature": (f["tempHigh"] + f["tempLow"]) / 2,
                            "templow": f["tempLow"],
                            "temphigh": f["tempHigh"],
                        }
                        for f in scenario["weather"]
                    ]
                }

            # Options
            options = {"waste_calendars": scenario.get("collectionCalendarIds", [])}

            # Render
            png = render_to_png(
                calendar_events=events,
                waste_events=[],  # Already included in events
                weather_data=weather_data,
                now=NOW,
                options=options,
            )

            # Save output
            output_path = OUTPUT_DIR / f"{scenario_id}_python.png"
            with open(output_path, "wb") as f:
                f.write(png)

            print(f"  ✓ Rendered: {len(png):,} bytes")
            print(f"  Saved to: {output_path.relative_to(Path.cwd())}\n")
            passed += 1

        except Exception as error:
            print(f"  ✗ Failed: {error}\n")
            failed += 1

    print("=" * 70)
    print(f"\nResults: {passed}/{passed + failed} scenarios rendered")
    print(f"\nPython outputs saved to: {OUTPUT_DIR.relative_to(Path.cwd())}/")
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
