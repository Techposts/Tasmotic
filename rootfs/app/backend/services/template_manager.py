import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class TemplateManager:
    """Manages device templates for Tasmota devices"""
    
    def __init__(self):
        self.db_path = '/opt/app/data/templates.db'
        self.templates_dir = '/opt/app/data/templates'
        self._init_database()
        self._load_builtin_templates()
    
    def _init_database(self):
        """Initialize SQLite database for template storage"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            os.makedirs(self.templates_dir, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    template_data TEXT NOT NULL,
                    gpio_config TEXT,
                    rules TEXT,
                    settings TEXT,
                    image_url TEXT,
                    author TEXT,
                    version TEXT,
                    tags TEXT,
                    public BOOLEAN DEFAULT 0,
                    downloads INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS template_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT,
                    user_id TEXT,
                    rating INTEGER,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES templates (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Template database initialized")
        except Exception as e:
            logger.error(f"Template database initialization error: {e}")
    
    def _load_builtin_templates(self):
        """Load built-in device templates"""
        builtin_templates = [
            {
                'id': 'sonoff_basic',
                'name': 'Sonoff Basic R2',
                'description': 'Basic WiFi smart switch with relay',
                'category': 'Switch',
                'manufacturer': 'Sonoff',
                'model': 'Basic R2',
                'template_data': {
                    'NAME': 'Sonoff Basic',
                    'GPIO': [17, 255, 255, 255, 255, 0, 255, 255, 21, 56, 255, 255, 255],
                    'FLAG': 0,
                    'BASE': 1
                },
                'gpio_config': {
                    'GPIO0': 'Button1',
                    'GPIO12': 'Relay1',
                    'GPIO13': 'Led1i'
                },
                'settings': {
                    'SetOption73': '1',  # Button decoupling
                    'LedState': '1'      # LED follows relay
                }
            },
            {
                'id': 'sonoff_s20',
                'name': 'Sonoff S20',
                'description': 'Smart plug with relay and LED',
                'category': 'Plug',
                'manufacturer': 'Sonoff',
                'model': 'S20',
                'template_data': {
                    'NAME': 'Sonoff S20',
                    'GPIO': [17, 255, 255, 255, 255, 0, 255, 255, 21, 56, 255, 255, 255],
                    'FLAG': 0,
                    'BASE': 1
                },
                'gpio_config': {
                    'GPIO0': 'Button1',
                    'GPIO12': 'Relay1',
                    'GPIO13': 'Led1i'
                }
            },
            {
                'id': 'wemos_d1_mini',
                'name': 'Wemos D1 Mini',
                'description': 'Generic ESP8266 development board',
                'category': 'Development',
                'manufacturer': 'Wemos',
                'model': 'D1 Mini',
                'template_data': {
                    'NAME': 'WeMos D1 mini',
                    'GPIO': [255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255],
                    'FLAG': 0,
                    'BASE': 18
                },
                'gpio_config': {
                    'D0': 'GPIO16',
                    'D1': 'GPIO5',
                    'D2': 'GPIO4',
                    'D3': 'GPIO0',
                    'D4': 'GPIO2',
                    'D5': 'GPIO14',
                    'D6': 'GPIO12',
                    'D7': 'GPIO13',
                    'D8': 'GPIO15'
                }
            },
            {
                'id': 'esp32_devkit',
                'name': 'ESP32 DevKit',
                'description': 'Generic ESP32 development board',
                'category': 'Development',
                'manufacturer': 'Espressif',
                'model': 'ESP32',
                'template_data': {
                    'NAME': 'ESP32-DevKit',
                    'GPIO': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    'FLAG': 0,
                    'BASE': 1
                },
                'gpio_config': {
                    'GPIO2': 'User',
                    'GPIO4': 'User',
                    'GPIO5': 'User'
                }
            }
        ]
        
        # Insert built-in templates if they don't exist
        for template in builtin_templates:
            existing = self.get_template(template['id'])
            if not existing:
                self._save_template_to_db(template)
                logger.info(f"Loaded built-in template: {template['name']}")
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Get all templates"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, description, category, manufacturer, model,
                       template_data, gpio_config, rules, settings, image_url,
                       author, version, tags, public, downloads, rating,
                       created_at, updated_at
                FROM templates
                ORDER BY category, manufacturer, name
            ''')
            
            templates = []
            for row in cursor.fetchall():
                template = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'manufacturer': row[4],
                    'model': row[5],
                    'template_data': json.loads(row[6]) if row[6] else {},
                    'gpio_config': json.loads(row[7]) if row[7] else {},
                    'rules': json.loads(row[8]) if row[8] else [],
                    'settings': json.loads(row[9]) if row[9] else {},
                    'image_url': row[10],
                    'author': row[11],
                    'version': row[12],
                    'tags': json.loads(row[13]) if row[13] else [],
                    'public': bool(row[14]),
                    'downloads': row[15],
                    'rating': row[16],
                    'created_at': row[17],
                    'updated_at': row[18]
                }
                templates.append(template)
            
            conn.close()
            return templates
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return []
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get specific template by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, description, category, manufacturer, model,
                       template_data, gpio_config, rules, settings, image_url,
                       author, version, tags, public, downloads, rating,
                       created_at, updated_at
                FROM templates
                WHERE id = ?
            ''', (template_id,))
            
            row = cursor.fetchone()
            if row:
                template = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'manufacturer': row[4],
                    'model': row[5],
                    'template_data': json.loads(row[6]) if row[6] else {},
                    'gpio_config': json.loads(row[7]) if row[7] else {},
                    'rules': json.loads(row[8]) if row[8] else [],
                    'settings': json.loads(row[9]) if row[9] else {},
                    'image_url': row[10],
                    'author': row[11],
                    'version': row[12],
                    'tags': json.loads(row[13]) if row[13] else [],
                    'public': bool(row[14]),
                    'downloads': row[15],
                    'rating': row[16],
                    'created_at': row[17],
                    'updated_at': row[18]
                }
                conn.close()
                return template
            
            conn.close()
            return None
        except Exception as e:
            logger.error(f"Error getting template {template_id}: {e}")
            return None
    
    def create_template(self, template_data: Dict[str, Any]) -> str:
        """Create new template"""
        try:
            template_id = template_data.get('id') or f"custom_{int(datetime.now().timestamp())}"
            template_data['id'] = template_id
            template_data['created_at'] = datetime.now().isoformat()
            template_data['updated_at'] = datetime.now().isoformat()
            
            self._save_template_to_db(template_data)
            logger.info(f"Created template: {template_id}")
            return template_id
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise
    
    def update_template(self, template_id: str, template_data: Dict[str, Any]) -> bool:
        """Update existing template"""
        try:
            template_data['updated_at'] = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE templates SET
                    name = ?, description = ?, category = ?, manufacturer = ?,
                    model = ?, template_data = ?, gpio_config = ?, rules = ?,
                    settings = ?, image_url = ?, author = ?, version = ?,
                    tags = ?, updated_at = ?
                WHERE id = ?
            ''', (
                template_data.get('name', ''),
                template_data.get('description', ''),
                template_data.get('category', ''),
                template_data.get('manufacturer', ''),
                template_data.get('model', ''),
                json.dumps(template_data.get('template_data', {})),
                json.dumps(template_data.get('gpio_config', {})),
                json.dumps(template_data.get('rules', [])),
                json.dumps(template_data.get('settings', {})),
                template_data.get('image_url', ''),
                template_data.get('author', ''),
                template_data.get('version', ''),
                json.dumps(template_data.get('tags', [])),
                template_data['updated_at'],
                template_id
            ))
            
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            if success:
                logger.info(f"Updated template: {template_id}")
            return success
        except Exception as e:
            logger.error(f"Error updating template {template_id}: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete template"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM templates WHERE id = ?', (template_id,))
            cursor.execute('DELETE FROM template_ratings WHERE template_id = ?', (template_id,))
            
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            if success:
                logger.info(f"Deleted template: {template_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {e}")
            return False
    
    def apply_template(self, template_id: str, device_id: str) -> Dict[str, Any]:
        """Apply template to device"""
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Get device manager to send commands
            from .device_manager import DeviceManager
            device_manager = DeviceManager(None)  # This will be injected properly
            device = device_manager.get_device(device_id)
            
            if not device:
                raise ValueError(f"Device {device_id} not found")
            
            results = []
            
            # Apply template
            if template['template_data']:
                template_json = json.dumps(template['template_data'])
                result = device_manager.send_command(device_id, 'Template', template_json)
                results.append({'command': 'Template', 'result': result})
            
            # Apply settings
            if template.get('settings'):
                for setting, value in template['settings'].items():
                    result = device_manager.send_command(device_id, setting, str(value))
                    results.append({'command': setting, 'result': result})
            
            # Apply rules
            if template.get('rules'):
                for i, rule in enumerate(template['rules'], 1):
                    result = device_manager.send_command(device_id, f'Rule{i}', rule)
                    results.append({'command': f'Rule{i}', 'result': result})
            
            # Restart device to apply changes
            restart_result = device_manager.send_command(device_id, 'Restart', '1')
            results.append({'command': 'Restart', 'result': restart_result})
            
            # Update template download count
            self._increment_downloads(template_id)
            
            logger.info(f"Applied template {template_id} to device {device_id}")
            return {
                'success': True,
                'template': template,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error applying template {template_id} to device {device_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_template_to_db(self, template_data: Dict[str, Any]):
        """Save template to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO templates
                (id, name, description, category, manufacturer, model,
                 template_data, gpio_config, rules, settings, image_url,
                 author, version, tags, public, downloads, rating,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template_data['id'],
                template_data.get('name', ''),
                template_data.get('description', ''),
                template_data.get('category', ''),
                template_data.get('manufacturer', ''),
                template_data.get('model', ''),
                json.dumps(template_data.get('template_data', {})),
                json.dumps(template_data.get('gpio_config', {})),
                json.dumps(template_data.get('rules', [])),
                json.dumps(template_data.get('settings', {})),
                template_data.get('image_url', ''),
                template_data.get('author', ''),
                template_data.get('version', '1.0'),
                json.dumps(template_data.get('tags', [])),
                template_data.get('public', False),
                template_data.get('downloads', 0),
                template_data.get('rating', 0.0),
                template_data.get('created_at', datetime.now().isoformat()),
                template_data.get('updated_at', datetime.now().isoformat())
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving template to database: {e}")
            raise
    
    def _increment_downloads(self, template_id: str):
        """Increment template download count"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE templates SET downloads = downloads + 1
                WHERE id = ?
            ''', (template_id,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error incrementing downloads for {template_id}: {e}")
    
    def search_templates(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """Search templates by name, description, or tags"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            sql = '''
                SELECT id, name, description, category, manufacturer, model,
                       template_data, gpio_config, rules, settings, image_url,
                       author, version, tags, public, downloads, rating,
                       created_at, updated_at
                FROM templates
                WHERE (name LIKE ? OR description LIKE ? OR tags LIKE ?)
            '''
            params = [f'%{query}%', f'%{query}%', f'%{query}%']
            
            if category:
                sql += ' AND category = ?'
                params.append(category)
            
            sql += ' ORDER BY downloads DESC, rating DESC, name'
            
            cursor.execute(sql, params)
            
            templates = []
            for row in cursor.fetchall():
                template = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'manufacturer': row[4],
                    'model': row[5],
                    'template_data': json.loads(row[6]) if row[6] else {},
                    'gpio_config': json.loads(row[7]) if row[7] else {},
                    'rules': json.loads(row[8]) if row[8] else [],
                    'settings': json.loads(row[9]) if row[9] else {},
                    'image_url': row[10],
                    'author': row[11],
                    'version': row[12],
                    'tags': json.loads(row[13]) if row[13] else [],
                    'public': bool(row[14]),
                    'downloads': row[15],
                    'rating': row[16],
                    'created_at': row[17],
                    'updated_at': row[18]
                }
                templates.append(template)
            
            conn.close()
            return templates
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return []