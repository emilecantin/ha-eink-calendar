#!/usr/bin/env python3
"""Analyze rendering differences between TypeScript and Python outputs."""

import sys
from pathlib import Path

import numpy as np  # pyright: ignore[reportMissingImports]
from PIL import Image


def analyze_diff_image(diff_path: Path, ts_path: Path, py_path: Path):
    """Analyze a diff image and identify patterns."""
    print(f"\n{'=' * 70}")
    print(f"Analyzing: {diff_path.stem.replace('_diff', '')}")
    print("=" * 70)

    # Load images
    diff_img = Image.open(diff_path)
    ts_img = Image.open(ts_path)
    py_img = Image.open(py_path)

    # Convert to numpy arrays
    diff_arr = np.array(diff_img)
    ts_arr = np.array(ts_img)
    py_arr = np.array(py_img)

    # Find different pixels (purple in diff image)
    # Purple is roughly (128, 0, 128) in the diff
    diff_mask = np.any(diff_arr != [255, 255, 255], axis=2)

    num_diff = np.sum(diff_mask)
    total_pixels = diff_mask.shape[0] * diff_mask.shape[1]
    percent = (num_diff / total_pixels) * 100

    print(f"Different pixels: {num_diff:,} ({percent:.2f}%)")

    if num_diff == 0:
        print("✓ Images are identical!")
        return

    # Find bounding box of differences
    rows, cols = np.where(diff_mask)
    if len(rows) > 0:
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()

        print(f"Difference region: ({min_col}, {min_row}) to ({max_col}, {max_row})")
        print(f"Size: {max_col - min_col}×{max_row - min_row}")

        # Sample some different pixels to understand the pattern
        sample_indices = np.random.choice(len(rows), min(10, len(rows)), replace=False)

        print("\nSample differences:")
        for idx in sample_indices[:5]:
            r, c = rows[idx], cols[idx]
            ts_pixel = ts_arr[r, c]
            py_pixel = py_arr[r, c]
            print(f"  Position ({c}, {r}): TS={ts_pixel} PY={py_pixel}")

    # Check if differences are primarily in text/antialiasing
    # Compare RGB channels
    if len(diff_arr.shape) == 3:
        r_diff = np.sum(ts_arr[:, :, 0] != py_arr[:, :, 0])
        g_diff = np.sum(ts_arr[:, :, 1] != py_arr[:, :, 1])
        b_diff = np.sum(ts_arr[:, :, 2] != py_arr[:, :, 2])

        print(f"\nChannel differences: R={r_diff:,} G={g_diff:,} B={b_diff:,}")

        # If all channels have same diff count, likely solid color differences
        if r_diff == g_diff == b_diff:
            print("→ Solid color differences (not antialiasing)")
        else:
            print("→ Mixed color differences (possibly antialiasing or gradients)")


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
