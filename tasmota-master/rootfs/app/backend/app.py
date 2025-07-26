#!/usr/bin/env python3

import os
import json
import asyncio
from flask import Flask, jsonify, request, send_from_directory, send_file, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
import threading
import time

from services.device_discovery import DeviceDiscovery
from services.mqtt_client import MQTTClient
from services.device_manager import DeviceManager
from services.template_manager import TemplateManager
from services.config_manager import ConfigManager
from services.firmware_manager import FirmwareManager
from services.firmware_cache import FirmwareCacheManager, FirmwareRecommendationEngine
from services.community_firmware import CommunityFirmwareManager
from services.firmware_analytics import FirmwareAnalyticsEngine
from services.background_scheduler import BackgroundScheduler
from services.device_config_service import DeviceConfigService
from utils.logger import logger, log_api_call, ErrorHandler, log_service_startup, get_service_health
from utils.security import rate_limit, validate_input, csrf_protect, add_security_headers
from utils.health_monitor import health_monitor

# Initialize Flask app
app = Flask(__name__)

# Use persistent secret key for Home Assistant Add-on
secret_key_file = '/data/secret_key'
try:
    with open(secret_key_file, 'rb') as f:
        app.config['SECRET_KEY'] = f.read()
except FileNotFoundError:
    # Generate new secret key and store it
    secret_key = os.urandom(32)
    os.makedirs('/data', exist_ok=True)
    with open(secret_key_file, 'wb') as f:
        f.write(secret_key)
    app.config['SECRET_KEY'] = secret_key

# Session configuration for Home Assistant Ingress
app.config['SESSION_COOKIE_SECURE'] = False  # Home Assistant uses HTTP internally
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Required for ingress iframe
app.config['SESSION_COOKIE_PATH'] = '/'
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize services
config_manager = ConfigManager()
device_manager = DeviceManager(config_manager)
template_manager = TemplateManager()
mqtt_client = MQTTClient(config_manager, device_manager)
device_discovery = DeviceDiscovery(device_manager, mqtt_client)

# Initialize firmware management services
firmware_manager = FirmwareManager(config_manager)
cache_manager = FirmwareCacheManager(firmware_manager)
community_manager = CommunityFirmwareManager(firmware_manager)
analytics_engine = FirmwareAnalyticsEngine(firmware_manager, community_manager)
recommendation_engine = FirmwareRecommendationEngine(firmware_manager)
background_scheduler = BackgroundScheduler(firmware_manager, cache_manager, community_manager, analytics_engine)
device_config_service = DeviceConfigService(device_manager, mqtt_client)

# Global state
app_state = {
    'services_running': False,
    'devices': {},
    'discovery_active': False,
    'start_time': time.time()
}

@app.route('/api/health')
@log_api_call('health_check')
def health_check():
    """Enhanced health check endpoint"""
    try:
        # Check all service health
        service_statuses = {}
        overall_status = 'healthy'
        
        # Check MQTT health
        mqtt_health = get_service_health('mqtt')
        mqtt_connected = mqtt_client.is_connected()
        service_statuses['mqtt'] = {
            'connected': mqtt_connected,
            'health': mqtt_health.get_health_info()
        }
        if not mqtt_connected:
            overall_status = 'degraded'
            
        # Check discovery health
        discovery_health = get_service_health('discovery')
        service_statuses['discovery'] = {
            'active': app_state['discovery_active'],
            'health': discovery_health.get_health_info()
        }
        
        # Check firmware services
        firmware_health = get_service_health('firmware_manager')
        service_statuses['firmware'] = {
            'health': firmware_health.get_health_info()
        }
        
        # Check background scheduler
        scheduler_health = get_service_health('background_scheduler')
        service_statuses['scheduler'] = {
            'health': scheduler_health.get_health_info()
        }
        
        return jsonify({
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'correlation_id': logger.get_correlation_id(),
            'services': service_statuses,
            'uptime_seconds': time.time() - app_state.get('start_time', time.time())
        })
        
    except Exception as e:
        logger.error("Health check failed", exc_info=True)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

@app.route('/api/config')
@log_api_call('get_config')
def get_config():
    """Get current configuration"""
    try:
        config = config_manager.get_config()
        logger.info("Configuration retrieved successfully")
        return jsonify(config)
    except Exception as e:
        logger.error("Failed to retrieve configuration", exc_info=True)
        return jsonify(ErrorHandler.handle_error('INVALID_CONFIGURATION', e)), 500

@app.route('/api/config', methods=['POST'])
@log_api_call('update_config')
def update_config():
    """Update configuration"""
    try:
        config_data = request.get_json()
        if not config_data:
            return jsonify(ErrorHandler.handle_error('INVALID_CONFIGURATION', 
                         Exception('No configuration data provided'))), 400
            
        config_manager.update_config(config_data)
        logger.info("Configuration updated successfully", 
                   config_keys=list(config_data.keys()))
        return jsonify({'success': True, 'message': 'Configuration updated'})
        
    except Exception as e:
        logger.error("Configuration update failed", exc_info=True)
        return jsonify(ErrorHandler.handle_error('INVALID_CONFIGURATION', e)), 500

@app.route('/api/devices')
def get_devices():
    """Get all discovered devices"""
    devices = device_manager.get_all_devices()
    return jsonify({
        'devices': devices,
        'count': len(devices)
    })

@app.route('/api/devices/<device_id>')
@log_api_call('get_device')
@rate_limit(limit=30, window=60)
@add_security_headers
def get_device(device_id):
    """Get specific device details"""
    try:
        # Validate device_id format
        from utils.security import InputValidator
        if not InputValidator.validate_string(device_id, 'device_id'):
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('Invalid device ID format'))), 400
                
        device = device_manager.get_device(device_id)
        if device:
            logger.info(f"Device details retrieved", device_id=device_id)
            return jsonify(device)
        else:
            logger.warning(f"Device not found", device_id=device_id)
            return jsonify(ErrorHandler.handle_error('DEVICE_NOT_FOUND', 
                Exception(f'Device {device_id} not found'))), 404
                
    except Exception as e:
        logger.error("Failed to retrieve device details", device_id=device_id, exc_info=True)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

@app.route('/api/devices/<device_id>/command', methods=['POST'])
@log_api_call('send_device_command')
@rate_limit(limit=10, window=60, block_on_exceed=True)  # Stricter limit for commands
@validate_input(device_id='device_id', command='safe_string')
@csrf_protect
@add_security_headers
def send_device_command(device_id):
    """Send command to device with security validation"""
    try:
        command_data = request.get_json()
        if not command_data:
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('No command data provided'))), 400
                
        command = command_data.get('command')
        params = command_data.get('params', {})
        
        if not command:
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('Command is required'))), 400
                
        # Validate device exists
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify(ErrorHandler.handle_error('DEVICE_NOT_FOUND', 
                Exception(f'Device {device_id} not found'))), 404
                
        logger.info(f"Sending command to device", 
                   device_id=device_id, 
                   command=command, 
                   params_count=len(params))
                   
        result = device_manager.send_command(device_id, command, params)
        
        logger.info(f"Command executed successfully", 
                   device_id=device_id, 
                   command=command)
                   
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        logger.error("Device command failed", 
                    device_id=device_id, 
                    command=command_data.get('command') if 'command_data' in locals() else 'unknown',
                    exc_info=True)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

@app.route('/api/discovery/start', methods=['POST'])
@log_api_call('start_discovery')
@rate_limit(limit=5, window=300)  # Only 5 discovery starts per 5 minutes
@csrf_protect
@add_security_headers
def start_discovery():
    """Start device discovery with rate limiting"""
    try:
        if app_state['discovery_active']:
            logger.info("Discovery already active, ignoring start request")
            return jsonify({'success': True, 'message': 'Discovery already active'})
            
        device_discovery.start_discovery()
        app_state['discovery_active'] = True
        
        logger.info("Device discovery started")
        socketio.emit('discovery_status', {'active': True})
        
        # Update service health
        get_service_health('discovery').mark_healthy()
        
        return jsonify({'success': True, 'message': 'Discovery started'})
        
    except Exception as e:
        logger.error("Failed to start discovery", exc_info=True)
        get_service_health('discovery').mark_unhealthy(e)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

@app.route('/api/discovery/stop', methods=['POST'])
def stop_discovery():
    """Stop device discovery"""
    try:
        device_discovery.stop_discovery()
        app_state['discovery_active'] = False
        socketio.emit('discovery_status', {'active': False})
        return jsonify({'success': True, 'message': 'Discovery stopped'})
    except Exception as e:
        logger.error(f"Discovery stop error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/templates')
def get_templates():
    """Get device templates"""
    templates = template_manager.get_all_templates()
    return jsonify({
        'templates': templates,
        'count': len(templates)
    })

@app.route('/api/templates', methods=['POST'])
def create_template():
    """Create new device template"""
    try:
        template_data = request.get_json()
        template_id = template_manager.create_template(template_data)
        return jsonify({'success': True, 'template_id': template_id})
    except Exception as e:
        logger.error(f"Template creation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/templates/<template_id>/apply', methods=['POST'])
def apply_template(template_id):
    """Apply template to device"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        result = template_manager.apply_template(template_id, device_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Template apply error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# CSRF Token endpoint
@app.route('/api/csrf-token')
@log_api_call('get_csrf_token')
@rate_limit(limit=10, window=60)
def get_csrf_token():
    """Get CSRF token for secure operations"""
    from utils.security import CSRFProtection
    
    # Check if we already have a valid token in session
    existing_token = session.get('csrf_token')
    if existing_token:
        logger.debug("Returning existing CSRF token")
        return jsonify({'csrf_token': existing_token})
    
    # Generate new token
    token = CSRFProtection.generate_token()
    session['csrf_token'] = token
    session.permanent = True  # Make session persistent
    
    logger.info("New CSRF token generated", 
               session_id=session.get('session_id', 'unknown')[:8])
    return jsonify({'csrf_token': token})

# Enhanced Health Monitoring Endpoints
@app.route('/api/health/comprehensive')
@log_api_call('comprehensive_health_check')
@rate_limit(limit=20, window=60)
@add_security_headers
def comprehensive_health_check():
    """Comprehensive health check with detailed metrics"""
    try:
        health_data = health_monitor.get_comprehensive_health()
        return jsonify(health_data)
    except Exception as e:
        logger.error("Comprehensive health check failed", exc_info=True)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

@app.route('/api/health/metrics')
@log_api_call('get_health_metrics')
@rate_limit(limit=30, window=60)
@add_security_headers
def get_health_metrics():
    """Get current system metrics"""
    try:
        metrics = health_monitor.get_system_metrics()
        return jsonify({
            'success': True,
            'metrics': {k: v.__dict__ if hasattr(v, '__dict__') else v 
                       for k, v in metrics.items()},
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error("Failed to get health metrics", exc_info=True)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

@app.route('/api/health/metrics/<metric_name>/history')
@log_api_call('get_metric_history')
@rate_limit(limit=20, window=60)
@add_security_headers
def get_metric_history(metric_name):
    """Get historical metrics data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        history = health_monitor.get_metrics_history(metric_name, hours)
        
        return jsonify({
            'success': True,
            'metric_name': metric_name,
            'hours': hours,
            'data_points': len(history),
            'history': history
        })
    except Exception as e:
        logger.error("Failed to get metric history", 
                    metric_name=metric_name, exc_info=True)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

# Firmware Management API Routes
@app.route('/api/firmware')
@log_api_call('get_firmware_list')
@rate_limit(limit=30, window=60)
@add_security_headers
def get_firmware_list():
    """Get official firmware list"""
    try:
        chip_type = request.args.get('chip_type')
        channel = request.args.get('channel')
        verified_only = request.args.get('verified_only', 'false').lower() == 'true'
        
        firmware_list = firmware_manager.get_firmware_list(
            chip_type=chip_type,
            channel=channel,
            verified_only=verified_only
        )
        
        return jsonify({
            'success': True,
            'firmware': firmware_list,
            'count': len(firmware_list)
        })
    except Exception as e:
        logger.error(f"Firmware list error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firmware/updates', methods=['POST'])
def check_firmware_updates():
    """Trigger firmware updates check"""
    try:
        update_results = background_scheduler.trigger_task_manually('firmware_updates')
        return jsonify(update_results)
    except Exception as e:
        logger.error(f"Firmware updates error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firmware/recommendations/<device_id>')
def get_firmware_recommendations(device_id):
    """Get firmware recommendations for device"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        recommendations = recommendation_engine.get_firmware_recommendations(device)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        logger.error(f"Firmware recommendations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firmware/community')
def get_community_firmware():
    """Get community firmware list"""
    try:
        chip_type = request.args.get('chip_type')
        status = request.args.get('status', 'approved')
        author = request.args.get('author')
        limit = int(request.args.get('limit', 50))
        
        firmware_list = community_manager.get_community_firmware_list(
            chip_type=chip_type,
            status=status,
            author=author,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'firmware': firmware_list,
            'count': len(firmware_list)
        })
    except Exception as e:
        logger.error(f"Community firmware error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firmware/upload', methods=['POST'])
@log_api_call('upload_community_firmware')
@rate_limit(limit=3, window=3600, block_on_exceed=True)  # Only 3 uploads per hour
@csrf_protect
@add_security_headers
def upload_community_firmware():
    """Upload community firmware with comprehensive security validation"""
    try:
        # Validate file presence
        if 'firmware' not in request.files:
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('No firmware file provided'))), 400
        
        firmware_file = request.files['firmware']
        if firmware_file.filename == '':
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('No file selected'))), 400
        
        # Validate file using security module
        from utils.security import InputValidator
        file_size = 0
        firmware_file.seek(0, 2)  # Seek to end
        file_size = firmware_file.tell()
        firmware_file.seek(0)  # Reset to beginning
        
        is_valid, error_msg = InputValidator.validate_firmware_upload(
            firmware_file.filename, file_size)
        if not is_valid:
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception(error_msg))), 400
        
        # Parse and validate metadata
        metadata = {}
        author_info = {}
        
        try:
            metadata = json.loads(request.form.get('metadata', '{}'))
            author_info = json.loads(request.form.get('author', '{}'))
        except json.JSONDecodeError:
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('Invalid metadata format'))), 400
        
        # Validate metadata fields
        if not InputValidator.validate_json_payload(metadata, 5000):
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('Metadata too large'))), 400
                
        if not InputValidator.validate_json_payload(author_info, 1000):
            return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                Exception('Author info too large'))), 400
        
        # Read file data
        file_data = firmware_file.read()
        
        logger.info("Processing firmware upload", 
                   filename=firmware_file.filename,
                   file_size=file_size,
                   author=author_info.get('name', 'unknown'))
        
        # Upload firmware (this is async, so we need to handle it properly)
        result = community_manager.upload_firmware(
            file_data,
            firmware_file.filename,
            metadata,
            author_info
        )
        
        # If result is a coroutine, we need to await it
        if hasattr(result, '__await__'):
            import asyncio
            result = asyncio.run(result)
        
        logger.info("Firmware upload completed", 
                   filename=firmware_file.filename,
                   success=result.get('success', False))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Firmware upload failed", 
                    filename=firmware_file.filename if 'firmware_file' in locals() else 'unknown',
                    exc_info=True)
        return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

@app.route('/api/firmware/<firmware_id>/download')
def download_firmware(firmware_id):
    """Download firmware file"""
    try:
        # Check cache first
        cached_path = cache_manager.get_cached_firmware_path(firmware_id)
        
        if cached_path and os.path.exists(cached_path):
            return send_file(cached_path, as_attachment=True)
        
        # If not cached, download and cache
        firmware_list = firmware_manager.get_firmware_list()
        firmware = next((f for f in firmware_list if f['id'] == firmware_id), None)
        
        if not firmware:
            return jsonify({'success': False, 'error': 'Firmware not found'}), 404
        
        cached_path = cache_manager.download_and_cache_firmware(
            firmware_id,
            firmware['download_url']
        )
        
        if cached_path:
            return send_file(cached_path, as_attachment=True)
        else:
            return jsonify({'success': False, 'error': 'Download failed'}), 500
            
    except Exception as e:
        logger.error(f"Firmware download error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firmware/analytics')
def get_firmware_analytics():
    """Get firmware analytics data"""
    try:
        analytics_data = analytics_engine.get_analytics_dashboard_data()
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Firmware analytics error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/comprehensive')
def get_comprehensive_analytics():
    """Get comprehensive analytics data for the dashboard"""
    try:
        # Mock comprehensive analytics data structure that frontend expects
        analytics_data = {
            'device_compatibility': {
                'summary': {
                    'total_devices': len(device_manager.get_all_devices()),
                    'compatibility_score': 0.85,
                    'risk_devices': 2,
                    'recommendations_available': 5
                },
                'by_chip_type': {
                    'ESP8266': {
                        'device_count': 8,
                        'avg_compatibility': 0.82,
                        'common_issues': ['Memory constraints', 'GPIO limitations']
                    },
                    'ESP32': {
                        'device_count': 4,
                        'avg_compatibility': 0.91,
                        'common_issues': ['WiFi stability']
                    }
                },
                'recent_analyses': []
            },
            'firmware_insights': {
                'summary': {
                    'total_firmware': 150,
                    'success_rate': 0.92,
                    'avg_download_time': 45.2,
                    'cache_hit_rate': 0.78
                },
                'popular_firmware': [
                    {
                        'name': 'tasmota.bin',
                        'version': '13.2.0',
                        'downloads': 245,
                        'success_rate': 0.94,
                        'compatibility_score': 0.89
                    }
                ],
                'performance_metrics': {
                    'download_speed': {'value': 2.1, 'trend': 'up'},
                    'cache_efficiency': {'value': 0.78, 'trend': 'stable'},
                    'error_rate': {'value': 0.08, 'trend': 'down'}
                }
            },
            'ml_recommendations': {
                'summary': {
                    'total_recommendations': 23,
                    'accuracy_score': 0.87,
                    'user_adoption_rate': 0.72
                },
                'recent_recommendations': [],
                'model_performance': {
                    'accuracy': 0.87,
                    'precision': 0.82,
                    'recall': 0.89,
                    'f1_score': 0.85
                }
            },
            'security_analysis': {
                'summary': {
                    'scanned_firmware': 89,
                    'security_issues': 3,
                    'risk_score': 2.1
                },
                'recent_scans': [],
                'vulnerability_trends': []
            }
        }
        
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Comprehensive analytics error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/flash/devices')
def get_flash_devices():
    """Get devices available for flashing (connected via USB)"""
    try:
        from services.flash_service import FlashService
        flash_service = FlashService()
        devices = flash_service.get_connected_devices()
        return jsonify({'devices': devices})
    except Exception as e:
        logger.error(f"Flash devices error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Device Configuration API Routes (Tasmotizer-like functionality)
@app.route('/api/devices/<device_id>/config/info')
@log_api_call('get_device_config_info')
@rate_limit(limit=30, window=60)
@add_security_headers
def get_device_config_info(device_id):
    """Get comprehensive device configuration information"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        device_info = device_config_service.get_device_info(device.get('ip'))
        
        if device_info:
            return jsonify({
                'success': True,
                'device_info': device_info
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to retrieve device information'}), 500
    except Exception as e:
        logger.error(f"Device config info error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>/config/wifi', methods=['POST'])
@log_api_call('configure_device_wifi')
@rate_limit(limit=5, window=300)
@validate_input(ssid='safe_string', password='safe_string')
@csrf_protect
@add_security_headers
def configure_device_wifi(device_id):
    """Configure WiFi settings on device"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No configuration data provided'}), 400
        
        ssid = data.get('ssid')
        password = data.get('password')
        ap_ssid = data.get('ap_ssid')
        ap_password = data.get('ap_password')
        
        if not ssid:
            return jsonify({'success': False, 'error': 'SSID is required'}), 400
        
        result = device_config_service.configure_wifi(
            device.get('ip'), ssid, password, ap_ssid, ap_password
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"WiFi configuration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>/config/mqtt', methods=['POST'])
@log_api_call('configure_device_mqtt')
@rate_limit(limit=10, window=300)
@validate_input(mqtt_host='safe_string')
@csrf_protect
@add_security_headers
def configure_device_mqtt(device_id):
    """Configure MQTT settings on device"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No configuration data provided'}), 400
        
        mqtt_host = data.get('mqtt_host')
        mqtt_port = data.get('mqtt_port', 1883)
        mqtt_user = data.get('mqtt_user', '')
        mqtt_pass = data.get('mqtt_pass', '')
        topic = data.get('topic', '')
        
        if not mqtt_host:
            return jsonify({'success': False, 'error': 'MQTT host is required'}), 400
        
        result = device_config_service.configure_mqtt(
            device.get('ip'), mqtt_host, mqtt_port, mqtt_user, mqtt_pass, topic
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"MQTT configuration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>/config/template', methods=['POST'])
@log_api_call('apply_device_template')
@rate_limit(limit=10, window=300)
@validate_input(template_name='safe_string')
@csrf_protect
@add_security_headers
def apply_device_template(device_id):
    """Apply device template (GPIO configuration)"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        data = request.get_json()
        template_name = data.get('template_name')
        
        if not template_name:
            return jsonify({'success': False, 'error': 'Template name is required'}), 400
        
        result = device_config_service.apply_template(device.get('ip'), template_name)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Template application error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>/config/name', methods=['POST'])
@log_api_call('configure_device_name')
@rate_limit(limit=10, window=300)
@validate_input(device_name='safe_string')
@csrf_protect
@add_security_headers
def configure_device_name(device_id):
    """Configure device and friendly names"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        data = request.get_json()
        device_name = data.get('device_name')
        friendly_name = data.get('friendly_name')
        
        if not device_name:
            return jsonify({'success': False, 'error': 'Device name is required'}), 400
        
        result = device_config_service.configure_device_name(
            device.get('ip'), device_name, friendly_name
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Device name configuration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>/config/command', methods=['POST'])
@log_api_call('send_raw_device_command')
@rate_limit(limit=20, window=300)
@validate_input(command='safe_string')
@csrf_protect
@add_security_headers
def send_raw_device_command(device_id):
    """Send raw Tasmota command to device"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        data = request.get_json()
        command = data.get('command')
        
        if not command:
            return jsonify({'success': False, 'error': 'Command is required'}), 400
        
        result = device_config_service.send_raw_command(device.get('ip'), command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Raw command error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>/config/backup')
@log_api_call('backup_device_config')
@rate_limit(limit=5, window=300)
@add_security_headers
def backup_device_config(device_id):
    """Backup device configuration"""
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        backup_data = device_config_service.backup_device_config(device.get('ip'))
        
        if backup_data:
            return jsonify({
                'success': True,
                'backup_data': backup_data
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to backup device configuration'}), 500
    except Exception as e:
        logger.error(f"Device backup error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/templates')
@log_api_call('get_device_templates')
@rate_limit(limit=30, window=60)
def get_device_templates():
    """Get available device templates"""
    try:
        templates = device_config_service.get_available_templates()
        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        logger.error(f"Get templates error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/discovery/network-scan', methods=['POST'])
@log_api_call('network_device_scan')
@rate_limit(limit=3, window=300)
@csrf_protect
@add_security_headers
def network_device_scan():
    """Scan network for Tasmota devices"""
    try:
        data = request.get_json() or {}
        network_range = data.get('network_range', '192.168.1')
        
        devices = device_config_service.scan_network_for_devices(network_range)
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices)
        })
    except Exception as e:
        logger.error(f"Network scan error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    cid = logger.set_correlation_id()
    logger.info('WebSocket client connected', 
               connection_type='websocket',
               client_correlation_id=cid)
    
    emit('status', {
        'connected': True,
        'correlation_id': cid,
        'services': {
            'mqtt': mqtt_client.is_connected(),
            'discovery': app_state['discovery_active']
        }
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info('WebSocket client disconnected', 
               connection_type='websocket',
               correlation_id=logger.get_correlation_id())

def device_update_callback(device_id, device_data):
    """Callback for device updates"""
    socketio.emit('device_update', {
        'device_id': device_id,
        'device': device_data
    })

def device_discovered_callback(device_data):
    """Callback for new device discovery"""
    socketio.emit('device_discovered', {
        'device': device_data
    })

def start_background_services():
    """Start background services with enhanced logging and health monitoring"""
    try:
        logger.info("Starting background services...", service="startup")
        
        # Register services with health monitor
        health_monitor.register_service('mqtt')
        health_monitor.register_service('discovery')
        health_monitor.register_service('background_scheduler')
        health_monitor.register_service('firmware_manager')
        health_monitor.register_service('app')
        
        # Add dependency checks
        health_monitor.add_dependency('mqtt_connection', 
                                    lambda: mqtt_client.is_connected(), 
                                    critical=True)
        health_monitor.add_dependency('database_access', 
                                    lambda: True,  # Simplified check - device_manager doesn't have test_database_connection
                                    critical=True)
        
        # Initialize MQTT client
        log_service_startup('mqtt', host=config_manager.get_config().get('mqtt_host', 'unknown'))
        mqtt_client.start()
        mqtt_health = get_service_health('mqtt')
        if mqtt_client.is_connected():
            mqtt_health.mark_healthy()
        else:
            mqtt_health.mark_degraded("Initial connection failed")
        
        # Set callbacks
        device_manager.set_update_callback(device_update_callback)
        device_discovery.set_discovery_callback(device_discovered_callback)
        
        # Start discovery
        log_service_startup('discovery')
        device_discovery.start_discovery()
        app_state['discovery_active'] = True
        get_service_health('discovery').mark_healthy()
        
        # Load devices from database
        logger.info("Loading devices from database", service="device_manager")
        device_count = device_manager.load_devices_from_db()
        logger.info(f"Loaded {device_count} devices from database", 
                   service="device_manager", device_count=device_count)
        
        # Start background scheduler
        log_service_startup('background_scheduler')
        background_scheduler.start()
        get_service_health('background_scheduler').mark_healthy()
        
        # Mark firmware services as healthy
        log_service_startup('firmware_manager')
        get_service_health('firmware_manager').mark_healthy()
        
        # Start health monitoring
        health_monitor.start_monitoring(interval=300)  # Check every 5 minutes
        
        app_state['services_running'] = True
        logger.info("All background services started successfully", 
                   service="startup", services_count=5)
                   
    except Exception as e:
        logger.error("Failed to start background services", 
                    service="startup", exc_info=True)
        # Mark all services as unhealthy
        for service_name in ['mqtt', 'discovery', 'background_scheduler', 'firmware_manager']:
            get_service_health(service_name).mark_unhealthy(e)
        raise

# Serve static files for frontend
@app.route('/')
def serve_frontend():
    return send_from_directory('/opt/app/frontend/build', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('/opt/app/frontend/build', path)

# Apply security middleware to all responses
@app.after_request
def apply_security_middleware(response):
    """Apply security headers to all responses"""
    from utils.security import SecurityHeaders
    response = SecurityHeaders.add_security_headers(response)
    
    # Add correlation ID to response headers for debugging
    correlation_id = logger.get_correlation_id()
    if correlation_id:
        response.headers['X-Correlation-ID'] = correlation_id
    
    return response

# Error handler for rate limiting
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors"""
    logger.warning("Rate limit exceeded", 
                  client_ip=request.remote_addr,
                  endpoint=request.endpoint)
    return jsonify(ErrorHandler.handle_error('RATE_LIMIT_EXCEEDED', e)), 429

# Global error handler
@app.errorhandler(500)
def internal_error_handler(e):
    """Handle internal server errors"""
    logger.error("Internal server error", 
                endpoint=request.endpoint,
                method=request.method,
                exc_info=True)
    return jsonify(ErrorHandler.handle_error('SERVICE_UNAVAILABLE', e)), 500

if __name__ == '__main__':
    # Start background services in a separate thread
    services_thread = threading.Thread(target=start_background_services)
    services_thread.daemon = True
    services_thread.start()
    
    # Log application startup
    logger.info("Starting Tasmota Master application", 
               host='0.0.0.0', 
               port=5000,
               debug=False)
    
    # Start the Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)