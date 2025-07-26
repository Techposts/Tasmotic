import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages add-on configuration"""
    
    def __init__(self):
        self.config_file = '/data/options.json'
        self.user_config_file = '/opt/app/data/user_config.json'
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from Home Assistant options"""
        config = {}
        
        # Load Home Assistant options
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    ha_config = json.load(f)
                config.update(ha_config)
                logger.info("Loaded Home Assistant configuration")
            except Exception as e:
                logger.error(f"Error loading HA config: {e}")
        
        # Load user configuration
        if os.path.exists(self.user_config_file):
            try:
                with open(self.user_config_file, 'r') as f:
                    user_config = json.load(f)
                config.update(user_config)
                logger.info("Loaded user configuration")
            except Exception as e:
                logger.error(f"Error loading user config: {e}")
        
        # Set defaults
        defaults = {
            'mqtt_host': 'core-mosquitto',
            'mqtt_port': 1883,
            'mqtt_username': '',
            'mqtt_password': '',
            'discovery_prefix': 'homeassistant',
            'device_scan_interval': 30,
            'auto_backup': True,
            'log_level': 'info'
        }
        
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        
        return config
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._config.copy()
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration"""
        self._config.update(updates)
        self._save_user_config()
        logger.info(f"Configuration updated: {list(updates.keys())}")
    
    def _save_user_config(self):
        """Save user configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.user_config_file), exist_ok=True)
            with open(self.user_config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user config: {e}")
    
    def get_mqtt_config(self) -> Dict[str, Any]:
        """Get MQTT configuration"""
        return {
            'host': self.get('mqtt_host'),
            'port': self.get('mqtt_port'),
            'username': self.get('mqtt_username'),
            'password': self.get('mqtt_password'),
            'discovery_prefix': self.get('discovery_prefix')
        }