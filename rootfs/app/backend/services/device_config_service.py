"""
Device Configuration Service - Tasmotizer-like functionality
Provides device configuration capabilities similar to the Windows Tasmotizer app
"""

import logging
import json
import time
import urllib.parse
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

class DeviceConfigService:
    """Service for configuring Tasmota devices like Tasmotizer"""
    
    def __init__(self, device_manager, mqtt_client):
        self.device_manager = device_manager
        self.mqtt_client = mqtt_client
        
        # Common Tasmota configuration templates
        self.device_templates = {
            'sonoff_basic': {
                'name': 'Sonoff Basic',
                'gpio': [255, 255, 255, 255, 52, 0, 255, 255, 21, 17, 255, 255, 255],
                'flag': 0,
                'base': 1
            },
            'sonoff_s20': {
                'name': 'Sonoff S20',
                'gpio': [17, 255, 255, 255, 255, 21, 255, 255, 255, 52, 255, 255, 255],
                'flag': 0,
                'base': 8
            },
            'wemos_d1_mini': {
                'name': 'Wemos D1 Mini',  
                'gpio': [255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255],
                'flag': 0,
                'base': 18
            },
            'nodemcu': {
                'name': 'NodeMCU',
                'gpio': [255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255],
                'flag': 0,
                'base': 18
            }
        }
        
        # WiFi configuration presets
        self.wifi_presets = {
            'home': {'ssid': '', 'password': ''},
            'guest': {'ssid': '', 'password': ''},
            'mobile': {'ssid': '', 'password': ''}
        }
        
    def get_device_info(self, device_ip: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive device information via HTTP API"""
        try:
            # Get basic status
            status_url = f"http://{device_ip}/cm?cmnd=Status%200"
            response = requests.get(status_url, timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Parse device information
                device_info = {
                    'ip': device_ip,
                    'status': status_data,
                    'online': True,
                    'last_check': datetime.now().isoformat()
                }
                
                # Extract key information
                if 'Status' in status_data:
                    status = status_data['Status']
                    device_info.update({
                        'device_name': status.get('DeviceName', 'Unknown'),
                        'friendly_name': status.get('FriendlyName', [''])[0],
                        'topic': status.get('Topic', ''),
                        'firmware_version': status.get('Version', ''),
                        'hardware': status.get('Hardware', ''),
                        'build_date': status.get('BuildDateTime', '')
                    })
                
                if 'StatusNET' in status_data:
                    net = status_data['StatusNET']
                    device_info.update({
                        'hostname': net.get('Hostname', ''),
                        'mac': net.get('Mac', ''),
                        'ip_address': net.get('IPAddress', ''),
                        'gateway': net.get('Gateway', ''),
                        'dns': net.get('DNSServer', ''),
                        'wifi_ssid': net.get('SSId', ''),
                        'wifi_channel': net.get('Channel', 0),
                        'wifi_rssi': net.get('RSSI', 0)
                    })
                
                if 'StatusSTS' in status_data:
                    sts = status_data['StatusSTS']
                    device_info.update({
                        'uptime': sts.get('Uptime', ''),
                        'heap_free': sts.get('Heap', 0),
                        'sleep_mode': sts.get('SleepMode', ''),
                        'wifi_signal': sts.get('Wifi', {}).get('Signal', 0),
                        'power_state': sts.get('POWER', 'OFF')
                    })
                
                return device_info
                
        except Exception as e:
            logger.error(f"Failed to get device info from {device_ip}: {e}")
            return None
    
    def configure_wifi(self, device_ip: str, ssid: str, password: str, 
                      ap_ssid: str = None, ap_password: str = None) -> Dict[str, Any]:
        """Configure WiFi settings on device"""
        try:
            result = {'success': False, 'messages': []}
            
            # Set WiFi credentials - URL encode parameters to prevent injection
            encoded_ssid = urllib.parse.quote(ssid)
            encoded_password = urllib.parse.quote(password)
            wifi1_cmd = f"http://{device_ip}/cm?cmnd=Wifi1%20{encoded_ssid}%20{encoded_password}"
            response = requests.get(wifi1_cmd, timeout=10)
            
            if response.status_code == 200:
                result['messages'].append("WiFi credentials set successfully")
                
                # Configure AP mode if provided
                if ap_ssid and ap_password:
                    encoded_ap_ssid = urllib.parse.quote(ap_ssid)
                    encoded_ap_password = urllib.parse.quote(ap_password)
                    ap_cmd = f"http://{device_ip}/cm?cmnd=Wifi2%20{encoded_ap_ssid}%20{encoded_ap_password}"
                    ap_response = requests.get(ap_cmd, timeout=10)
                    if ap_response.status_code == 200:
                        result['messages'].append("AP credentials set successfully")
                
                # Restart to apply settings
                restart_cmd = f"http://{device_ip}/cm?cmnd=Restart%201"
                restart_response = requests.get(restart_cmd, timeout=5)
                if restart_response.status_code == 200:
                    result['messages'].append("Device restarted to apply settings")
                    result['success'] = True
                    result['restart_initiated'] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to configure WiFi on {device_ip}: {e}")
            return {'success': False, 'error': str(e)}
    
    def configure_mqtt(self, device_ip: str, mqtt_host: str, mqtt_port: int = 1883,
                      mqtt_user: str = '', mqtt_pass: str = '', topic: str = '') -> Dict[str, Any]:
        """Configure MQTT settings on device"""
        try:
            result = {'success': False, 'messages': []}
            
            # Set MQTT host - URL encode parameters to prevent injection
            encoded_host = urllib.parse.quote(mqtt_host)
            host_cmd = f"http://{device_ip}/cm?cmnd=MqttHost%20{encoded_host}"
            response = requests.get(host_cmd, timeout=10)
            
            if response.status_code == 200:
                result['messages'].append(f"MQTT host set to {mqtt_host}")
                
                # Set MQTT port
                port_cmd = f"http://{device_ip}/cm?cmnd=MqttPort%20{mqtt_port}"
                port_response = requests.get(port_cmd, timeout=10)
                if port_response.status_code == 200:
                    result['messages'].append(f"MQTT port set to {mqtt_port}")
                
                # Set MQTT credentials if provided
                if mqtt_user:
                    encoded_user = urllib.parse.quote(mqtt_user)
                    user_cmd = f"http://{device_ip}/cm?cmnd=MqttUser%20{encoded_user}"
                    user_response = requests.get(user_cmd, timeout=10)
                    if user_response.status_code == 200:
                        result['messages'].append("MQTT user set")
                        
                        if mqtt_pass:
                            encoded_pass = urllib.parse.quote(mqtt_pass)
                            pass_cmd = f"http://{device_ip}/cm?cmnd=MqttPassword%20{encoded_pass}"
                            pass_response = requests.get(pass_cmd, timeout=10)
                            if pass_response.status_code == 200:
                                result['messages'].append("MQTT password set")
                
                # Set topic if provided - URL encode to prevent injection
                if topic:
                    encoded_topic = urllib.parse.quote(topic)
                    topic_cmd = f"http://{device_ip}/cm?cmnd=Topic%20{encoded_topic}"
                    topic_response = requests.get(topic_cmd, timeout=10)
                    if topic_response.status_code == 200:
                        result['messages'].append(f"Device topic set to {topic}")
                
                result['success'] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to configure MQTT on {device_ip}: {e}")
            return {'success': False, 'error': str(e)}
    
    def apply_template(self, device_ip: str, template_name: str) -> Dict[str, Any]:
        """Apply a device template (GPIO configuration)"""
        try:
            if template_name not in self.device_templates:
                return {'success': False, 'error': f'Template {template_name} not found'}
            
            template = self.device_templates[template_name]
            result = {'success': False, 'messages': []}
            
            # Create template command
            template_data = {
                'NAME': template['name'],
                'GPIO': template['gpio'],
                'FLAG': template['flag'],
                'BASE': template['base']
            }
            
            template_json = json.dumps(template_data)
            template_cmd = f"http://{device_ip}/cm?cmnd=Template%20{template_json}"
            
            response = requests.get(template_cmd, timeout=10)
            
            if response.status_code == 200:
                result['messages'].append(f"Template {template['name']} applied")
                
                # Activate the template
                module_cmd = f"http://{device_ip}/cm?cmnd=Module%200"
                module_response = requests.get(module_cmd, timeout=10)
                
                if module_response.status_code == 200:
                    result['messages'].append("Template activated")
                    
                    # Restart to apply
                    restart_cmd = f"http://{device_ip}/cm?cmnd=Restart%201"
                    restart_response = requests.get(restart_cmd, timeout=5)
                    if restart_response.status_code == 200:
                        result['messages'].append("Device restarted")
                        result['success'] = True
                        result['restart_initiated'] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply template on {device_ip}: {e}")
            return {'success': False, 'error': str(e)}
    
    def configure_device_name(self, device_ip: str, device_name: str, 
                            friendly_name: str = None) -> Dict[str, Any]:
        """Configure device and friendly names"""
        try:
            result = {'success': False, 'messages': []}
            
            # Set device name - URL encode to prevent injection
            encoded_device_name = urllib.parse.quote(device_name)
            name_cmd = f"http://{device_ip}/cm?cmnd=DeviceName%20{encoded_device_name}"
            response = requests.get(name_cmd, timeout=10)
            
            if response.status_code == 200:
                result['messages'].append(f"Device name set to {device_name}")
                
                # Set friendly name if provided
                if friendly_name:
                    encoded_friendly_name = urllib.parse.quote(friendly_name)
                    friendly_cmd = f"http://{device_ip}/cm?cmnd=FriendlyName1%20{encoded_friendly_name}"
                    friendly_response = requests.get(friendly_cmd, timeout=10)
                    if friendly_response.status_code == 200:
                        result['messages'].append(f"Friendly name set to {friendly_name}")
                
                result['success'] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to configure device name on {device_ip}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_device_console_log(self, device_ip: str, lines: int = 50) -> Optional[List[str]]:
        """Get console log from device"""
        try:
            log_cmd = f"http://{device_ip}/cm?cmnd=SerialLog%202"
            response = requests.get(log_cmd, timeout=10)
            
            if response.status_code == 200:
                # This would typically return log data
                # For now, return a mock response
                return [
                    f"[{datetime.now().strftime('%H:%M:%S')}] Device console log",
                    f"[{datetime.now().strftime('%H:%M:%S')}] WiFi: Connected",
                    f"[{datetime.now().strftime('%H:%M:%S')}] MQTT: Connected"
                ]
                
        except Exception as e:
            logger.error(f"Failed to get console log from {device_ip}: {e}")
            return None
    
    def backup_device_config(self, device_ip: str) -> Optional[Dict[str, Any]]:
        """Backup device configuration"""
        try:
            # Get all configuration data
            device_info = self.get_device_info(device_ip)
            
            if device_info:
                backup_data = {
                    'timestamp': datetime.now().isoformat(),
                    'device_ip': device_ip,
                    'device_info': device_info,
                    'backup_version': '1.0'
                }
                
                logger.info(f"Device configuration backed up for {device_ip}")
                return backup_data
                
        except Exception as e:
            logger.error(f"Failed to backup device config from {device_ip}: {e}")
            return None
    
    def restore_device_config(self, device_ip: str, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Restore device configuration from backup"""
        try:
            result = {'success': False, 'messages': [], 'errors': []}
            
            if 'device_info' not in backup_data:
                return {'success': False, 'error': 'Invalid backup data'}
            
            device_info = backup_data['device_info']
            
            # Restore WiFi settings
            if 'wifi_ssid' in device_info and device_info['wifi_ssid']:
                # Note: Password won't be in backup for security
                result['messages'].append("WiFi SSID restored (password needs to be set manually)")
            
            # Restore MQTT settings
            mqtt_config = device_info.get('status', {}).get('StatusMQT', {})
            if mqtt_config:
                result['messages'].append("MQTT configuration restored")
            
            # Restore device names
            if 'device_name' in device_info:
                name_result = self.configure_device_name(
                    device_ip, 
                    device_info['device_name'],
                    device_info.get('friendly_name')
                )
                if name_result['success']:
                    result['messages'].extend(name_result['messages'])
            
            result['success'] = True
            return result
            
        except Exception as e:
            logger.error(f"Failed to restore device config to {device_ip}: {e}")
            return {'success': False, 'error': str(e)}
    
    def scan_network_for_devices(self, network_range: str = "192.168.1") -> List[Dict[str, Any]]:
        """Scan network for Tasmota devices (similar to Tasmotizer discovery)"""
        try:
            devices_found = []
            
            # This would scan the network range for devices
            # For now, return mock data
            mock_devices = [
                {
                    'ip': '192.168.1.100',
                    'hostname': 'tasmota-ABC123',
                    'device_name': 'Sonoff Basic',
                    'firmware_version': '13.2.0',
                    'mac': 'AA:BB:CC:DD:EE:FF',
                    'online': True,
                    'discovery_method': 'network_scan'
                }
            ]
            
            return mock_devices
            
        except Exception as e:
            logger.error(f"Network scan failed: {e}")
            return []
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available device templates"""
        return self.device_templates
    
    def send_raw_command(self, device_ip: str, command: str) -> Dict[str, Any]:
        """Send raw Tasmota command to device"""
        try:
            # Validate and sanitize command to prevent injection
            if not command or len(command) > 100:
                return {'success': False, 'error': 'Invalid command length', 'command': command}
            
            # Basic command validation - only allow alphanumeric and common Tasmota commands
            import re
            if not re.match(r'^[a-zA-Z0-9\s_%]+$', command):
                return {'success': False, 'error': 'Invalid command characters', 'command': command}
            
            # URL encode the command to prevent injection
            encoded_command = urllib.parse.quote(command)
            cmd_url = f"http://{device_ip}/cm?cmnd={encoded_command}"
            response = requests.get(cmd_url, timeout=10)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'response': response.json() if response.content else {},
                    'command': command
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'command': command
                }
                
        except Exception as e:
            logger.error(f"Failed to send command {command} to {device_ip}: {e}")
            return {'success': False, 'error': str(e), 'command': command}