"""
MQTT Message Validation for Tasmota devices
Provides schema validation for incoming MQTT messages to prevent malicious payloads
"""

import json
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class MQTTMessageValidator:
    """Validates MQTT messages from Tasmota devices"""
    
    # Allowed Tasmota commands and their expected value types
    TASMOTA_COMMANDS = {
        'POWER': {'type': ['str', 'int'], 'values': ['ON', 'OFF', 'TOGGLE', '0', '1']},
        'STATUS': {'type': ['str', 'int'], 'values': ['0', '1', '2', '3', '5', '8', '10', '11']},
        'RESULT': {'type': 'dict', 'max_keys': 50},
        'STATE': {'type': 'dict', 'max_keys': 100},
        'SENSOR': {'type': 'dict', 'max_keys': 50},
        'INFO1': {'type': 'dict', 'max_keys': 20},
        'INFO2': {'type': 'dict', 'max_keys': 20},
        'INFO3': {'type': 'dict', 'max_keys': 20},
        'LWT': {'type': 'str', 'values': ['Online', 'Offline']},
        'UPTIME': {'type': 'str'},
        'Version': {'type': 'str', 'max_length': 50},
        'Hostname': {'type': 'str', 'max_length': 63}  # RFC 1123 limit
    }
    
    # Device name pattern for Tasmota devices
    DEVICE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')
    
    # Topic structure validation
    TOPIC_PATTERNS = {
        'stat': re.compile(r'^stat/[a-zA-Z0-9_-]{1,32}/[A-Z0-9_]{1,20}$'),
        'tele': re.compile(r'^tele/[a-zA-Z0-9_-]{1,32}/[A-Z0-9_]{1,20}$'),
        'cmnd': re.compile(r'^cmnd/[a-zA-Z0-9_-]{1,32}/[A-Z0-9_]{1,20}$'),
        'discovery': re.compile(r'^tasmota/discovery/[A-F0-9]{12}$')
    }
    
    @classmethod
    def validate_topic(cls, topic: str) -> tuple[bool, Optional[str]]:
        """Validate MQTT topic structure"""
        if not topic or len(topic) > 128:
            return False, "Topic too long or empty"
        
        # Check for malicious patterns
        if any(char in topic for char in ['..', '//', '<', '>', '"', "'"]):
            return False, "Topic contains invalid characters"
        
        # Validate against known patterns
        topic_type = topic.split('/')[0] if '/' in topic else ''
        
        if topic_type in ['stat', 'tele', 'cmnd']:
            pattern = cls.TOPIC_PATTERNS.get(topic_type)
            if pattern and not pattern.match(topic):
                return False, f"Invalid {topic_type} topic format"
        elif topic.startswith('tasmota/discovery'):
            if not cls.TOPIC_PATTERNS['discovery'].match(topic):
                return False, "Invalid discovery topic format"
        else:
            return False, f"Unknown topic type: {topic_type}"
        
        return True, None
    
    @classmethod
    def validate_device_name(cls, device_name: str) -> tuple[bool, Optional[str]]:
        """Validate device name format"""
        if not device_name:
            return False, "Device name is empty"
        
        if not cls.DEVICE_NAME_PATTERN.match(device_name):
            return False, "Device name contains invalid characters or is too long"
        
        return True, None
    
    @classmethod
    def validate_payload_size(cls, payload: str) -> tuple[bool, Optional[str]]:
        """Validate payload size to prevent DoS"""
        if len(payload) > 8192:  # 8KB limit for Tasmota messages
            return False, "Payload too large"
        return True, None
    
    @classmethod
    def validate_json_payload(cls, payload: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate and parse JSON payload"""
        try:
            # Check payload size first
            is_valid, error = cls.validate_payload_size(payload)
            if not is_valid:
                return False, error, None
            
            # Parse JSON
            data = json.loads(payload)
            
            # Basic structure validation
            if isinstance(data, dict):
                # Check for excessive nesting
                if cls._get_dict_depth(data) > 5:
                    return False, "JSON payload too deeply nested", None
                
                # Check for too many keys
                if cls._count_dict_keys(data) > 200:
                    return False, "JSON payload has too many keys", None
            
            return True, None, data
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}", None
        except Exception as e:
            logger.warning(f"JSON validation error: {e}")
            return False, "JSON validation failed", None
    
    @classmethod
    def validate_command_payload(cls, command: str, payload_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate command-specific payload data"""
        if command not in cls.TASMOTA_COMMANDS:
            # Allow unknown commands but log them
            logger.info(f"Unknown Tasmota command: {command}")
            return True, None
        
        cmd_rules = cls.TASMOTA_COMMANDS[command]
        
        # Check data type
        expected_type = cmd_rules.get('type')
        if expected_type:
            if isinstance(expected_type, list):
                # Multiple allowed types
                valid_type = False
                for etype in expected_type:
                    if etype == 'str' and isinstance(payload_data, str):
                        valid_type = True
                        break
                    elif etype == 'int' and isinstance(payload_data, int):
                        valid_type = True
                        break
                    elif etype == 'dict' and isinstance(payload_data, dict):
                        valid_type = True
                        break
                
                if not valid_type:
                    return False, f"Invalid data type for {command}"
            else:
                # Single expected type
                if expected_type == 'str' and not isinstance(payload_data, str):
                    return False, f"Expected string for {command}"
                elif expected_type == 'int' and not isinstance(payload_data, int):
                    return False, f"Expected integer for {command}"
                elif expected_type == 'dict' and not isinstance(payload_data, dict):
                    return False, f"Expected dictionary for {command}"
        
        # Check allowed values
        if 'values' in cmd_rules and isinstance(payload_data, (str, int)):
            if str(payload_data) not in cmd_rules['values']:
                return False, f"Invalid value for {command}: {payload_data}"
        
        # Check dictionary constraints
        if isinstance(payload_data, dict):
            max_keys = cmd_rules.get('max_keys', 100)
            if len(payload_data) > max_keys:
                return False, f"Too many keys in {command} payload"
        
        # Check string length
        if isinstance(payload_data, str):
            max_length = cmd_rules.get('max_length', 1000)
            if len(payload_data) > max_length:
                return False, f"String too long for {command}"
        
        return True, None
    
    @classmethod
    def validate_discovery_payload(cls, payload_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate Tasmota discovery message payload"""
        required_fields = ['ip', 'mac']
        
        for field in required_fields:
            if field not in payload_data:
                return False, f"Missing required field: {field}"
        
        # Validate IP address format
        ip = payload_data.get('ip')
        if ip and not cls._is_valid_ip(ip):
            return False, f"Invalid IP address: {ip}"
        
        # Validate MAC address format
        mac = payload_data.get('mac')
        if mac and not cls._is_valid_mac(mac):
            return False, f"Invalid MAC address: {mac}"
        
        # Validate optional fields
        if 'fn' in payload_data:
            friendly_names = payload_data['fn']
            if not isinstance(friendly_names, list) or len(friendly_names) > 4:
                return False, "Invalid friendly names format"
            for fn in friendly_names:
                if not isinstance(fn, str) or len(fn) > 64:
                    return False, "Friendly name too long"
        
        return True, None
    
    @staticmethod
    def _get_dict_depth(d: Dict, depth: int = 0) -> int:
        """Calculate maximum depth of nested dictionary"""
        if not isinstance(d, dict):
            return depth
        return max([MQTTMessageValidator._get_dict_depth(v, depth + 1) 
                   for v in d.values()] + [depth])
    
    @staticmethod
    def _count_dict_keys(d: Dict) -> int:
        """Count total number of keys in nested dictionary"""
        count = len(d)
        for value in d.values():
            if isinstance(value, dict):
                count += MQTTMessageValidator._count_dict_keys(value)
        return count
    
    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Validate IPv4 address format"""
        import ipaddress
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def _is_valid_mac(mac: str) -> bool:
        """Validate MAC address format"""
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(mac_pattern.match(mac))

class MQTTMessageSanitizer:
    """Sanitizes MQTT message data before processing"""
    
    @staticmethod
    def sanitize_device_data(device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize device data from MQTT messages"""
        sanitized = {}
        
        # Allowed fields and their types
        allowed_fields = {
            'name': str,
            'ip': str,
            'mac': str,
            'firmware_version': str,
            'hardware': str,
            'last_seen': str,
            'status': str,
            'uptime': str,
            'wifi_signal': int,
            'power_state': str,
            'free_memory': int,
            'hostname': str,
            'friendly_name': str,
            'topic': str,
            'group_topic': str
        }
        
        for field, expected_type in allowed_fields.items():
            if field in device_data:
                value = device_data[field]
                if isinstance(value, expected_type):
                    # Additional sanitization for strings
                    if expected_type == str:
                        sanitized[field] = str(value)[:200]  # Limit string length
                    else:
                        sanitized[field] = value
        
        # Add timestamp if not present
        if 'last_seen' not in sanitized:
            sanitized['last_seen'] = datetime.now().isoformat()
        
        return sanitized