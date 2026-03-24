#!/usr/bin/env python3
"""
Single entry point for visual regression testing.

This script:
1. Generates all test images using both TypeScript and Python renderers
2. Computes pixel differences
3. Generates HTML comparison report
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report status."""
    print(f"\n{'=' * 70}")
    print(f"{description}")
    print(f"{'=' * 70}")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    return True


def main():
    print("E-Ink Calendar Visual Regression Test Suite")
    print("=" * 70)

    # Step 1: Generate TypeScript reference renders
    if not run_command(
        "cd server && npm run build && node run_comparison_tests.js",
        "Step 1/4: Generating TypeScript reference renders",
    ):
        print("\n❌ Failed to generate TypeScript renders")
        return 1

    # Step 2: Generate Python renders with standalone renderer
    if not run_command(
        "python3 tests/utils/regenerate_all_tests.py",
        "Step 2/4: Generating Python renders",
    ):
        print("\n❌ Failed to generate Python renders")
        return 1

    # Step 3: Analyze pixel differences
    if not run_command(
        "python3 tests/utils/analyze_differences.py",
        "Step 3/4: Analyzing pixel differences",
    ):
        print("\n❌ Failed to analyze differences")
        return 1

    # Step 4: Generate HTML comparison report
    if not run_command(
        "python3 tests/utils/create_comparison_report.py",
        "Step 4/4: Generating HTML comparison report",
    ):
        print("\n❌ Failed to generate report")
        return 1

    # Success
    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)
    print("\nView results:")
    report_path = Path("comparison_tests/comparison_report.html").absolute()
    print(f"  open {report_path}")
    print("\nOr:")
    print(f"  file://{report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
