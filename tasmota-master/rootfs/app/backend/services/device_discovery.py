import logging
import threading
import time
import socket
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
import requests

logger = logging.getLogger(__name__)

class TasmotaServiceListener(ServiceListener):
    """Service listener for Tasmota device discovery via mDNS/Zeroconf"""
    
    def __init__(self, discovery_service):
        self.discovery_service = discovery_service
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.info(f"Service removed: {name}")
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            self.discovery_service._process_mdns_service(info)

class DeviceDiscovery:
    """Discovers Tasmota devices on the network"""
    
    def __init__(self, device_manager, mqtt_client):
        self.device_manager = device_manager
        self.mqtt_client = mqtt_client
        self.discovery_callback = None
        self.running = False
        self.zeroconf = None
        self.browser = None
        self.discovery_thread = None
        self.network_scan_thread = None
        
        # Services to discover
        self.services = [
            "_http._tcp.local.",
            "_tasmota._tcp.local.",
            "_esphomelib._tcp.local."
        ]
    
    def set_discovery_callback(self, callback: Callable):
        """Set callback function for device discovery"""
        self.discovery_callback = callback
    
    def start_discovery(self):
        """Start device discovery process"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting device discovery...")
        
        # Start mDNS discovery
        self._start_mdns_discovery()
        
        # Start network scanning
        self._start_network_scan()
        
        # Trigger MQTT discovery
        self._trigger_mqtt_discovery()
    
    def stop_discovery(self):
        """Stop device discovery process"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping device discovery...")
        
        # Stop mDNS discovery
        if self.browser:
            self.browser.cancel()
        if self.zeroconf:
            self.zeroconf.close()
        
        self.zeroconf = None
        self.browser = None
    
    def _start_mdns_discovery(self):
        """Start mDNS/Zeroconf discovery"""
        try:
            self.zeroconf = Zeroconf()
            listener = TasmotaServiceListener(self)
            
            self.browser = ServiceBrowser(self.zeroconf, self.services, listener)
            logger.info("mDNS discovery started")
        except Exception as e:
            logger.error(f"mDNS discovery error: {e}")
    
    def _start_network_scan(self):
        """Start network IP scanning"""
        self.network_scan_thread = threading.Thread(target=self._network_scan_loop)
        self.network_scan_thread.daemon = True
        self.network_scan_thread.start()
    
    def _network_scan_loop(self):
        """Network scanning loop"""
        while self.running:
            try:
                self._scan_network()
                time.sleep(300)  # Scan every 5 minutes
            except Exception as e:
                logger.error(f"Network scan error: {e}")
                time.sleep(60)
    
    def _scan_network(self):
        """Scan local network for devices"""
        logger.info("Starting network scan...")
        
        # Get local network range
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network_base = '.'.join(local_ip.split('.')[:-1])
        except Exception as e:
            logger.error(f"Failed to get local IP: {e}")
            return
        
        # Scan common ports and paths
        threads = []
        for i in range(1, 255):
            if not self.running:
                break
                
            ip = f"{network_base}.{i}"
            thread = threading.Thread(target=self._check_device_at_ip, args=(ip,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            
            # Limit concurrent threads
            if len(threads) >= 50:
                for t in threads:
                    t.join(timeout=0.1)
                threads = [t for t in threads if t.is_alive()]
        
        # Wait for remaining threads
        for thread in threads:
            thread.join(timeout=5)
    
    def _check_device_at_ip(self, ip: str):
        """Check if there's a Tasmota device at the given IP"""
        try:
            # Try common Tasmota endpoints
            endpoints = [
                f"http://{ip}/",
                f"http://{ip}/cm?cmnd=Status",
                f"http://{ip}/ay",  # Tasmota info endpoint
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=2)
                    if response.status_code == 200:
                        content = response.text.lower()
                        
                        # Check for Tasmota indicators
                        if any(indicator in content for indicator in [
                            'tasmota', 'esp8266', 'esp32', 'sonoff'
                        ]):
                            self._process_http_device(ip, response)
                            return
                            
                except requests.RequestException:
                    continue
                    
        except Exception as e:
            logger.debug(f"IP check error for {ip}: {e}")
    
    def _process_http_device(self, ip: str, response):
        """Process device found via HTTP"""
        try:
            # Try to get device status
            status_url = f"http://{ip}/cm?cmnd=Status"
            status_response = requests.get(status_url, timeout=5)
            
            if status_response.status_code == 200:
                try:
                    status_data = status_response.json()
                    device_data = self._extract_device_info_from_status(ip, status_data)
                    if device_data:
                        self._add_discovered_device(device_data)
                except Exception as e:
                    logger.debug(f"Status parsing error for {ip}: {e}")
            
            # Fallback: create basic device info
            device_data = {
                'ip': ip,
                'name': f"Tasmota-{ip.split('.')[-1]}",
                'discovery_method': 'http_scan',
                'last_seen': datetime.now().isoformat(),
                'status': 'online'
            }
            self._add_discovered_device(device_data)
            
        except Exception as e:
            logger.error(f"HTTP device processing error: {e}")
    
    def _process_mdns_service(self, info):
        """Process mDNS service discovery"""
        try:
            if not info.addresses:
                return
            
            ip = socket.inet_ntoa(info.addresses[0])
            name = info.name.split('.')[0]
            
            device_data = {
                'ip': ip,
                'name': name,
                'port': info.port,
                'discovery_method': 'mdns',
                'last_seen': datetime.now().isoformat(),
                'status': 'online',
                'service_info': {
                    'type': info.type,
                    'name': info.name,
                    'properties': dict(info.properties) if info.properties else {}
                }
            }
            
            # Try to get additional info via HTTP
            try:
                status_url = f"http://{ip}/cm?cmnd=Status"
                response = requests.get(status_url, timeout=3)
                if response.status_code == 200:
                    status_data = response.json()
                    additional_info = self._extract_device_info_from_status(ip, status_data)
                    if additional_info:
                        device_data.update(additional_info)
            except Exception:
                pass
            
            self._add_discovered_device(device_data)
            
        except Exception as e:
            logger.error(f"mDNS service processing error: {e}")
    
    def _extract_device_info_from_status(self, ip: str, status_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract device information from Tasmota status response"""
        try:
            device_info = {
                'ip': ip,
                'discovery_method': 'tasmota_api'
            }
            
            # Extract from Status response
            if 'Status' in status_data:
                status = status_data['Status']
                device_info.update({
                    'name': status.get('DeviceName', f"Tasmota-{ip.split('.')[-1]}"),
                    'friendly_name': status.get('FriendlyName', [''])[0],
                    'topic': status.get('Topic'),
                    'group_topic': status.get('GroupTopic'),
                    'firmware_version': status.get('Version'),
                    'hardware': status.get('Hardware')
                })
            
            # Extract from StatusSTS
            if 'StatusSTS' in status_data:
                sts = status_data['StatusSTS']
                device_info.update({
                    'uptime': sts.get('Uptime'),
                    'wifi_signal': sts.get('Wifi', {}).get('RSSI'),
                    'power_state': sts.get('POWER')
                })
            
            # Extract from StatusNET
            if 'StatusNET' in status_data:
                net = status_data['StatusNET']
                device_info.update({
                    'hostname': net.get('Hostname'),
                    'mac': net.get('Mac'),
                    'gateway': net.get('Gateway'),
                    'dns': net.get('DNSServer')
                })
            
            return device_info
            
        except Exception as e:
            logger.error(f"Status extraction error: {e}")
            return None
    
    def _trigger_mqtt_discovery(self):
        """Trigger MQTT discovery for Tasmota devices"""
        if self.mqtt_client.is_connected():
            # Send discovery trigger
            self.mqtt_client.send_command("tasmotas", "SetOption19", "0")
            logger.info("Triggered MQTT discovery")
    
    def _add_discovered_device(self, device_data: Dict[str, Any]):
        """Add discovered device to device manager"""
        try:
            device_id = self.device_manager.add_device(device_data)
            
            # Notify callback
            if self.discovery_callback:
                try:
                    self.discovery_callback(device_data)
                except Exception as e:
                    logger.error(f"Discovery callback error: {e}")
            
            logger.info(f"Device discovered: {device_data.get('name', 'Unknown')} at {device_data.get('ip', 'Unknown IP')}")
            
        except Exception as e:
            logger.error(f"Failed to add discovered device: {e}")
    
    def discover_device_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """Manually discover device by IP address"""
        try:
            # Check if device responds to Tasmota API
            status_url = f"http://{ip}/cm?cmnd=Status"
            response = requests.get(status_url, timeout=5)
            
            if response.status_code == 200:
                status_data = response.json()
                device_data = self._extract_device_info_from_status(ip, status_data)
                
                if device_data:
                    device_data['last_seen'] = datetime.now().isoformat()
                    device_data['status'] = 'online'
                    
                    device_id = self.device_manager.add_device(device_data)
                    return self.device_manager.get_device(device_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Manual discovery error for {ip}: {e}")
            return None