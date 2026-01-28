#!/usr/bin/env python3
"""Analyze rendering differences - simple version without numpy."""

import sys
from pathlib import Path

from PIL import Image


def analyze_diff_image(diff_path: Path, ts_path: Path, py_path: Path):
    """Analyze a diff image and identify patterns."""
    print(f"\n{'=' * 70}")
    print(f"Analyzing: {diff_path.stem.replace('_diff', '')}")
    print("=" * 70)

    # Load images
    ts_img = Image.open(ts_path).convert("RGB")
    py_img = Image.open(py_path).convert("RGB")

    # Get dimensions
    width, height = ts_img.size
    total_pixels = width * height

    # Count differences
    num_diff = 0
    diff_samples = []

    ts_pixels = ts_img.load()
    py_pixels = py_img.load()

    for y in range(height):
        for x in range(width):
            ts_pixel = ts_pixels[x, y]  # pyright: ignore[reportOptionalSubscript]
            py_pixel = py_pixels[x, y]  # pyright: ignore[reportOptionalSubscript]
            if ts_pixel != py_pixel:
                num_diff += 1
                if len(diff_samples) < 10:  # Sample first 10 differences
                    diff_samples.append((x, y, ts_pixel, py_pixel))

    percent = (num_diff / total_pixels) * 100

    print(f"Different pixels: {num_diff:,} ({percent:.2f}%)")
    print(f"Image size: {width}×{height}")

    if num_diff == 0:
        print("✓ Images are identical!")
        return

    print("\nSample differences (first 5):")
    for x, y, ts_pixel, py_pixel in diff_samples[:5]:
        print(f"  ({x:4d}, {y:4d}): TS={ts_pixel} PY={py_pixel}")


def main():
    """Analyze all diff images."""
    comparison_dir = Path(__file__).parent / "comparison_tests"

    if not comparison_dir.exists():
        print(f"Error: {comparison_dir} does not exist")
        sys.exit(1)

    diff_files = sorted(comparison_dir.glob("*_diff.png"))

    if not diff_files:
        print("No diff files found")
        sys.exit(1)

    print(f"\nFound {len(diff_files)} diff files to analyze\n")

    for diff_path in diff_files:
        # Get corresponding TypeScript and Python images
        base_name = diff_path.stem.replace("_diff", "")
        ts_path = comparison_dir / f"{base_name}_typescript.png"
        py_path = comparison_dir / f"{base_name}_python.png"

        if not ts_path.exists() or not py_path.exists():
            print(f"Skipping {base_name}: missing TypeScript or Python image")
            continue

        analyze_diff_image(diff_path, ts_path, py_path)


if __name__ == "__main__":
    main()
