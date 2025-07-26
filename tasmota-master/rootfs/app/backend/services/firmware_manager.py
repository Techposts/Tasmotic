import asyncio
import aiohttp
import hashlib
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import zipfile
import tempfile

logger = logging.getLogger(__name__)

class FirmwareManager:
    """Complete firmware management system with automated tracking"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.db_path = '/opt/app/data/firmware.db'
        self.cache_dir = '/opt/app/data/firmware_cache'
        self.temp_dir = '/opt/app/data/temp'
        
        # Firmware sources
        self.sources = {
            'github_releases': {
                'url': 'https://api.github.com/repos/arendst/Tasmota/releases',
                'type': 'github_api',
                'channel': 'stable'
            },
            'github_artifacts': {
                'url': 'https://api.github.com/repos/arendst/Tasmota/actions/artifacts',
                'type': 'github_api',
                'channel': 'development'
            },
            'ota_esp8266': {
                'url': 'http://ota.tasmota.com/tasmota/release/',
                'type': 'ota_server',
                'chip_type': 'ESP8266',
                'channel': 'stable'
            },
            'ota_esp32': {
                'url': 'http://ota.tasmota.com/tasmota32/release/',
                'type': 'ota_server',
                'chip_type': 'ESP32',
                'channel': 'stable'
            },
            'ota_esp8266_dev': {
                'url': 'http://ota.tasmota.com/tasmota/',
                'type': 'ota_server',
                'chip_type': 'ESP8266',
                'channel': 'development'
            },
            'ota_esp32_dev': {
                'url': 'http://ota.tasmota.com/tasmota32/',
                'type': 'ota_server',
                'chip_type': 'ESP32',
                'channel': 'development'
            }
        }
        
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize firmware database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Firmware table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firmware (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    chip_type TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    source TEXT NOT NULL,
                    download_url TEXT NOT NULL,
                    local_path TEXT,
                    size INTEGER,
                    md5_hash TEXT,
                    sha256_hash TEXT,
                    published_at TIMESTAMP,
                    changelog TEXT,
                    features TEXT,
                    compatibility TEXT,
                    download_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    verified BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'available',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Download statistics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firmware_downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firmware_id TEXT,
                    user_agent TEXT,
                    ip_address TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (firmware_id) REFERENCES firmware (id)
                )
            ''')
            
            # User ratings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firmware_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firmware_id TEXT,
                    user_id TEXT,
                    rating INTEGER,
                    comment TEXT,
                    device_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (firmware_id) REFERENCES firmware (id)
                )
            ''')
            
            # Update tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS update_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    last_check TIMESTAMP,
                    found_updates INTEGER,
                    errors TEXT,
                    duration REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Firmware database initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    async def check_all_sources_for_updates(self) -> Dict[str, Any]:
        """Check all sources for firmware updates"""
        results = {
            'total_updates': 0,
            'sources': {},
            'errors': []
        }
        
        for source_name, source_config in self.sources.items():
            try:
                logger.info(f"Checking source: {source_name}")
                start_time = datetime.now()
                
                if source_config['type'] == 'github_api':
                    updates = await self._check_github_source(source_name, source_config)
                elif source_config['type'] == 'ota_server':
                    updates = await self._check_ota_source(source_name, source_config)
                else:
                    logger.warning(f"Unknown source type: {source_config['type']}")
                    continue
                
                # Record update check
                duration = (datetime.now() - start_time).total_seconds()
                self._record_update_check(source_name, len(updates), None, duration)
                
                results['sources'][source_name] = {
                    'updates': len(updates),
                    'duration': duration,
                    'firmware': updates
                }
                results['total_updates'] += len(updates)
                
                logger.info(f"Found {len(updates)} updates from {source_name}")
                
            except Exception as e:
                error_msg = f"Error checking {source_name}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                self._record_update_check(source_name, 0, str(e), 0)
        
        return results
    
    async def _check_github_source(self, source_name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check GitHub API for firmware updates"""
        updates = []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Tasmota-Master/1.0'
                }
                
                # Add GitHub token if available
                github_token = self.config_manager.get('github_token')
                if github_token:
                    headers['Authorization'] = f'token {github_token}'
                
                async with session.get(config['url'], headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'releases' in config['url']:
                            updates = await self._process_github_releases(data, config)
                        elif 'artifacts' in config['url']:
                            updates = await self._process_github_artifacts(data, config)
                    else:
                        logger.error(f"GitHub API error: {response.status}")
        
        except Exception as e:
            logger.error(f"GitHub source check failed: {e}")
        
        return updates
    
    async def _process_github_releases(self, releases: List[Dict], config: Dict) -> List[Dict[str, Any]]:
        """Process GitHub releases"""
        updates = []
        
        for release in releases[:10]:  # Process last 10 releases
            if release.get('draft') or release.get('prerelease'):
                continue
            
            version = release['tag_name']
            published_at = release['published_at']
            changelog = release.get('body', '')
            
            for asset in release.get('assets', []):
                if asset['name'].endswith('.bin'):
                    firmware_info = self._parse_firmware_filename(asset['name'])
                    if firmware_info:
                        firmware_id = self._generate_firmware_id(
                            asset['name'], version, config['channel']
                        )
                        
                        # Check if already exists
                        if not self._firmware_exists(firmware_id):
                            updates.append({
                                'id': firmware_id,
                                'name': asset['name'],
                                'version': version,
                                'chip_type': firmware_info['chip_type'],
                                'variant': firmware_info['variant'],
                                'channel': config['channel'],
                                'source': 'github_releases',
                                'download_url': asset['browser_download_url'],
                                'size': asset['size'],
                                'published_at': published_at,
                                'changelog': changelog,
                                'features': firmware_info.get('features', []),
                                'compatibility': firmware_info.get('compatibility', [])
                            })
        
        return updates
    
    async def _check_ota_source(self, source_name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check OTA server for firmware updates"""
        updates = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(config['url']) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        firmware_files = self._parse_ota_directory(html_content, config['url'])
                        
                        for file_info in firmware_files:
                            firmware_info = self._parse_firmware_filename(file_info['name'])
                            if firmware_info and firmware_info['chip_type'] == config['chip_type']:
                                firmware_id = self._generate_firmware_id(
                                    file_info['name'], 'latest', config['channel']
                                )
                                
                                if not self._firmware_exists(firmware_id):
                                    updates.append({
                                        'id': firmware_id,
                                        'name': file_info['name'],
                                        'version': 'latest',
                                        'chip_type': firmware_info['chip_type'],
                                        'variant': firmware_info['variant'],
                                        'channel': config['channel'],
                                        'source': source_name,
                                        'download_url': file_info['url'],
                                        'size': file_info.get('size', 0),
                                        'published_at': datetime.now().isoformat(),
                                        'features': firmware_info.get('features', []),
                                        'compatibility': firmware_info.get('compatibility', [])
                                    })
        
        except Exception as e:
            logger.error(f"OTA source check failed: {e}")
        
        return updates
    
    def _parse_ota_directory(self, html_content: str, base_url: str) -> List[Dict[str, Any]]:
        """Parse OTA server directory listing"""
        files = []
        
        # Simple regex to find .bin files in directory listing
        bin_pattern = re.compile(r'href="([^"]*\.bin)"[^>]*>([^<]*\.bin)</a>.*?(\d+)', re.IGNORECASE)
        
        for match in bin_pattern.finditer(html_content):
            filename = match.group(1)
            display_name = match.group(2)
            size = int(match.group(3)) if match.group(3).isdigit() else 0
            
            files.append({
                'name': filename,
                'display_name': display_name,
                'url': urljoin(base_url, filename),
                'size': size
            })
        
        return files
    
    def _parse_firmware_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Parse firmware filename to extract metadata"""
        # Remove .bin extension
        name = filename.replace('.bin', '').lower()
        
        # Determine chip type
        chip_type = 'ESP8266'
        if 'tasmota32' in name or 'esp32' in name:
            chip_type = 'ESP32'
        elif 'tasmota-esp32' in name:
            chip_type = 'ESP32'
        
        # Determine variant
        variant = 'standard'
        features = []
        compatibility = []
        
        if 'minimal' in name:
            variant = 'minimal'
            features = ['OTA', 'Basic GPIO']
        elif 'lite' in name:
            variant = 'lite'
            features = ['MQTT', 'WiFi', 'Basic Controls']
        elif 'sensors' in name:
            variant = 'sensors'
            features = ['All Sensors', 'DHT22', 'DS18B20', 'BMP280']
        elif 'display' in name:
            variant = 'display'
            features = ['Display Support', 'SSD1306', 'ILI9341']
        elif 'ir' in name:
            variant = 'ir'
            features = ['IR Transmit', 'IR Receive', 'HVAC Control']
        elif 'zigbee' in name:
            variant = 'zigbee'
            features = ['Zigbee Bridge', 'CC2530', 'Coordinator']
        elif 'knx' in name:
            variant = 'knx'
            features = ['KNX Protocol', 'Building Automation']
        
        # Language variants
        if '-de' in name:
            variant += '-de'
            compatibility.append('German')
        elif '-cn' in name:
            variant += '-cn'
            compatibility.append('Chinese')
        
        return {
            'chip_type': chip_type,
            'variant': variant,
            'features': features,
            'compatibility': compatibility
        }
    
    def _generate_firmware_id(self, name: str, version: str, channel: str) -> str:
        """Generate unique firmware ID"""
        unique_string = f"{name}_{version}_{channel}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _firmware_exists(self, firmware_id: str) -> bool:
        """Check if firmware already exists in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM firmware WHERE id = ?', (firmware_id,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception as e:
            logger.error(f"Error checking firmware existence: {e}")
            return False
    
    def _record_update_check(self, source: str, found_updates: int, error: str, duration: float):
        """Record update check results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO update_history (source, last_check, found_updates, errors, duration)
                VALUES (?, ?, ?, ?, ?)
            ''', (source, datetime.now(), found_updates, error, duration))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error recording update check: {e}")
    
    async def save_firmware_updates(self, updates: List[Dict[str, Any]]) -> int:
        """Save firmware updates to database"""
        saved_count = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for update in updates:
                cursor.execute('''
                    INSERT OR REPLACE INTO firmware 
                    (id, name, version, chip_type, variant, channel, source, download_url,
                     size, published_at, changelog, features, compatibility, verified, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    update['id'],
                    update['name'],
                    update['version'],
                    update['chip_type'],
                    update['variant'],
                    update['channel'],
                    update['source'],
                    update['download_url'],
                    update.get('size', 0),
                    update.get('published_at'),
                    update.get('changelog', ''),
                    json.dumps(update.get('features', [])),
                    json.dumps(update.get('compatibility', [])),
                    1 if update['source'] == 'github_releases' else 0,  # Auto-verify GitHub releases
                    'available'
                ))
                saved_count += 1
            
            conn.commit()
            conn.close()
            logger.info(f"Saved {saved_count} firmware updates to database")
            
        except Exception as e:
            logger.error(f"Error saving firmware updates: {e}")
        
        return saved_count
    
    def get_firmware_list(self, chip_type: str = None, channel: str = None, 
                         variant: str = None, verified_only: bool = False) -> List[Dict[str, Any]]:
        """Get firmware list with filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT f.*, 
                       COUNT(fd.id) as download_count,
                       AVG(fr.rating) as avg_rating
                FROM firmware f
                LEFT JOIN firmware_downloads fd ON f.id = fd.firmware_id AND fd.success = 1
                LEFT JOIN firmware_ratings fr ON f.id = fr.firmware_id
                WHERE f.status = 'available'
            '''
            params = []
            
            if chip_type:
                query += ' AND f.chip_type = ?'
                params.append(chip_type)
            
            if channel:
                query += ' AND f.channel = ?'
                params.append(channel)
            
            if variant:
                query += ' AND f.variant = ?'
                params.append(variant)
            
            if verified_only:
                query += ' AND f.verified = 1'
            
            query += '''
                GROUP BY f.id
                ORDER BY 
                    CASE f.channel 
                        WHEN 'stable' THEN 1 
                        WHEN 'beta' THEN 2 
                        WHEN 'development' THEN 3 
                    END,
                    f.published_at DESC,
                    download_count DESC
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            firmware_list = []
            for row in rows:
                firmware = {
                    'id': row[0],
                    'name': row[1],
                    'version': row[2],
                    'chip_type': row[3],
                    'variant': row[4],
                    'channel': row[5],
                    'source': row[6],
                    'download_url': row[7],
                    'local_path': row[8],
                    'size': row[9],
                    'md5_hash': row[10],
                    'sha256_hash': row[11],
                    'published_at': row[12],
                    'changelog': row[13],
                    'features': json.loads(row[14]) if row[14] else [],
                    'compatibility': json.loads(row[15]) if row[15] else [],
                    'download_count': row[16],
                    'rating': row[17],
                    'verified': bool(row[18]),
                    'status': row[19],
                    'created_at': row[20],
                    'updated_at': row[21],
                    'total_downloads': row[22] or 0,
                    'avg_rating': row[23] or 0.0
                }
                firmware_list.append(firmware)
            
            conn.close()
            return firmware_list
            
        except Exception as e:
            logger.error(f"Error getting firmware list: {e}")
            return []