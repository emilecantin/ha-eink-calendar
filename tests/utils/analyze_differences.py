#!/usr/bin/env python3
"""Analyze visual differences between TypeScript and Python renders."""

from pathlib import Path

from PIL import Image


def analyze_difference(ts_path, py_path):
    """Analyze differences between two images."""
    ts_img = Image.open(ts_path).convert("RGB")
    py_img = Image.open(py_path).convert("RGB")

    if ts_img.size != py_img.size:
        return f"SIZE MISMATCH: TS={ts_img.size} vs PY={py_img.size}"

    # Calculate pixel differences
    width, height = ts_img.size
    total_pixels = width * height
    different_pixels = 0

    ts_pixels = ts_img.load()
    py_pixels = py_img.load()

    # Sample every 10th pixel for speed
    for y in range(0, height, 10):
        for x in range(0, width, 10):
            if ts_pixels[x, y] != py_pixels[x, y]:
                different_pixels += 1

    # Extrapolate to full image
    sampled_pixels = (width // 10) * (height // 10)
    estimated_diff = (different_pixels / sampled_pixels) * total_pixels
    diff_percent = (estimated_diff / total_pixels) * 100

    return f"{estimated_diff:,.0f} pixels ({diff_percent:.1f}%)"


def main():
    project_root = Path(__file__).parent.parent.parent
    comparison_dir = project_root / "comparison_tests"

    print("\n" + "=" * 70)
    print("Visual Difference Analysis")
    print("=" * 70 + "\n")

    scenarios = [
        "empty_calendar",
        "single_event_tomorrow",
        "multiple_events_tomorrow",
        "all_day_events",
        "multi_day_event",
        "long_title_wrapping",
        "overflow_events",
        "weekend_event",
        "waste_collection",
        "weather_forecast",
        "upcoming_events",
        "full_calendar",
    ]

    for scenario in scenarios:
        ts_file = comparison_dir / f"{scenario}_typescript.png"
        py_file = comparison_dir / f"{scenario}_python.png"

        if not ts_file.exists() or not py_file.exists():
            print(f"{scenario:30s} MISSING FILES")
            continue

        result = analyze_difference(ts_file, py_file)
        print(f"{scenario:30s} {result}")

    print("\n" + "=" * 70)
    print("\nNOTE: High percentages indicate significant visual differences")
    print("      Low percentages (<5%) are usually font rendering differences")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
