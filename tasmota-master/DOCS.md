# Tasmota Master Documentation

## Installation

### Via HACS (Recommended)

1. **Add Custom Repository:**
   - Open HACS in Home Assistant
   - Go to "Add-ons" section
   - Click the three dots menu → "Custom repositories"
   - Add repository URL: `https://github.com/yourusername/tasmota-master`
   - Category: "Add-on"
   - Click "Add"

2. **Install Add-on:**
   - Find "Tasmota Master" in the add-on store
   - Click "Install"
   - Wait for installation to complete

3. **Configure:**
   - Go to "Configuration" tab
   - Configure MQTT settings (usually auto-detected)
   - Click "Save"

4. **Start:**
   - Go to "Info" tab
   - Click "Start"
   - Enable "Start on boot" (recommended)

### Manual Installation

1. Copy the `tasmota-master` folder to your Home Assistant `addons` directory
2. Restart Home Assistant
3. Install the add-on from the Supervisor panel

## Configuration

### Basic Configuration

```yaml
mqtt_host: core-mosquitto          # MQTT broker hostname
mqtt_port: 1883                    # MQTT broker port
mqtt_username: ""                  # MQTT username (optional)
mqtt_password: ""                  # MQTT password (optional)
discovery_prefix: homeassistant    # MQTT discovery prefix
device_scan_interval: 30           # Device scan interval in seconds
auto_backup: true                  # Automatic device backup
log_level: info                    # Logging level
```

### Advanced Configuration

```yaml
github_token: ""                   # GitHub token for increased API limits
enable_analytics: true             # Enable analytics features
max_cache_size_gb: 2              # Maximum cache size in GB
community_features: true          # Enable community firmware features
```

## Features

### 🔍 Device Discovery

**Automatic Discovery:**
- mDNS/Zeroconf scanning
- Network IP scanning
- MQTT discovery integration

**Manual Discovery:**
- Add devices by IP address
- Import device configurations
- Bulk device operations

### 📱 Device Management

**Real-time Monitoring:**
- Device status and health
- WiFi signal strength
- Memory usage and uptime
- Power state monitoring

**Device Control:**
- Send commands via MQTT
- Configure device settings
- Restart and reset devices
- Backup device configurations

### 🔧 Firmware Management

**Official Firmware:**
- Automatic tracking of Tasmota releases
- Development and stable channels
- Multi-architecture support (ESP8266/ESP32)
- Smart recommendations based on device

**Community Firmware:**
- Upload custom firmware
- Community ratings and reviews
- Verified firmware badges
- Template sharing

**Web-based Flashing:**
- Flash devices directly from browser
- No software installation required
- Progress tracking and error recovery
- Automatic device detection

### 🤖 AI-Powered Features

**Smart Recommendations:**
- Device compatibility analysis
- Risk assessment for flashing
- Success rate predictions
- Similar device matching

**Analytics:**
- Firmware popularity trends
- Device compatibility insights
- Success rate statistics
- Automated reporting

### 📊 Templates

**Device Templates:**
- Pre-configured device templates
- Visual GPIO configuration
- Template sharing and import
- Community template library

**Template Features:**
- Drag-and-drop GPIO assignment
- Automatic device detection
- One-click template application
- Version management

## Usage Guide

### First-Time Setup

1. **Start the Add-on:**
   - Install and start Tasmota Master
   - Open the Web UI from the add-on info page

2. **Configure MQTT:**
   - MQTT settings are usually auto-detected
   - If using custom MQTT broker, update settings

3. **Discover Devices:**
   - Click "Start Discovery" in the Discovery tab
   - Wait for devices to appear
   - Devices will be added automatically

### Device Management

1. **View Devices:**
   - Go to "Devices" tab to see all discovered devices
   - Click on device for detailed information

2. **Send Commands:**
   - Use the command interface to send MQTT commands
   - Common commands: `Status`, `Restart`, `Reset`

3. **Configure Devices:**
   - Apply templates for quick configuration
   - Modify GPIO settings visually
   - Set up automations and rules

### Firmware Flashing

1. **Select Device:**
   - Connect ESP device via USB to your Home Assistant device
   - Select device from the flashing interface

2. **Choose Firmware:**
   - Browse recommended firmware for your device
   - View firmware details and compatibility
   - Select appropriate variant (sensors, display, etc.)

3. **Flash:**
   - Click "Flash" to start the process
   - Monitor progress in real-time
   - Device will reboot with new firmware

### Community Features

1. **Upload Firmware:**
   - Drag and drop .bin firmware files
   - Add description and metadata
   - Submit for community review

2. **Rate and Review:**
   - Rate firmware based on your experience
   - Leave detailed reviews for other users
   - Report issues or problems

## Troubleshooting

### Common Issues

**MQTT Connection Failed:**
- Verify MQTT broker is running
- Check username/password if authentication enabled
- Ensure MQTT broker allows connections from add-on

**Device Discovery Not Working:**
- Check that devices are on same network
- Verify mDNS is working on your network
- Try manual device addition by IP address

**Flashing Failed:**
- Ensure device is in download mode
- Check USB cable and connections
- Verify correct firmware for device type
- Try different baud rate

**Web UI Not Loading:**
- Check add-on logs for errors
- Restart the add-on
- Clear browser cache
- Try different browser

### Getting Help

1. **Check Logs:**
   - View add-on logs for error messages
   - Enable debug logging for detailed information

2. **Community Support:**
   - Search existing issues on GitHub
   - Join Home Assistant community forums
   - Ask questions in Discord/Reddit

3. **Report Issues:**
   - Create detailed bug reports with logs
   - Include environment information
   - Provide steps to reproduce

## Advanced Usage

### API Access

The add-on provides a REST API for advanced users:

```
GET /api/devices              # List all devices
GET /api/firmware             # List available firmware
POST /api/firmware/upload     # Upload custom firmware
GET /api/analytics            # Get analytics data
```

### Custom Templates

Create custom device templates:

```json
{
  "name": "Custom Device",
  "description": "My custom ESP32 device",
  "gpio": {
    "GPIO2": "Led1",
    "GPIO4": "Button1",
    "GPIO5": "Relay1"
  },
  "rules": [
    "ON Button1#State DO POWER TOGGLE ENDON"
  ]
}
```

### Automation Integration

Use with Home Assistant automations:

```yaml
automation:
  - alias: "Flash firmware when device added"
    trigger:
      platform: webhook
      webhook_id: tasmota_device_added
    action:
      service: rest_command.flash_device
      data:
        device_id: "{{ trigger.json.device_id }}"
        firmware_id: "stable_sensors"
```

## Security

### Best Practices

- Use strong MQTT authentication
- Regularly update firmware
- Review community firmware before use
- Enable automatic backups
- Monitor device access logs

### Network Security

- Use VLANs to isolate IoT devices
- Enable WPA3 on WiFi networks
- Regular security updates
- Monitor unusual network activity

## Performance Optimization

### Cache Management

- Adjust cache size based on available storage
- Enable automatic cache cleanup
- Pre-cache popular firmware versions

### Network Optimization

- Use wired connection for Home Assistant
- Optimize WiFi channel selection
- Consider mesh networks for better coverage

### Resource Usage

- Monitor add-on resource usage
- Adjust scan intervals based on device count
- Use selective discovery for large networks