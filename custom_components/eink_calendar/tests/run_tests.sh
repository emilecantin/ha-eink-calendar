#!/usr/bin/env bash
# Run all renderer unit tests.
# Usage: ./run_tests.sh [pytest args...]
#   e.g. ./run_tests.sh -k "weather"
#        ./run_tests.sh --no-header -q

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Repo root is epcal/ (3 levels up from tests/)
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV="$REPO_ROOT/.venv"

if [ ! -d "$VENV" ]; then
    echo "Creating venv and installing dependencies..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q pytest pillow python-dateutil
fi

cd "$SCRIPT_DIR"
exec "$VENV/bin/python" -m pytest "$@"
