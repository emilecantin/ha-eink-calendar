#!/usr/bin/env python3
"""
Generate PNG icons from Material Design Icons (MDI) SVG files.

This script downloads SVG icons from the @mdi/svg npm package and converts
them to 24x24 PNG files for use in the E-Ink Calendar renderer.
"""

import json
import subprocess
import sys
from pathlib import Path

try:
    from cairosvg import svg2png  # pyright: ignore[reportMissingImports]
except ImportError:
    print("Error: cairosvg is required. Install with: pip install cairosvg")
    sys.exit(1)

# Icon names to generate (without mdi: prefix)
ICONS_TO_GENERATE = [
    # Existing icons (for reference/regeneration)
    "airplane",
    "bell",
    "briefcase",
    "calendar",
    "car",
    "check",
    "email",
    "food",
    "gift",
    "heart",
    "home",
    "medical",
    "party",
    "phone",
    "school",
    "shopping",
    "star",
    # New common calendar icons
    "infinity",
    "account",
    "account-group",
    "baby-face",
    "bank",
    "basket",
    "beach",
    "beer",
    "bike",
    "book",
    "bookmark",
    "brush",
    "bug",
    "cake",
    "camera",
    "cash",
    "charity",
    "chart-line",
    "church",
    "city",
    "clipboard",
    "clock",
    "coffee",
    "cog",
    "compass",
    "controller-classic",
    "creation",
    "domain",
    "dumbbell",
    "earth",
    "family-tree",
    "ferry",
    "file-document",
    "film",
    "finance",
    "fire",
    "flag",
    "flask",
    "flower",
    "football",
    "forest",
    "fuel",
    "gamepad",
    "glass-cocktail",
    "golf",
    "hammer",
    "handshake",
    "hiking",
    "hospital",
    "image",
    "karate",
    "key",
    "ladder",
    "laptop",
    "leaf",
    "library",
    "lightbulb",
    "link",
    "lock",
    "map-marker",
    "meditation",
    "microphone",
    "monitor",
    "motorbike",
    "music",
    "nature",
    "newspaper",
    "notebook",
    "palette",
    "paw",
    "pencil",
    "pharmacy",
    "piano",
    "pill",
    "pizza",
    "presentation",
    "printer",
    "puzzle",
    "racquetball",
    "restore",
    "robot",
    "rocket",
    "run",
    "sail-boat",
    "scale-balance",
    "scissors",
    "shield",
    "ship-wheel",
    "sitemap",
    "soccer",
    "sofa",
    "spa",
    "subway",
    "swim",
    "sync",
    "taxi",
    "teach",
    "television",
    "tennis",
    "thumb-up",
    "tools",
    "train",
    "trophy",
    "truck",
    "umbrella",
    "video",
    "wallet",
    "water",
    "waves",
    "weight-lifter",
    "wifi",
    "wrench",
    "yoga",
]

# Icon size (24x24 to match existing icons)
ICON_SIZE = 24


def download_mdi_svg(icon_name: str, svg_dir: Path) -> Path | None:
    """
    Download MDI SVG icon from jsdelivr CDN.

    Args:
        icon_name: Icon name without 'mdi:' prefix (e.g., 'calendar', 'infinity')
        svg_dir: Directory to save SVG files

    Returns:
        Path to downloaded SVG file, or None if download failed
    """
    svg_file = svg_dir / f"{icon_name}.svg"

    if svg_file.exists():
        return svg_file

    # Try to download from jsdelivr CDN
    url = f"https://cdn.jsdelivr.net/npm/@mdi/svg@latest/svg/{icon_name}.svg"

    print(f"Downloading {icon_name}...")
    try:
        subprocess.run(
            ["curl", "-sL", "-o", str(svg_file), url],
            check=True,
            capture_output=True,
            text=True,
        )

        # Check if file was downloaded and is valid SVG
        if svg_file.exists() and svg_file.stat().st_size > 0:
            with open(svg_file, "r") as f:
                content = f.read()
                if "<svg" in content:
                    return svg_file

        print(f"  Warning: Failed to download {icon_name}")
        if svg_file.exists():
            svg_file.unlink()
        return None

    except subprocess.CalledProcessError as e:
        print(f"  Error downloading {icon_name}: {e}")
        return None


def convert_svg_to_png(svg_file: Path, png_file: Path) -> bool:
    """
    Convert SVG to PNG using cairosvg.

    Args:
        svg_file: Path to SVG file
        png_file: Path to output PNG file

    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        svg2png(
            url=str(svg_file),
            write_to=str(png_file),
            output_width=ICON_SIZE,
            output_height=ICON_SIZE,
        )
        return True
    except Exception as e:
        print(f"  Error converting {svg_file.name}: {e}")
        return False


def main():
    """Generate PNG icons from MDI SVG files."""
    script_dir = Path(__file__).parent
    icons_dir = script_dir / "icons"
    svg_dir = script_dir / "icons_svg_cache"

    # Create directories
    icons_dir.mkdir(exist_ok=True)
    svg_dir.mkdir(exist_ok=True)

    print(f"Generating {len(ICONS_TO_GENERATE)} icons...")
    print(f"Icons directory: {icons_dir}")
    print(f"SVG cache directory: {svg_dir}")
    print()

    success_count = 0
    failed_icons = []

    for icon_name in ICONS_TO_GENERATE:
        png_file = icons_dir / f"{icon_name}.png"

        # Download SVG
        svg_file = download_mdi_svg(icon_name, svg_dir)
        if not svg_file:
            failed_icons.append(icon_name)
            continue

        # Convert to PNG
        if convert_svg_to_png(svg_file, png_file):
            print(f"  ✓ Generated {icon_name}.png")
            success_count += 1
        else:
            failed_icons.append(icon_name)

    print()
    print(f"Successfully generated {success_count}/{len(ICONS_TO_GENERATE)} icons")

    if failed_icons:
        print(f"\nFailed to generate {len(failed_icons)} icons:")
        for icon_name in failed_icons:
            print(f"  - {icon_name}")

    # Generate a JSON file listing all available icons
    available_icons = sorted([f.stem for f in icons_dir.glob("*.png")])
    icons_list_file = icons_dir / "available_icons.json"
    with open(icons_list_file, "w") as f:
        json.dump(available_icons, f, indent=2)

    print(f"\nTotal icons available: {len(available_icons)}")
    print(f"Icon list saved to: {icons_list_file}")


if __name__ == "__main__":
    main()
