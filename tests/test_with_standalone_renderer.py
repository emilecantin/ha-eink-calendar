#!/usr/bin/env python3
"""Test script using EPCAL renderer."""

import sys
from pathlib import Path

# Add custom_components/epcal to path to make renderer importable as a package
# This avoids importing the HA integration's __init__.py
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "epcal"))

# Now we can import renderer as a relative package
from renderer.renderer import render_to_png
from test_data_library import NOW, TEST_SCENARIOS


def test_render():
    print("Testing EPCAL Renderer")
    print("=" * 70)

    scenario = TEST_SCENARIOS["single_event_tomorrow"]

    print("\nRendering 'single_event_tomorrow' scenario...")
    png = render_to_png(
        scenario["events"],
        scenario["waste_events"],
        scenario["weather"],
        NOW,
        scenario["options"],
    )

    print(f"✓ Successfully rendered PNG ({len(png)} bytes)")

    # Save output
    output_path = Path("comparison_tests/python_test.png")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(png)

    print(f"✓ Saved to {output_path}")
    print("\n✅ Test successful!")
    return True


if __name__ == "__main__":
    success = test_render()
    sys.exit(0 if success else 1)
