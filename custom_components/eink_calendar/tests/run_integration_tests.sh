#!/usr/bin/env bash
# Run integration tests against a real Home Assistant instance.
#
# Usage:
#   ./run_integration_tests.sh                 # HA must already be running
#   ./run_integration_tests.sh --start-ha      # Start HA via docker-compose first
#   ./run_integration_tests.sh -k "announce"   # Pass extra pytest args
#
# Environment variables:
#   HA_URL    — Base URL of the HA instance (default: http://localhost:18123)
#   HA_TOKEN  — Long-lived access token for HA API (needed for entry-creation tests)
#
# To create a long-lived access token:
#   1. Open HA UI → Profile → Long-Lived Access Tokens → Create Token
#   2. export HA_TOKEN="eyJ..."

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV="$REPO_ROOT/.venv"
COMPOSE_FILE="$REPO_ROOT/docker-compose.test.yml"

START_HA=false
STOP_HA=false
PYTEST_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --start-ha)
            START_HA=true
            STOP_HA=true
            shift
            ;;
        --stop-ha)
            STOP_HA=true
            shift
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Set defaults
export HA_URL="${HA_URL:-http://localhost:18123}"

# Ensure venv has required packages
if [ ! -d "$VENV" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q pytest pytest-asyncio aiohttp 2>/dev/null

# Start HA if requested
if [ "$START_HA" = true ]; then
    echo "Starting Home Assistant via docker-compose.test.yml..."
    docker compose -f "$COMPOSE_FILE" up -d

    echo "Waiting for Home Assistant to be ready..."
    MAX_WAIT=120
    ELAPSED=0
    until curl -sf "$HA_URL" > /dev/null 2>&1; do
        if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
            echo "ERROR: Home Assistant did not start within ${MAX_WAIT}s"
            echo "Check logs: docker compose -f $COMPOSE_FILE logs"
            exit 1
        fi
        sleep 2
        ELAPSED=$((ELAPSED + 2))
        printf "."
    done
    echo ""
    echo "Home Assistant is ready at $HA_URL"
fi

# Run integration tests
echo ""
echo "=== Running integration tests against $HA_URL ==="
echo ""

cd "$SCRIPT_DIR"
"$VENV/bin/python" -m pytest integration/ -v --tb=short "${PYTEST_ARGS[@]}" || TEST_EXIT=$?

# Stop HA if we started it
if [ "$STOP_HA" = true ]; then
    echo ""
    echo "Stopping Home Assistant..."
    docker compose -f "$COMPOSE_FILE" down
fi

exit ${TEST_EXIT:-0}
