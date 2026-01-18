#!/usr/bin/env bash
set -e

# EPCAL Add-on Startup Script
# Uses bashio for Home Assistant Supervisor API integration

# Source bashio library
source /usr/lib/bashio/bashio.sh

bashio::log.info "Starting EPCAL - E-Paper Calendar..."

# Get configuration options
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.info "Log level: ${LOG_LEVEL}"

# Home Assistant Supervisor provides these environment variables:
# - SUPERVISOR_TOKEN: Token for Supervisor API
# - SUPERVISOR_API: URL to Supervisor API (usually http://supervisor)
#
# For the HA Core API, we use:
# - http://supervisor/core/api with SUPERVISOR_TOKEN

# Export environment variables for the Node.js server
export HA_URL="http://supervisor/core"
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export PORT=4000
export LOG_LEVEL="${LOG_LEVEL}"

# Check if running with Ingress
if bashio::var.has_value "$(bashio::addon.ingress_entry)"; then
    INGRESS_ENTRY=$(bashio::addon.ingress_entry)
    bashio::log.info "Ingress enabled at: ${INGRESS_ENTRY}"
    export INGRESS_PATH="${INGRESS_ENTRY}"
fi

# Data directory for persistent config
export CONFIG_PATH="/data/epcal-config.json"

bashio::log.info "Home Assistant API: ${HA_URL}"
bashio::log.info "Config file: ${CONFIG_PATH}"

# Start the server
bashio::log.info "Starting server on port ${PORT}..."
exec npx ts-node index.ts
