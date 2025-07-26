# Tasmota Master - Home Assistant Add-on

A comprehensive Tasmota device management suite for Home Assistant with beautiful UI and advanced features.

## Features

### 🎯 Core Features
- **Automatic Device Discovery** - Find Tasmota devices via mDNS and network scanning
- **Web-based Device Management** - Control and configure devices through intuitive interface
- **Template System** - Visual device template creation and management
- **Bulk Operations** - Manage multiple devices simultaneously
- **Real-time Monitoring** - Live device status and performance metrics

### 🔧 Advanced Features
- **Web-based Flashing** - Flash ESP32/ESP8266 devices directly from browser
- **MQTT Integration** - Seamless integration with Home Assistant MQTT
- **Device Templates** - Pre-configured templates for popular devices
- **Configuration Wizard** - Guided setup for new devices
- **Backup & Restore** - Device configuration backup and restoration

### 🎨 User Experience
- **Modern UI** - Clean, responsive Material Design interface
- **Real-time Updates** - WebSocket-based live updates
- **Mobile Friendly** - Optimized for mobile and tablet use
- **Home Assistant Integration** - Native panel integration with ingress

## Installation

### Via HACS (Recommended)
1. Add this repository to HACS custom repositories
2. Install "Tasmota Master" add-on
3. Configure and start the add-on

### Manual Installation
1. Copy the `tasmota-master` folder to your Home Assistant add-ons directory
2. Restart Home Assistant
3. Install the add-on from the Supervisor panel

## Configuration

### Basic Configuration
```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_username: ""
mqtt_password: ""
discovery_prefix: homeassistant
device_scan_interval: 30
auto_backup: true
log_level: info
```

### MQTT Setup
The add-on works with any MQTT broker, but is pre-configured for the official Mosquitto add-on:

1. Install and configure the Mosquitto broker add-on
2. Create a Home Assistant user for MQTT
3. Configure the credentials in the add-on options

## Usage

### Device Discovery
1. Open the Tasmota Master panel in Home Assistant
2. Go to Discovery tab
3. Click "Start Discovery" to scan for devices
4. Devices will appear automatically as they're found

### Device Management
1. View all devices in the Dashboard
2. Click on any device to view details
3. Send commands, update firmware, or apply templates
4. Monitor real-time status and performance

### Templates
1. Browse built-in templates in the Templates tab
2. Apply templates to devices with one click
3. Create custom templates for your devices
4. Share templates with the community

### Flashing
1. Connect ESP device via USB
2. Go to Flashing tab
3. Select device and firmware
4. Click Flash to install Tasmota

## Architecture

### Backend Services
- **Flask API** - REST API for device management
- **MQTT Client** - Device communication via MQTT
- **Device Discovery** - mDNS and network scanning
- **Template Manager** - Device template system
- **Flash Service** - ESP device flashing

### Frontend
- **React + TypeScript** - Modern web application
- **Material-UI** - Beautiful, responsive design
- **Socket.IO** - Real-time updates
- **WebSerial API** - Browser-based device flashing

### Database
- **SQLite** - Device storage and templates
- **File Storage** - Firmware cache and backups

## Development

### Prerequisites
- Home Assistant OS or Supervised
- Docker environment
- Node.js (for frontend development)

### Building
```bash
# Build the add-on
docker build -t tasmota-master .

# Development with hot reload
cd rootfs/app/frontend
npm install
npm run dev
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

### Common Issues
- **MQTT Connection**: Ensure MQTT broker is running and credentials are correct
- **Device Discovery**: Check network connectivity and firewall settings
- **Flashing Issues**: Verify USB device permissions and WebSerial support

### Getting Help
- Check the troubleshooting guide
- Post in Home Assistant Community forum
- Report bugs on GitHub

## Roadmap

### Phase 1 (Current)
- [x] Basic device discovery and management
- [x] Template system
- [x] Web interface
- [x] MQTT integration

### Phase 2 (Next)
- [ ] Advanced automation builder
- [ ] Plugin system
- [ ] Cloud template repository
- [ ] Mobile app

### Phase 3 (Future)
- [ ] Machine learning device classification
- [ ] Advanced analytics
- [ ] Multi-language support
- [ ] Enterprise features

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Tasmota project for the amazing firmware
- Home Assistant community for inspiration
- All contributors and testers