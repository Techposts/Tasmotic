import json
import logging
import threading
import time
from datetime import datetime
import paho.mqtt.client as mqtt
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class MQTTClient:
    """MQTT client for Tasmota device communication"""
    
    def __init__(self, config_manager, device_manager):
        self.config_manager = config_manager
        self.device_manager = device_manager
        self.client = None
        self.connected = False
        self.running = False
        self.reconnect_thread = None
        
        # MQTT topics
        self.discovery_topic = "tasmota/discovery/+"
        self.stat_topic = "stat/+/+"
        self.tele_topic = "tele/+/+"
        self.cmnd_topic_template = "cmnd/{}/+"
        
    def start(self):
        """Start MQTT client"""
        if self.running:
            return
            
        self.running = True
        self._setup_client()
        self._connect()
        
        # Start reconnection thread
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop)
        self.reconnect_thread.daemon = True
        self.reconnect_thread.start()
        
        logger.info("MQTT client started")
    
    def stop(self):
        """Stop MQTT client"""
        self.running = False
        if self.client:
            self.client.disconnect()
            self.client.loop_stop()
        logger.info("MQTT client stopped")
    
    def _setup_client(self):
        """Setup MQTT client with security and callbacks"""
        config = self.config_manager.get_mqtt_config()
        
        # Use MQTT v3.1.1 for better security
        self.client = mqtt.Client(protocol=mqtt.MQTTv311)
        
        # Set credentials if provided
        if config.get('username') and config.get('password'):
            self.client.username_pw_set(config['username'], config['password'])
            logger.info("MQTT authentication configured")
        else:
            logger.warning("MQTT running without authentication - consider adding credentials")
        
        # Configure TLS if enabled
        if config.get('use_tls', False):
            self.client.tls_set()
            logger.info("MQTT TLS encryption enabled")
        
        # Set security options
        self.client.max_inflight_messages_set(20)  # Limit concurrent messages
        self.client.max_queued_messages_set(100)   # Limit queued messages
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_log = self._on_log
        
        # Enable logging
        self.client.enable_logger(logger)
    
    def _connect(self):
        """Connect to MQTT broker"""
        try:
            config = self.config_manager.get_mqtt_config()
            self.client.connect(config['host'], config['port'], 60)
            self.client.loop_start()
            logger.info(f"Connecting to MQTT broker: {config['host']}:{config['port']}")
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for successful MQTT connection"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected successfully")
            
            # Subscribe to Tasmota topics
            topics = [
                (self.discovery_topic, 0),
                (self.stat_topic, 0),
                (self.tele_topic, 0),
                ("tasmota/+/+", 0)  # Catch-all for Tasmota messages
            ]
            
            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"Subscribed to: {topic}")
                
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.connected = False
        if rc != 0:
            logger.warning("MQTT disconnected unexpectedly")
        else:
            logger.info("MQTT disconnected")
    
    def _on_log(self, client, userdata, level, buf):
        """Callback for MQTT logging"""
        # Filter out noisy logs and potential sensitive information
        if any(sensitive in buf.lower() for sensitive in ['password', 'secret', 'key', 'token']):
            logger.debug("MQTT log message filtered (contains sensitive data)")
            return
        
        if level == mqtt.MQTT_LOG_ERR:
            logger.error(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            logger.warning(f"MQTT: {buf}")
        else:
            logger.debug(f"MQTT: {buf}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for received MQTT messages with validation"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Import validator
            from utils.mqtt_validator import MQTTMessageValidator, MQTTMessageSanitizer
            
            # Validate topic format
            is_valid_topic, topic_error = MQTTMessageValidator.validate_topic(topic)
            if not is_valid_topic:
                logger.warning(f"Invalid MQTT topic rejected: {topic} - {topic_error}")
                return
            
            # Validate payload size
            is_valid_size, size_error = MQTTMessageValidator.validate_payload_size(payload)
            if not is_valid_size:
                logger.warning(f"MQTT payload too large rejected: {topic} - {size_error}")
                return
            
            logger.debug(f"MQTT message: {topic} -> {payload[:200]}{'...' if len(payload) > 200 else ''}")
            
            # Parse topic parts
            topic_parts = topic.split('/')
            
            if len(topic_parts) < 3:
                logger.warning(f"MQTT topic has insufficient parts: {topic}")
                return
            
            message_type = topic_parts[0]  # stat, tele, cmnd
            device_name = topic_parts[1]
            command = topic_parts[2]
            
            # Validate device name
            is_valid_device, device_error = MQTTMessageValidator.validate_device_name(device_name)
            if not is_valid_device:
                logger.warning(f"Invalid device name rejected: {device_name} - {device_error}")
                return
            
            # Handle different message types with validation
            if message_type == "stat":
                self._handle_stat_message(device_name, command, payload)
            elif message_type == "tele":
                self._handle_tele_message(device_name, command, payload)
            elif topic.startswith("tasmota/discovery"):
                self._handle_discovery_message(payload)
            else:
                logger.warning(f"Unknown MQTT message type: {message_type}")
                
        except UnicodeDecodeError:
            logger.warning(f"MQTT message with invalid UTF-8 encoding rejected: {topic}")
        except Exception as e:
            logger.error(f"MQTT message processing error: {e}", exc_info=True)
    
    def _handle_stat_message(self, device_name: str, command: str, payload: str):
        """Handle status messages from devices with validation"""
        try:
            from utils.mqtt_validator import MQTTMessageValidator, MQTTMessageSanitizer
            
            # Validate and parse JSON payload
            is_valid, error, data = MQTTMessageValidator.validate_json_payload(payload)
            if not is_valid:
                logger.warning(f"Invalid JSON in stat message from {device_name}: {error}")
                return
            
            # Validate command-specific payload
            is_valid_cmd, cmd_error = MQTTMessageValidator.validate_command_payload(command, data)
            if not is_valid_cmd:
                logger.warning(f"Invalid command payload from {device_name}: {cmd_error}")
                return
            
            if command == "STATUS":
                # Device status information
                self._process_device_status(device_name, data)
            elif command == "RESULT":
                # Command results - sanitize before logging
                sanitized_data = {k: str(v)[:100] for k, v in data.items() if isinstance(k, str)}
                logger.info(f"Command result from {device_name}: {sanitized_data}")
                
        except Exception as e:
            logger.warning(f"Error processing stat message from {device_name}: {e}")
    
    def _handle_tele_message(self, device_name: str, command: str, payload: str):
        """Handle telemetry messages from devices with validation"""
        try:
            from utils.mqtt_validator import MQTTMessageValidator, MQTTMessageSanitizer
            
            # Validate and parse JSON payload
            is_valid, error, data = MQTTMessageValidator.validate_json_payload(payload)
            if not is_valid:
                logger.warning(f"Invalid JSON in tele message from {device_name}: {error}")
                return
            
            # Validate command-specific payload
            is_valid_cmd, cmd_error = MQTTMessageValidator.validate_command_payload(command, data)
            if not is_valid_cmd:
                logger.warning(f"Invalid telemetry payload from {device_name}: {cmd_error}")
                return
            
            if command == "STATE":
                # Device telemetry state
                self._process_device_telemetry(device_name, data)
            elif command == "SENSOR":
                # Sensor data
                self._process_sensor_data(device_name, data)
            elif command in ["INFO1", "INFO2", "INFO3"]:
                # Device information
                self._process_device_info(device_name, data)
                
        except Exception as e:
            logger.warning(f"Error processing tele message from {device_name}: {e}")
    
    def _handle_discovery_message(self, payload: str):
        """Handle Tasmota discovery messages with validation"""
        try:
            from utils.mqtt_validator import MQTTMessageValidator, MQTTMessageSanitizer
            
            # Validate and parse JSON payload
            is_valid, error, data = MQTTMessageValidator.validate_json_payload(payload)
            if not is_valid:
                logger.warning(f"Invalid JSON in discovery message: {error}")
                return
            
            # Validate discovery-specific payload
            is_valid_discovery, discovery_error = MQTTMessageValidator.validate_discovery_payload(data)
            if not is_valid_discovery:
                logger.warning(f"Invalid discovery payload: {discovery_error}")
                return
            
            logger.info(f"Valid discovery message received from {data.get('ip', 'unknown')}")
            
            # Extract and sanitize device information
            device_data = {
                'name': data.get('fn', [None])[0] if data.get('fn') else 'Unknown',
                'ip': data.get('ip'),
                'mac': data.get('mac'),
                'firmware_version': data.get('sw', '')[:50],  # Limit version string
                'hardware': data.get('md', '')[:50],  # Limit hardware string
                'last_seen': datetime.now().isoformat(),
                'status': 'online',
                'discovery_method': 'mqtt'
            }
            
            # Sanitize device data before adding
            sanitized_device_data = MQTTMessageSanitizer.sanitize_device_data(device_data)
            
            # Add device to manager
            self.device_manager.add_device(sanitized_device_data)
            
        except Exception as e:
            logger.warning(f"Error processing discovery message: {e}")
    
    def _process_device_status(self, device_name: str, data: Dict[str, Any]):
        """Process device status data"""
        status_data = {
            'status': 'online',
            'last_seen': datetime.now().isoformat()
        }
        
        # Extract relevant status information
        if 'StatusSTS' in data:
            sts = data['StatusSTS']
            status_data.update({
                'uptime': sts.get('Uptime'),
                'wifi_signal': sts.get('Wifi', {}).get('RSSI'),
                'power_state': sts.get('POWER')
            })
        
        # Update device in manager
        device_id = device_name.replace('-', '').replace('_', '')
        self.device_manager.update_device_status(device_id, status_data)
    
    def _process_device_telemetry(self, device_name: str, data: Dict[str, Any]):
        """Process device telemetry data"""
        telemetry_data = {
            'status': 'online',
            'last_seen': datetime.now().isoformat(),
            'uptime': data.get('Uptime'),
            'free_memory': data.get('Heap'),
            'wifi_signal': data.get('Wifi', {}).get('RSSI'),
            'power_state': data.get('POWER')
        }
        
        # Update device in manager
        device_id = device_name.replace('-', '').replace('_', '')
        self.device_manager.update_device_status(device_id, telemetry_data)
    
    def _process_sensor_data(self, device_name: str, data: Dict[str, Any]):
        """Process sensor data from device"""
        logger.info(f"Sensor data from {device_name}: {data}")
        # This can be extended to handle specific sensor types
    
    def _process_device_info(self, device_name: str, data: Dict[str, Any]):
        """Process device information"""
        logger.info(f"Device info from {device_name}: {data}")
        # This can be extended to handle device info updates
    
    def send_command(self, device_name: str, command: str, payload: str = ""):
        """Send command to device with security validation"""
        if not self.connected:
            raise Exception("MQTT not connected")
        
        from utils.mqtt_validator import MQTTMessageValidator
        
        # Validate device name
        is_valid_device, device_error = MQTTMessageValidator.validate_device_name(device_name)
        if not is_valid_device:
            logger.warning(f"Invalid device name for command: {device_name} - {device_error}")
            raise ValueError(f"Invalid device name: {device_error}")
        
        # Validate command format
        if not command or not isinstance(command, str) or len(command) > 20:
            logger.warning(f"Invalid command format: {command}")
            raise ValueError("Invalid command format")
        
        # Validate payload size
        is_valid_size, size_error = MQTTMessageValidator.validate_payload_size(payload)
        if not is_valid_size:
            logger.warning(f"Command payload too large: {size_error}")
            raise ValueError(f"Payload error: {size_error}")
        
        topic = f"cmnd/{device_name}/{command}"
        
        # Final topic validation
        is_valid_topic, topic_error = MQTTMessageValidator.validate_topic(topic)
        if not is_valid_topic:
            logger.warning(f"Invalid command topic: {topic} - {topic_error}")
            raise ValueError(f"Topic error: {topic_error}")
        
        try:
            result = self.client.publish(topic, payload, qos=1)  # Use QoS 1 for reliability
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Sent command: {topic} -> {payload[:50]}{'...' if len(payload) > 50 else ''}")
                return True
            else:
                logger.error(f"Failed to publish command: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def request_device_status(self, device_name: str):
        """Request status from device"""
        commands = ['STATUS', 'STATUS1', 'STATUS2', 'STATUS5']
        for cmd in commands:
            self.send_command(device_name, cmd)
    
    def is_connected(self) -> bool:
        """Check if MQTT client is connected"""
        return self.connected
    
    def _reconnect_loop(self):
        """Background thread for handling reconnections"""
        while self.running:
            if not self.connected:
                logger.info("Attempting to reconnect to MQTT...")
                try:
                    self._connect()
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")
            
            time.sleep(30)  # Check every 30 seconds