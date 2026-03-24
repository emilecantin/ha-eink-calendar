#!/bin/bash
# Test runner script for E-Ink Calendar integration

set -e

echo "================================================"
echo "E-Ink Calendar Integration Test Suite"
echo "================================================"
echo ""

cd "$(dirname "$0")"

# Run unit tests
echo "Running unit tests..."
echo "--------------------"

python3 -m unittest test_event_filters.py
echo "✓ Event filters tests passed"

python3 -m unittest test_weather_utils.py
echo "✓ Weather utils tests passed"

python3 -m unittest test_event_renderer.py
echo "✓ Event renderer tests passed"

# Run integration tests
echo ""
echo "Running integration tests..."
echo "-----------------------------"

python3 -m unittest test_renderer_integration.py
echo "✓ Renderer integration tests passed"

echo ""
echo "================================================"
echo "All tests passed! ✓"
echo "================================================"
