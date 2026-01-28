#!/usr/bin/env python3
"""
Generate HTML comparison report showing TypeScript vs Python renders side-by-side.

Run after both test runners have completed:
  python3 create_comparison_report.py
"""

import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

COMPARISON_DIR = PROJECT_ROOT / "comparison_tests"
REPORT_FILE = COMPARISON_DIR / "comparison_report.html"


def create_diff_image(ts_path, py_path):
    """Create a diff image highlighting differences in red."""
    ts_img = Image.open(ts_path).convert("RGB")
    py_img = Image.open(py_path).convert("RGB")

    ts_pixels = ts_img.load()
    py_pixels = py_img.load()

    # Create diff image
    diff_img = Image.new("RGB", ts_img.size, (255, 255, 255))
    diff_pixels = diff_img.load()

    diff_count = 0
    for y in range(ts_img.height):
        for x in range(ts_img.width):
            ts_rgb = ts_pixels[x, y]
            py_rgb = py_pixels[x, y]

            if ts_rgb != py_rgb:
                # Bright magenta for differences (high contrast with red and black)
                diff_pixels[x, y] = (255, 0, 255)
                diff_count += 1
            else:
                # Keep original pixel
                diff_pixels[x, y] = ts_rgb

    # Save diff
    diff_path = COMPARISON_DIR / f"{ts_path.stem.replace('_typescript', '')}_diff.png"
    diff_img.save(diff_path)

    return diff_path, diff_count


def create_side_by_side(ts_path, py_path, scenario_name):
    """Create a side-by-side comparison image and diff image."""
    ts_img = Image.open(ts_path)
    py_img = Image.open(py_path)

    # Create diff image
    diff_path, diff_count = create_diff_image(ts_path, py_path)

    # Create comparison canvas with space for 3 images
    padding = 20
    gap = 20
    label_height = 60

    width = (ts_img.width * 3) + (2 * padding) + (gap * 2)
    height = max(ts_img.height, py_img.height) + (2 * padding) + label_height

    comparison = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(comparison)

    # Try to load font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except Exception:
        font = ImageFont.load_default()

    # Labels
    draw.text((padding, 10), "TypeScript (Reference)", fill="blue", font=font)
    draw.text((padding + ts_img.width + gap, 10), "Python (New)", fill="red", font=font)
    diff_img = Image.open(diff_path)
    total_pixels = ts_img.width * ts_img.height
    diff_pct = (diff_count / total_pixels) * 100
    draw.text(
        (padding + (ts_img.width + gap) * 2, 10),
        f"Diff ({diff_count} pixels, {diff_pct:.1f}%)",
        fill="purple",
        font=font,
    )

    # Paste images
    y_offset = label_height
    comparison.paste(ts_img, (padding, y_offset))
    comparison.paste(py_img, (padding + ts_img.width + gap, y_offset))
    comparison.paste(diff_img, (padding + (ts_img.width + gap) * 2, y_offset))

    # Draw borders
    draw.rectangle(
        [
            padding - 1,
            y_offset - 1,
            padding + ts_img.width + 1,
            y_offset + ts_img.height + 1,
        ],
        outline="blue",
        width=2,
    )
    draw.rectangle(
        [
            padding + ts_img.width + gap - 1,
            y_offset - 1,
            padding + ts_img.width + gap + py_img.width + 1,
            y_offset + py_img.height + 1,
        ],
        outline="red",
        width=2,
    )
    draw.rectangle(
        [
            padding + (ts_img.width + gap) * 2 - 1,
            y_offset - 1,
            padding + (ts_img.width + gap) * 2 + diff_img.width + 1,
            y_offset + diff_img.height + 1,
        ],
        outline="purple",
        width=2,
    )

    # Save
    output_path = (
        COMPARISON_DIR / f"{ts_path.stem.replace('_typescript', '')}_comparison.png"
    )
    comparison.save(output_path)
    return output_path, diff_count


print("\n" + "=" * 70)
print("Generating Comparison Report")
print("=" * 70 + "\n")

# Find all TypeScript renders
ts_files = sorted(COMPARISON_DIR.glob("*_typescript.png"))

if not ts_files:
    print("✗ No TypeScript renders found!")
    print(f"  Expected in: {COMPARISON_DIR.absolute()}")
    print("\nRun: node run_comparison_tests.js")
    exit(1)

print(f"Found {len(ts_files)} TypeScript renders\n")

# Generate comparisons
html_parts = []
html_parts.append(
    """<!DOCTYPE html>
<html>
<head>
    <title>TypeScript vs Python Rendering Comparison</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        h1 { margin: 0 0 10px 0; }
        .subtitle { opacity: 0.9; margin: 0; }
        .test-case {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .test-name {
            font-size: 22px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .test-description {
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .comparison-img {
            width: 100%;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .legend {
            display: flex;
            gap: 30px;
            margin-top: 10px;
            font-size: 14px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-box {
            width: 20px;
            height: 20px;
            border-radius: 3px;
        }
        .legend-ts { background: blue; }
        .legend-py { background: red; }
        .stats {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>TypeScript vs Python Rendering Comparison</h1>
        <p class="subtitle">Generated: """
    + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    + """</p>
    </div>
"""
)

comparison_count = 0
missing_count = 0

for ts_file in ts_files:
    scenario_id = ts_file.stem.replace("_typescript", "")
    py_file = COMPARISON_DIR / f"{scenario_id}_python.png"

    # Load test data for description
    from test_data_library import TEST_SCENARIOS

    scenario = TEST_SCENARIOS.get(scenario_id, {})
    name = scenario.get("name", scenario_id.replace("_", " ").title())
    description = scenario.get("description", "")

    print(f"Processing: {name}...")

    if not py_file.exists():
        print(f"  ⚠ Missing Python render: {py_file.name}")
        html_parts.append(f"""
    <div class="test-case">
        <div class="test-name">{name}</div>
        <div class="test-description">{description}</div>
        <p style="color: orange;">⚠ Python render missing - run Python tests</p>
    </div>
""")
        missing_count += 1
        continue

    # Create side-by-side comparison
    comparison_path, diff_count = create_side_by_side(ts_file, py_file, name)
    print(f"  ✓ Created: {comparison_path.name}")

    # Get file sizes
    ts_size = ts_file.stat().st_size
    py_size = py_file.stat().st_size
    total_pixels = Image.open(ts_file).width * Image.open(ts_file).height
    diff_pct = (diff_count / total_pixels) * 100

    html_parts.append(f'''
    <div class="test-case">
        <div class="test-name">{name}</div>
        <div class="test-description">{description}</div>
        <img src="{comparison_path.name}" alt="{name}" class="comparison-img">
        <div class="legend">
            <div class="legend-item">
                <div class="legend-box legend-ts"></div>
                <span>TypeScript: {ts_size:,} bytes</span>
            </div>
            <div class="legend-item">
                <div class="legend-box legend-py"></div>
                <span>Python: {py_size:,} bytes</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: purple;"></div>
                <span>Diff: {diff_count:,} pixels ({diff_pct:.2f}%)</span>
            </div>
        </div>
    </div>
''')
    comparison_count += 1

# Summary
html_parts.append(f"""
    <div class="stats">
        <strong>Summary:</strong> Generated {comparison_count} comparisons
        {f"<br>⚠ Missing {missing_count} Python renders" if missing_count > 0 else ""}
    </div>

    <div class="test-case">
        <div class="test-name">Review Checklist</div>
        <p>Look for differences in:</p>
        <ul>
            <li><strong>Font rendering:</strong> Size, weight, spacing</li>
            <li><strong>Text alignment:</strong> Horizontal and vertical positioning</li>
            <li><strong>Icons:</strong> Size, position, rendering</li>
            <li><strong>Colors:</strong> Black/red layer separation</li>
            <li><strong>Spacing:</strong> Padding, margins, line height</li>
            <li><strong>Multi-day indicators:</strong> Arrows (◀ ▶), positioning</li>
            <li><strong>Weather:</strong> Icon symbols, temperature formatting</li>
            <li><strong>Waste icons:</strong> Positioning in calendar grid</li>
            <li><strong>Text wrapping:</strong> Line breaks, truncation</li>
            <li><strong>Overflow:</strong> "+X more" indicator</li>
        </ul>
    </div>
</body>
</html>
""")

# Write report
REPORT_FILE.write_text("".join(html_parts))

print("\n" + "=" * 70)
print(f"✓ Report generated: {REPORT_FILE}")
print(f"  {comparison_count} comparisons created")
if missing_count > 0:
    print(f"  ⚠ {missing_count} Python renders missing")
print(f"\nOpen: file://{REPORT_FILE.absolute()}")
print("=" * 70 + "\n")
