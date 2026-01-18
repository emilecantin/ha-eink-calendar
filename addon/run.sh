#!/usr/bin/env bash
set -e

# EPCAL Startup Script
# Supports both Home Assistant Add-on mode and standalone Docker mode

echo "Starting EPCAL - E-Paper Calendar..."

# Detect if running in HA Supervisor environment
if [ -n "${SUPERVISOR_TOKEN:-}" ] && [ -f /usr/lib/bashio/bashio.sh ]; then
    # ===== HA ADD-ON MODE =====
    echo "Running in Home Assistant Add-on mode"

    # Source bashio library
    source /usr/lib/bashio/bashio.sh

    # Get configuration options
    LOG_LEVEL=$(bashio::config 'log_level' 2>/dev/null || echo "info")
    bashio::log.info "Log level: ${LOG_LEVEL}"

    # Export environment variables for the Node.js server
    export HA_URL="http://supervisor/core"
    export HA_TOKEN="${SUPERVISOR_TOKEN}"
    export PORT=4000
    export LOG_LEVEL="${LOG_LEVEL}"

    # Check if running with Ingress
    if bashio::var.has_value "$(bashio::addon.ingress_entry 2>/dev/null)"; then
        INGRESS_ENTRY=$(bashio::addon.ingress_entry)
        bashio::log.info "Ingress enabled at: ${INGRESS_ENTRY}"
        export INGRESS_PATH="${INGRESS_ENTRY}"
    fi

    # Data directory for persistent config (add-on mode)
    export CONFIG_PATH="/data/epcal-config.json"

    bashio::log.info "Home Assistant API: ${HA_URL}"
    bashio::log.info "Config file: ${CONFIG_PATH}"
else
    # ===== STANDALONE DOCKER MODE =====
    echo "Running in standalone Docker mode"

    # Use environment variables or defaults
    export PORT="${PORT:-4000}"
    export CONFIG_PATH="${CONFIG_PATH:-/app/config/.epcal-config.json}"

    echo "Config file: ${CONFIG_PATH}"
    echo "Port: ${PORT}"
fi

# Start the server
echo "Starting server on port ${PORT}..."
exec npx ts-node index.ts
