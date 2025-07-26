#!/usr/bin/with-contenv bashio

# Home Assistant Add-on: Tasmota Master
# Main entry point script

set -e

bashio::log.info "Starting Tasmota Master Add-on..."

# Get configuration options from Home Assistant
MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USERNAME=$(bashio::config 'mqtt_username' '')
MQTT_PASSWORD=$(bashio::config 'mqtt_password' '')
DISCOVERY_PREFIX=$(bashio::config 'discovery_prefix')
LOG_LEVEL=$(bashio::config 'log_level')
GITHUB_TOKEN=$(bashio::config 'github_token' '')
ENABLE_ANALYTICS=$(bashio::config 'enable_analytics')
MAX_CACHE_SIZE=$(bashio::config 'max_cache_size_gb')
COMMUNITY_FEATURES=$(bashio::config 'community_features')
DEVICE_SCAN_INTERVAL=$(bashio::config 'device_scan_interval')
AUTO_BACKUP=$(bashio::config 'auto_backup')

bashio::log.info "Configuration loaded:"
bashio::log.info "- MQTT Host: ${MQTT_HOST}"
bashio::log.info "- MQTT Port: ${MQTT_PORT}"
bashio::log.info "- Discovery Prefix: ${DISCOVERY_PREFIX}"
bashio::log.info "- Log Level: ${LOG_LEVEL}"

# Export environment variables for the application
export MQTT_HOST="${MQTT_HOST}"
export MQTT_PORT="${MQTT_PORT}"
export MQTT_USERNAME="${MQTT_USERNAME}"
export MQTT_PASSWORD="${MQTT_PASSWORD}"
export DISCOVERY_PREFIX="${DISCOVERY_PREFIX}"
export LOG_LEVEL="${LOG_LEVEL}"
export GITHUB_TOKEN="${GITHUB_TOKEN}"
export ENABLE_ANALYTICS="${ENABLE_ANALYTICS}"
export MAX_CACHE_SIZE_GB="${MAX_CACHE_SIZE}"
export COMMUNITY_FEATURES="${COMMUNITY_FEATURES}"
export DEVICE_SCAN_INTERVAL="${DEVICE_SCAN_INTERVAL}"
export AUTO_BACKUP="${AUTO_BACKUP}"

# Home Assistant specific environment variables
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"
export HASSIO_TOKEN="${SUPERVISOR_TOKEN}"

# Set Python path
export PYTHONPATH="/opt/app/backend:${PYTHONPATH}"
export FLASK_ENV="production"

# Create necessary directories
mkdir -p /opt/app/data /opt/app/logs /opt/app/config

# Change to backend directory
cd /opt/app/backend

# Start nginx in background
bashio::log.info "Starting nginx..."
nginx -g 'daemon on;'

# Wait a moment for nginx to start
sleep 2

# Start the Flask application
bashio::log.info "Starting Tasmota Master Flask application..."
exec python3 app.py