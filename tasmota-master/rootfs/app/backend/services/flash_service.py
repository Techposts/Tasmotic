import logging
import serial.tools.list_ports
import requests
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FlashService:
    """Service for flashing ESP32/ESP8266 devices with Tasmota firmware"""
    
    def __init__(self):
        self.firmware_cache_dir = '/opt/app/data/firmware'
        self.firmware_urls = {
            'tasmota': 'http://ota.tasmota.com/tasmota/release/',
            'tasmota32': 'http://ota.tasmota.com/tasmota32/release/'
        }
        os.makedirs(self.firmware_cache_dir, exist_ok=True)
    
    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Get list of connected serial devices (ESP32/ESP8266)"""
        devices = []
        
        try:
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                device_info = {
                    'port': port.device,
                    'description': port.description,
                    'hwid': port.hwid,
                    'manufacturer': getattr(port, 'manufacturer', 'Unknown'),
                    'product': getattr(port, 'product', 'Unknown'),
                    'vid': getattr(port, 'vid', None),
                    'pid': getattr(port, 'pid', None)
                }
                
                # Check if it's likely an ESP device
                if self._is_esp_device(port):
                    device_info['likely_esp'] = True
                    device_info['chip_type'] = self._detect_chip_type(port)
                
                devices.append(device_info)
            
            logger.info(f"Found {len(devices)} serial devices")
            return devices
            
        except Exception as e:
            logger.error(f"Error getting connected devices: {e}")
            return []
    
    def _is_esp_device(self, port) -> bool:
        """Check if port is likely an ESP device"""
        # Common ESP device identifiers
        esp_indicators = [
            'cp210x',  # Common USB-to-serial chip
            'ch340',   # Another common chip
            'ftdi',    # FTDI chips
            'esp32',   # Direct ESP32 indicators
            'esp8266',
            'silicon labs',
            'qinheng'
        ]
        
        description_lower = port.description.lower()
        hwid_lower = port.hwid.lower() if port.hwid else ''
        
        return any(indicator in description_lower or indicator in hwid_lower 
                  for indicator in esp_indicators)
    
    def _detect_chip_type(self, port) -> str:
        """Attempt to detect ESP32 vs ESP8266"""
        # This is a basic detection - in a real implementation,
        # you'd use esptool.py to actually query the chip
        description_lower = port.description.lower()
        
        if 'esp32' in description_lower:
            return 'ESP32'
        elif 'esp8266' in description_lower:
            return 'ESP8266'
        else:
            return 'Unknown'
    
    def get_firmware_list(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get available firmware versions"""
        firmware_list = {
            'esp8266': [],
            'esp32': []
        }
        
        try:
            # Get ESP8266 firmware
            esp8266_firmware = self._fetch_firmware_list('tasmota')
            firmware_list['esp8266'] = esp8266_firmware
            
            # Get ESP32 firmware
            esp32_firmware = self._fetch_firmware_list('tasmota32')
            firmware_list['esp32'] = esp32_firmware
            
            logger.info(f"Retrieved firmware list: {len(esp8266_firmware)} ESP8266, {len(esp32_firmware)} ESP32")
            return firmware_list
            
        except Exception as e:
            logger.error(f"Error getting firmware list: {e}")
            return firmware_list
    
    def _fetch_firmware_list(self, platform: str) -> List[Dict[str, Any]]:
        """Fetch firmware list from Tasmota OTA server"""
        try:
            url = self.firmware_urls[platform]
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Parse HTML to extract .bin files
                # This is a simplified implementation
                firmware_files = []
                
                # Common Tasmota firmware variants
                variants = [
                    'tasmota.bin',
                    'tasmota-sensors.bin',
                    'tasmota-lite.bin',
                    'tasmota-minimal.bin',
                    'tasmota-display.bin',
                    'tasmota-ir.bin'
                ]
                
                if platform == 'tasmota32':
                    variants = [f.replace('tasmota', 'tasmota32') for f in variants]
                
                for variant in variants:
                    firmware_files.append({
                        'filename': variant,
                        'url': f"{url}{variant}",
                        'version': 'latest',
                        'description': self._get_firmware_description(variant),
                        'size': 0,  # Would need to fetch to get actual size
                        'features': self._get_firmware_features(variant)
                    })
                
                return firmware_files
            else:
                logger.error(f"Failed to fetch firmware list: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching firmware list for {platform}: {e}")
            return []
    
    def _get_firmware_description(self, filename: str) -> str:
        """Get description for firmware variant"""
        descriptions = {
            'tasmota.bin': 'Standard Tasmota with most features',
            'tasmota32.bin': 'Standard Tasmota32 for ESP32',
            'tasmota-sensors.bin': 'Includes additional sensor support',
            'tasmota32-sensors.bin': 'ESP32 version with sensor support',
            'tasmota-lite.bin': 'Minimal version for low memory devices',
            'tasmota32-lite.bin': 'ESP32 minimal version',
            'tasmota-minimal.bin': 'Bootloader for OTA updates',
            'tasmota32-minimal.bin': 'ESP32 bootloader for OTA',
            'tasmota-display.bin': 'With display support',
            'tasmota32-display.bin': 'ESP32 with display support',
            'tasmota-ir.bin': 'With infrared support',
            'tasmota32-ir.bin': 'ESP32 with infrared support'
        }
        return descriptions.get(filename, 'Tasmota firmware variant')
    
    def _get_firmware_features(self, filename: str) -> List[str]:
        """Get feature list for firmware variant"""
        base_features = ['MQTT', 'HTTP', 'WiFi', 'OTA']
        
        if 'sensors' in filename:
            base_features.extend(['DHT22', 'DS18B20', 'BMP280', 'SHT30'])
        if 'display' in filename:
            base_features.extend(['SSD1306', 'ILI9341', 'SH1106'])
        if 'ir' in filename:
            base_features.extend(['IR Transmit', 'IR Receive'])
        if 'lite' in filename or 'minimal' in filename:
            base_features = ['MQTT', 'WiFi', 'Basic GPIO']
        
        return base_features
    
    def download_firmware(self, firmware_url: str, filename: str) -> str:
        """Download firmware to local cache"""
        try:
            local_path = os.path.join(self.firmware_cache_dir, filename)
            
            # Check if already cached
            if os.path.exists(local_path):
                logger.info(f"Firmware already cached: {filename}")
                return local_path
            
            logger.info(f"Downloading firmware: {firmware_url}")
            response = requests.get(firmware_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded firmware: {filename}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading firmware {filename}: {e}")
            raise
    
    def flash_device(self, port: str, firmware_path: str, chip_type: str = 'auto') -> Dict[str, Any]:
        """Flash device with firmware (placeholder for actual flashing)"""
        try:
            # This would integrate with esptool.py for actual flashing
            # For now, return a mock successful result
            
            result = {
                'success': True,
                'message': f'Successfully flashed {port} with {os.path.basename(firmware_path)}',
                'port': port,
                'firmware': firmware_path,
                'chip_type': chip_type,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Mock flash completed: {port}")
            return result
            
        except Exception as e:
            logger.error(f"Error flashing device {port}: {e}")
            return {
                'success': False,
                'error': str(e),
                'port': port
            }
    
    def get_device_info(self, port: str) -> Optional[Dict[str, Any]]:
        """Get information about connected device"""
        try:
            # This would use esptool.py to query device info
            # For now, return mock data
            
            device_info = {
                'port': port,
                'chip_type': 'ESP32',
                'chip_id': '0x1234567890',
                'flash_size': '4MB',
                'current_firmware': 'Unknown',
                'mac_address': '00:11:22:33:44:55'
            }
            
            return device_info
            
        except Exception as e:
            logger.error(f"Error getting device info for {port}: {e}")
            return None