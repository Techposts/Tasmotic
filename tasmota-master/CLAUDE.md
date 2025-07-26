# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tasmota Master is a comprehensive Home Assistant add-on for managing Tasmota devices. It features a hybrid firmware management system with four phases: official firmware tracking, smart caching with AI recommendations, community firmware platform, and advanced analytics engine.

## Architecture

### Multi-Service Backend Architecture
The system uses a modular service-oriented architecture centered around Flask with WebSocket support:

- **Main Application** (`app.py`): Central Flask app that orchestrates all services
- **Service Layer** (`services/`): 12 specialized services handling different aspects:
  - `firmware_manager.py`: Core firmware tracking from multiple sources (GitHub, OTA servers)
  - `firmware_cache.py`: LRU caching system with AI-powered recommendations using TF-IDF
  - `community_firmware.py`: Community upload platform with security scanning and moderation
  - `firmware_analytics.py`: ML-powered device compatibility analysis and risk assessment
  - `background_scheduler.py`: Comprehensive task scheduler with 8 scheduled jobs
  - `device_manager.py`, `device_discovery.py`: Device management and mDNS discovery
  - `mqtt_client.py`: MQTT integration for Home Assistant
  - `template_manager.py`: Device template system
  - `config_manager.py`: Configuration management
  - `flash_service.py`: ESP32/ESP8266 flashing service

### Frontend Architecture
React TypeScript application with Material-UI components, featuring:
- Real-time updates via Socket.IO
- WebSerial API integration for browser-based device flashing
- Tabbed interface for firmware management (recommendations, official, community, analytics)
- Responsive design for mobile and desktop

### Data Architecture
- **SQLite Database**: Device storage, firmware metadata, analytics, community ratings
- **File System Cache**: Firmware binaries with LRU eviction (configurable 1-10GB)
- **Background Processing**: Automated firmware tracking, cache optimization, ML model retraining

## Development Commands

### Building
```bash
# Build the add-on (automatically runs validation)
./scripts/build.sh

# Multi-architecture build for production
./scripts/build.sh --multi-arch

# Frontend development with hot reload
cd rootfs/app/frontend
npm install
npm run dev
```

### Testing and Validation
```bash
# Run full validation (config, Python syntax, TypeScript, Docker)
./scripts/validate.sh

# Type check frontend only
cd rootfs/app/frontend && npm run type-check

# Test Python imports
cd rootfs/app/backend && python3 -c "from app import app"
```

### Development Workflow
```bash
# Start backend development server
cd rootfs/app/backend && python3 app.py

# Frontend development (separate terminal)
cd rootfs/app/frontend && npm run dev

# Full Docker build test
docker build -t tasmota-master .
```

## Key Integration Points

### Service Initialization Flow
Services are initialized in a specific order in `app.py`:
1. Configuration Manager loads HA add-on options
2. Device/MQTT services establish communication layer
3. Firmware management services (manager → cache → community → analytics)
4. Background scheduler starts automated tasks
5. WebSocket callbacks connect real-time updates

### Background Scheduler Tasks
The `BackgroundScheduler` manages 8 critical tasks:
- Firmware update checks (every 2 hours)
- Cache cleanup and optimization (daily)
- Community firmware moderation (hourly)
- ML model retraining (weekly)
- Analytics data aggregation (daily)
- Device health monitoring (every 15 minutes)

### API Patterns
- RESTful API endpoints follow `/api/{service}/{action}` pattern
- WebSocket events for real-time updates (`device_update`, `discovery_status`)
- Async/await patterns for firmware operations
- Error handling with structured JSON responses

## Configuration

### Home Assistant Add-on Config
The add-on integrates deeply with Home Assistant through:
- **Ingress**: Web UI accessible through HA interface on port 8099
- **MQTT Integration**: Pre-configured for `core-mosquitto` add-on
- **Device Access**: USB device mounting for ESP flashing (`/dev/ttyUSB*`, `/dev/ttyACM*`)
- **Privileges**: `NET_ADMIN` for network discovery

### Environment-Specific Behavior
- **Development**: Hot reload, debug logging, separate frontend/backend
- **Production**: Optimized builds, compressed assets, health monitoring
- **Home Assistant**: Ingress panel, configuration through HA UI, integrated logging

## Security Architecture

### Multi-Layer Validation
Community firmware uploads go through comprehensive security scanning:
1. File format validation and magic number checking
2. Binary entropy analysis to detect packed/encrypted payloads
3. Signature verification for known firmware types
4. Size limits and rate limiting
5. Automated moderation pipeline with manual review queue

### Data Protection
- No sensitive data logged or stored in plain text
- Firmware cache uses content-based addressing
- User uploads are sandboxed and scanned before storage