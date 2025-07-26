# Changelog

All notable changes to the Tasmota Master add-on will be documented in this file.

## [1.0.0] - 2025-01-24

### Added
- Initial release of Tasmota Master add-on
- Automatic device discovery via mDNS and network scanning
- Web-based device management interface
- Device template system with built-in templates
- MQTT integration with Home Assistant
- Real-time device monitoring and updates
- Web-based ESP32/ESP8266 flashing capability
- SQLite database for device and template storage
- Material-UI based responsive web interface
- WebSocket support for real-time updates
- Device configuration wizard
- Bulk device operations
- Template creation and management
- Firmware download and caching
- Home Assistant ingress panel integration

### Core Features
- **Device Discovery**: mDNS, network scanning, MQTT discovery
- **Device Management**: Status monitoring, command sending, configuration
- **Template System**: Built-in templates, custom template creation
- **Flashing**: Web-based device flashing with WebSerial API
- **UI**: Modern React-based interface with Material-UI
- **Integration**: Native Home Assistant panel with ingress

### Built-in Templates
- Sonoff Basic R2
- Sonoff S20
- Wemos D1 Mini
- ESP32 DevKit

### API Endpoints
- `/api/health` - Health check
- `/api/config` - Configuration management
- `/api/devices` - Device management
- `/api/discovery` - Device discovery control
- `/api/templates` - Template management
- `/api/flash` - Device flashing

### WebSocket Events
- `device_update` - Real-time device updates
- `device_discovered` - New device discovery notifications
- `discovery_status` - Discovery process status

### Configuration Options
- MQTT broker settings
- Discovery preferences
- Auto-backup settings
- Logging configuration

## [Unreleased]

### Planned Features
- Advanced automation builder
- Plugin system for extensibility
- Cloud template repository
- Enhanced analytics and reporting
- Mobile application
- Multi-language support
- Enterprise features

### Improvements
- Performance optimizations
- Enhanced error handling
- Better device detection algorithms
- Expanded template library
- Advanced configuration options