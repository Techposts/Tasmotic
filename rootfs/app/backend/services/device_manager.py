import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import sqlite3
import os

logger = logging.getLogger(__name__)

class DeviceManager:
    """Manages Tasmota devices and their state"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.devices = {}
        self.update_callback = None
        self.db_path = '/opt/app/data/devices.db'
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for device storage"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    ip TEXT,
                    mac TEXT,
                    firmware_version TEXT,
                    hardware TEXT,
                    template TEXT,
                    config TEXT,
                    last_seen TIMESTAMP,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uptime INTEGER,
                    free_memory INTEGER,
                    wifi_signal INTEGER,
                    power_state TEXT,
                    FOREIGN KEY (device_id) REFERENCES devices (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def set_update_callback(self, callback: Callable):
        """Set callback function for device updates"""
        self.update_callback = callback
    
    def add_device(self, device_data: Dict[str, Any]) -> str:
        """Add or update device"""
        device_id = device_data.get('id') or device_data.get('mac', '').replace(':', '')
        
        with self.lock:
            # Update in-memory storage
            if device_id in self.devices:
                self.devices[device_id].update(device_data)
                self.devices[device_id]['updated_at'] = datetime.now().isoformat()
            else:
                device_data['id'] = device_id
                device_data['created_at'] = datetime.now().isoformat()
                device_data['updated_at'] = datetime.now().isoformat()
                self.devices[device_id] = device_data
            
            # Update database
            self._save_device_to_db(device_id, self.devices[device_id])
            
            # Notify callback
            if self.update_callback:
                try:
                    self.update_callback(device_id, self.devices[device_id])
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        logger.info(f"Device updated: {device_id}")
        return device_id
    
    def _save_device_to_db(self, device_id: str, device_data: Dict[str, Any]):
        """Save device to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO devices 
                (id, name, ip, mac, firmware_version, hardware, template, config, 
                 last_seen, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_id,
                device_data.get('name', ''),
                device_data.get('ip', ''),
                device_data.get('mac', ''),
                device_data.get('firmware_version', ''),
                device_data.get('hardware', ''),
                json.dumps(device_data.get('template', {})),
                json.dumps(device_data.get('config', {})),
                device_data.get('last_seen', datetime.now().isoformat()),
                device_data.get('status', 'unknown'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Database save error: {e}")
    
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by ID"""
        with self.lock:
            return self.devices.get(device_id)
    
    def get_all_devices(self) -> Dict[str, Any]:
        """Get all devices"""
        with self.lock:
            return self.devices.copy()
    
    def remove_device(self, device_id: str) -> bool:
        """Remove device"""
        with self.lock:
            if device_id in self.devices:
                del self.devices[device_id]
                
                # Remove from database
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM devices WHERE id = ?', (device_id,))
                    cursor.execute('DELETE FROM device_stats WHERE device_id = ?', (device_id,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Database delete error: {e}")
                
                logger.info(f"Device removed: {device_id}")
                return True
        return False
    
    def update_device_status(self, device_id: str, status_data: Dict[str, Any]):
        """Update device status"""
        if device_id in self.devices:
            with self.lock:
                self.devices[device_id]['status'] = status_data.get('status', 'online')
                self.devices[device_id]['last_seen'] = datetime.now().isoformat()
                
                # Update specific status fields
                for key in ['uptime', 'free_memory', 'wifi_signal', 'power_state']:
                    if key in status_data:
                        self.devices[device_id][key] = status_data[key]
                
                # Save stats to database
                self._save_device_stats(device_id, status_data)
                
                # Notify callback
                if self.update_callback:
                    try:
                        self.update_callback(device_id, self.devices[device_id])
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
    
    def _save_device_stats(self, device_id: str, stats: Dict[str, Any]):
        """Save device statistics to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO device_stats 
                (device_id, uptime, free_memory, wifi_signal, power_state)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                device_id,
                stats.get('uptime'),
                stats.get('free_memory'),
                stats.get('wifi_signal'),
                json.dumps(stats.get('power_state', {}))
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Stats save error: {e}")
    
    def send_command(self, device_id: str, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send command to device via MQTT"""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        # This will be implemented to send MQTT commands
        logger.info(f"Sending command to {device_id}: {command}")
        
        # For now, return success
        return {
            'success': True,
            'command': command,
            'params': params,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_device_stats(self, device_id: str, hours: int = 24) -> list:
        """Get device statistics history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, uptime, free_memory, wifi_signal, power_state
                FROM device_stats
                WHERE device_id = ? AND timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            '''.format(hours), (device_id,))
            
            stats = []
            for row in cursor.fetchall():
                stats.append({
                    'timestamp': row[0],
                    'uptime': row[1],
                    'free_memory': row[2],
                    'wifi_signal': row[3],
                    'power_state': json.loads(row[4]) if row[4] else {}
                })
            
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Stats retrieval error: {e}")
            return []
    
    def load_devices_from_db(self):
        """Load devices from database on startup"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM devices')
            rows = cursor.fetchall()
            
            for row in rows:
                device_data = {
                    'id': row[0],
                    'name': row[1],
                    'ip': row[2],
                    'mac': row[3],
                    'firmware_version': row[4],
                    'hardware': row[5],
                    'template': json.loads(row[6]) if row[6] else {},
                    'config': json.loads(row[7]) if row[7] else {},
                    'last_seen': row[8],
                    'status': row[9],
                    'created_at': row[10],
                    'updated_at': row[11]
                }
                self.devices[device_data['id']] = device_data
            
            conn.close()
            logger.info(f"Loaded {len(self.devices)} devices from database")
        except Exception as e:
            logger.error(f"Database load error: {e}")