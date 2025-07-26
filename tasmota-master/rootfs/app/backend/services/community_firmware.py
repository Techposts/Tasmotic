import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from werkzeug.utils import secure_filename
import magic
import zipfile
import requests

logger = logging.getLogger(__name__)

class CommunityFirmwareManager:
    """Manage user-uploaded and community firmware"""
    
    def __init__(self, firmware_manager):
        self.firmware_manager = firmware_manager
        self.db_path = '/opt/app/data/community_firmware.db'
        self.upload_dir = '/opt/app/data/community_uploads'
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {'.bin', '.gz'}
        
        os.makedirs(self.upload_dir, exist_ok=True)
        self._init_community_database()
    
    def _init_community_database(self):
        """Initialize community firmware database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # User-uploaded firmware
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS community_firmware (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    display_name TEXT,
                    description TEXT,
                    version TEXT,
                    chip_type TEXT NOT NULL,
                    variant TEXT,
                    author_name TEXT,
                    author_email TEXT,
                    author_github TEXT,
                    upload_source TEXT DEFAULT 'user_upload',
                    local_path TEXT NOT NULL,
                    file_size INTEGER,
                    md5_hash TEXT,
                    sha256_hash TEXT,
                    features TEXT,
                    compatibility TEXT,
                    gpio_template TEXT,
                    build_info TEXT,
                    source_code_url TEXT,
                    documentation_url TEXT,
                    license TEXT DEFAULT 'Unknown',
                    tags TEXT,
                    status TEXT DEFAULT 'pending',
                    verification_notes TEXT,
                    download_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    rating_count INTEGER DEFAULT 0,
                    report_count INTEGER DEFAULT 0,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP,
                    verified_by TEXT
                )
            ''')
            
            # Community ratings and reviews
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS community_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firmware_id TEXT,
                    user_identifier TEXT,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    review_text TEXT,
                    device_info TEXT,
                    flash_success BOOLEAN,
                    issues_encountered TEXT,
                    recommended BOOLEAN,
                    helpful_votes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (firmware_id) REFERENCES community_firmware (id)
                )
            ''')
            
            # Firmware reports (for spam/malware)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firmware_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firmware_id TEXT,
                    reporter_identifier TEXT,
                    report_type TEXT CHECK (report_type IN ('spam', 'malware', 'inappropriate', 'copyright', 'other')),
                    report_reason TEXT,
                    additional_info TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (firmware_id) REFERENCES community_firmware (id)
                )
            ''')
            
            # Community collections
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firmware_collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    author_name TEXT,
                    author_github TEXT,
                    tags TEXT,
                    firmware_list TEXT,
                    download_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    public BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Community firmware database initialized")
        except Exception as e:
            logger.error(f"Community database initialization error: {e}")
    
    async def upload_firmware(self, file_data: bytes, filename: str, 
                            metadata: Dict[str, Any], 
                            author_info: Dict[str, Any]) -> Dict[str, Any]:
        """Upload and process community firmware"""
        try:
            # Validate file
            validation_result = await self._validate_firmware_upload(
                file_data, filename, metadata
            )
            
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'details': validation_result.get('details', {})
                }
            
            # Generate unique ID
            firmware_id = self._generate_community_firmware_id(filename, metadata)
            
            # Save file
            secure_name = secure_filename(filename)
            file_extension = os.path.splitext(secure_name)[1].lower()
            local_filename = f"{firmware_id}{file_extension}"
            local_path = os.path.join(self.upload_dir, local_filename)
            
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            # Calculate hashes
            md5_hash = hashlib.md5(file_data).hexdigest()
            sha256_hash = hashlib.sha256(file_data).hexdigest()
            
            # Parse firmware for additional metadata
            firmware_analysis = await self._analyze_firmware_file(local_path)
            
            # Save to database
            community_firmware = {
                'id': firmware_id,
                'name': secure_name,
                'display_name': metadata.get('display_name', secure_name),
                'description': metadata.get('description', ''),
                'version': metadata.get('version', 'custom'),
                'chip_type': metadata.get('chip_type', validation_result.get('chip_type', 'Unknown')),
                'variant': metadata.get('variant', 'custom'),
                'author_name': author_info.get('name', 'Anonymous'),
                'author_email': author_info.get('email', ''),
                'author_github': author_info.get('github', ''),
                'local_path': local_path,
                'file_size': len(file_data),
                'md5_hash': md5_hash,
                'sha256_hash': sha256_hash,
                'features': json.dumps(metadata.get('features', [])),
                'compatibility': json.dumps(metadata.get('compatibility', [])),
                'gpio_template': json.dumps(metadata.get('gpio_template', {})),
                'build_info': json.dumps(firmware_analysis.get('build_info', {})),
                'source_code_url': metadata.get('source_code_url', ''),
                'documentation_url': metadata.get('documentation_url', ''),
                'license': metadata.get('license', 'Unknown'),
                'tags': json.dumps(metadata.get('tags', [])),
                'status': 'pending'  # Requires review
            }
            
            self._save_community_firmware(community_firmware)
            
            logger.info(f"Community firmware uploaded: {firmware_id}")
            
            return {
                'success': True,
                'firmware_id': firmware_id,
                'status': 'uploaded',
                'message': 'Firmware uploaded successfully and is pending review'
            }
            
        except Exception as e:
            logger.error(f"Error uploading community firmware: {e}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    async def _validate_firmware_upload(self, file_data: bytes, filename: str, 
                                      metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate uploaded firmware file"""
        try:
            # Check file size
            if len(file_data) > self.max_file_size:
                return {
                    'valid': False,
                    'error': f'File too large. Maximum size is {self.max_file_size / 1024 / 1024:.1f}MB'
                }
            
            if len(file_data) < 100000:  # Less than 100KB
                return {
                    'valid': False,
                    'error': 'File too small to be valid firmware'
                }
            
            # Check file extension
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension not in self.allowed_extensions:
                return {
                    'valid': False,
                    'error': f'Invalid file type. Allowed: {", ".join(self.allowed_extensions)}'
                }
            
            # Check for duplicate (by hash)
            file_hash = hashlib.sha256(file_data).hexdigest()
            if self._firmware_hash_exists(file_hash):
                return {
                    'valid': False,
                    'error': 'This firmware file has already been uploaded'
                }
            
            # Basic firmware validation
            validation_result = await self._validate_firmware_binary(file_data)
            if not validation_result['valid']:
                return validation_result
            
            # Scan for malware (basic checks)
            malware_check = await self._scan_for_malware(file_data)
            if not malware_check['clean']:
                return {
                    'valid': False,
                    'error': 'Security scan failed',
                    'details': malware_check.get('details', {})
                }
            
            return {
                'valid': True,
                'chip_type': validation_result.get('chip_type'),
                'estimated_size': validation_result.get('estimated_size')
            }
            
        except Exception as e:
            logger.error(f"Firmware validation error: {e}")
            return {
                'valid': False,
                'error': f'Validation failed: {str(e)}'
            }
    
    async def _validate_firmware_binary(self, file_data: bytes) -> Dict[str, Any]:
        """Validate firmware binary format"""
        try:
            # Check ESP32 firmware magic
            if len(file_data) >= 4 and file_data[:4] == b'\xE9\x00\x00\x00':
                return {
                    'valid': True,
                    'chip_type': 'ESP32',
                    'format': 'ESP32 firmware'
                }
            
            # Check ESP8266 firmware magic
            if len(file_data) >= 1 and file_data[0] == 0xE9:
                return {
                    'valid': True,
                    'chip_type': 'ESP8266',
                    'format': 'ESP8266 firmware'
                }
            
            # Check for compressed firmware
            if file_data[:2] == b'\x1f\x8b':  # GZIP magic
                return {
                    'valid': True,
                    'chip_type': 'Unknown',
                    'format': 'Compressed firmware'
                }
            
            return {
                'valid': False,
                'error': 'Invalid firmware format - no valid magic bytes found'
            }
            
        except Exception as e:
            logger.error(f"Binary validation error: {e}")
            return {
                'valid': False,
                'error': f'Binary validation failed: {str(e)}'
            }
    
    async def _scan_for_malware(self, file_data: bytes) -> Dict[str, Any]:
        """Basic malware scanning"""
        try:
            # Check for suspicious patterns
            suspicious_patterns = [
                b'eval(',
                b'exec(',
                b'system(',
                b'shell_exec(',
                b'<?php',
                b'<script',
                b'javascript:',
                b'<iframe'
            ]
            
            for pattern in suspicious_patterns:
                if pattern in file_data:
                    return {
                        'clean': False,
                        'details': {
                            'reason': 'Suspicious content detected',
                            'pattern': pattern.decode('utf-8', errors='ignore')
                        }
                    }
            
            # Check file entropy (high entropy might indicate encryption/packing)
            import math
            byte_counts = [0] * 256
            for byte in file_data[:10000]:  # Check first 10KB
                byte_counts[byte] += 1
            
            entropy = 0
            length = min(len(file_data), 10000)
            for count in byte_counts:
                if count > 0:
                    freq = count / length
                    entropy -= freq * math.log2(freq)
            
            # Firmware should have moderate entropy
            if entropy > 7.5:
                logger.warning(f"High entropy detected: {entropy}")
                # Don't reject, just log
            
            return {
                'clean': True,
                'entropy': entropy
            }
            
        except Exception as e:
            logger.error(f"Malware scan error: {e}")
            return {
                'clean': True,  # Allow on scan error
                'error': str(e)
            }
    
    async def _analyze_firmware_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze firmware file for metadata"""
        try:
            analysis = {
                'build_info': {},
                'strings': [],
                'estimated_features': []
            }
            
            # Read file in chunks to find strings
            with open(file_path, 'rb') as f:
                chunk_size = 8192
                strings = []
                current_string = b""
                
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    for byte in chunk:
                        if 32 <= byte <= 126:  # Printable ASCII
                            current_string += bytes([byte])
                        else:
                            if len(current_string) >= 4:
                                strings.append(current_string.decode('ascii', errors='ignore'))
                            current_string = b""
                
                # Look for version strings
                version_patterns = ['Tasmota', 'ESP8266', 'ESP32', 'Arduino']
                build_strings = [s for s in strings if any(p in s for p in version_patterns)]
                analysis['strings'] = build_strings[:20]  # Keep first 20
                
                # Estimate features based on strings
                feature_indicators = {
                    'MQTT': ['mqtt', 'broker', 'publish', 'subscribe'],
                    'HTTP': ['http', 'web', 'server', 'client'],
                    'WiFi': ['wifi', 'ssid', 'password', 'connect'],
                    'Sensors': ['dht', 'ds18b20', 'bmp', 'sensor'],
                    'Display': ['display', 'oled', 'lcd', 'ssd1306'],
                    'IR': ['infrared', 'remote', 'ir_send', 'ir_recv']
                }
                
                found_features = []
                for feature, indicators in feature_indicators.items():
                    if any(any(ind in s.lower() for ind in indicators) for s in strings):
                        found_features.append(feature)
                
                analysis['estimated_features'] = found_features
            
            return analysis
            
        except Exception as e:
            logger.error(f"Firmware analysis error: {e}")
            return {'build_info': {}, 'strings': [], 'estimated_features': []}
    
    def _generate_community_firmware_id(self, filename: str, metadata: Dict[str, Any]) -> str:
        """Generate unique ID for community firmware"""
        unique_string = f"{filename}_{metadata.get('version', 'custom')}_{datetime.now().isoformat()}"
        return f"community_{hashlib.md5(unique_string.encode()).hexdigest()}"
    
    def _firmware_hash_exists(self, file_hash: str) -> bool:
        """Check if firmware with this hash already exists"""
        try:
            # Check official firmware
            conn = sqlite3.connect(self.firmware_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM firmware WHERE sha256_hash = ?', (file_hash,))
            if cursor.fetchone():
                conn.close()
                return True
            conn.close()
            
            # Check community firmware
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM community_firmware WHERE sha256_hash = ?', (file_hash,))
            exists = cursor.fetchone() is not None
            conn.close()
            
            return exists
            
        except Exception as e:
            logger.error(f"Error checking firmware hash: {e}")
            return False
    
    def _save_community_firmware(self, firmware_data: Dict[str, Any]):
        """Save community firmware to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO community_firmware
                (id, name, display_name, description, version, chip_type, variant,
                 author_name, author_email, author_github, local_path, file_size,
                 md5_hash, sha256_hash, features, compatibility, gpio_template,
                 build_info, source_code_url, documentation_url, license, tags, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                firmware_data['id'],
                firmware_data['name'],
                firmware_data['display_name'],
                firmware_data['description'],
                firmware_data['version'],
                firmware_data['chip_type'],
                firmware_data['variant'],
                firmware_data['author_name'],
                firmware_data['author_email'],
                firmware_data['author_github'],
                firmware_data['local_path'],
                firmware_data['file_size'],
                firmware_data['md5_hash'],
                firmware_data['sha256_hash'],
                firmware_data['features'],
                firmware_data['compatibility'],
                firmware_data['gpio_template'],
                firmware_data['build_info'],
                firmware_data['source_code_url'],
                firmware_data['documentation_url'],
                firmware_data['license'],
                firmware_data['tags'],
                firmware_data['status']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving community firmware: {e}")
            raise
    
    def get_community_firmware_list(self, chip_type: str = None, 
                                   status: str = 'approved', 
                                   tags: List[str] = None,
                                   author: str = None,
                                   limit: int = 50) -> List[Dict[str, Any]]:
        """Get community firmware list with filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT cf.*, 
                       AVG(cr.rating) as avg_rating,
                       COUNT(cr.id) as rating_count,
                       cf.download_count
                FROM community_firmware cf
                LEFT JOIN community_ratings cr ON cf.id = cr.firmware_id
                WHERE 1=1
            '''
            params = []
            
            if chip_type:
                query += ' AND cf.chip_type = ?'
                params.append(chip_type)
            
            if status:
                query += ' AND cf.status = ?'
                params.append(status)
            
            if author:
                query += ' AND (cf.author_name LIKE ? OR cf.author_github LIKE ?)'
                params.extend([f'%{author}%', f'%{author}%'])
            
            if tags:
                for tag in tags:
                    query += ' AND cf.tags LIKE ?'
                    params.append(f'%{tag}%')
            
            query += '''
                GROUP BY cf.id
                ORDER BY avg_rating DESC, cf.download_count DESC, cf.uploaded_at DESC
                LIMIT ?
            '''
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            firmware_list = []
            for row in rows:
                firmware = {
                    'id': row[0],
                    'name': row[1],
                    'display_name': row[2],
                    'description': row[3],
                    'version': row[4],
                    'chip_type': row[5],
                    'variant': row[6],
                    'author_name': row[7],
                    'author_email': row[8],
                    'author_github': row[9],
                    'upload_source': row[10],
                    'local_path': row[11],
                    'file_size': row[12],
                    'md5_hash': row[13],
                    'sha256_hash': row[14],
                    'features': json.loads(row[15]) if row[15] else [],
                    'compatibility': json.loads(row[16]) if row[16] else [],
                    'gpio_template': json.loads(row[17]) if row[17] else {},
                    'build_info': json.loads(row[18]) if row[18] else {},
                    'source_code_url': row[19],
                    'documentation_url': row[20],
                    'license': row[21],
                    'tags': json.loads(row[22]) if row[22] else [],
                    'status': row[23],
                    'verification_notes': row[24],
                    'download_count': row[25],
                    'uploaded_at': row[29],
                    'verified_at': row[30],
                    'verified_by': row[31],
                    'avg_rating': row[32] or 0.0,
                    'rating_count': row[33] or 0
                }
                firmware_list.append(firmware)
            
            conn.close()
            return firmware_list
            
        except Exception as e:
            logger.error(f"Error getting community firmware list: {e}")
            return []
    
    def submit_firmware_rating(self, firmware_id: str, user_identifier: str,
                             rating: int, review_text: str = None,
                             device_info: Dict[str, Any] = None,
                             flash_success: bool = None) -> Dict[str, Any]:
        """Submit rating and review for community firmware"""
        try:
            if not 1 <= rating <= 5:
                return {
                    'success': False,
                    'error': 'Rating must be between 1 and 5'
                }
            
            # Check if user already rated this firmware
            if self._user_already_rated(firmware_id, user_identifier):
                return {
                    'success': False,
                    'error': 'You have already rated this firmware'
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO community_ratings
                (firmware_id, user_identifier, rating, review_text, device_info, flash_success)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                firmware_id, user_identifier, rating, review_text,
                json.dumps(device_info) if device_info else None,
                flash_success
            ))
            
            # Update firmware average rating
            cursor.execute('''
                UPDATE community_firmware 
                SET rating = (
                    SELECT AVG(rating) FROM community_ratings 
                    WHERE firmware_id = ?
                ),
                rating_count = (
                    SELECT COUNT(*) FROM community_ratings 
                    WHERE firmware_id = ?
                )
                WHERE id = ?
            ''', (firmware_id, firmware_id, firmware_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Rating submitted for firmware {firmware_id}: {rating} stars")
            
            return {
                'success': True,
                'message': 'Rating submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error submitting firmware rating: {e}")
            return {
                'success': False,
                'error': f'Failed to submit rating: {str(e)}'
            }
    
    def _user_already_rated(self, firmware_id: str, user_identifier: str) -> bool:
        """Check if user already rated this firmware"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id FROM community_ratings 
                WHERE firmware_id = ? AND user_identifier = ?
            ''', (firmware_id, user_identifier))
            
            exists = cursor.fetchone() is not None
            conn.close()
            
            return exists
            
        except Exception as e:
            logger.error(f"Error checking user rating: {e}")
            return False
    
    def report_firmware(self, firmware_id: str, reporter_identifier: str,
                       report_type: str, report_reason: str,
                       additional_info: str = None) -> Dict[str, Any]:
        """Report firmware for various issues"""
        try:
            valid_report_types = ['spam', 'malware', 'inappropriate', 'copyright', 'other']
            if report_type not in valid_report_types:
                return {
                    'success': False,
                    'error': f'Invalid report type. Must be one of: {", ".join(valid_report_types)}'
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO firmware_reports
                (firmware_id, reporter_identifier, report_type, report_reason, additional_info)
                VALUES (?, ?, ?, ?, ?)
            ''', (firmware_id, reporter_identifier, report_type, report_reason, additional_info))
            
            # Update report count
            cursor.execute('''
                UPDATE community_firmware 
                SET report_count = (
                    SELECT COUNT(*) FROM firmware_reports 
                    WHERE firmware_id = ? AND status = 'pending'
                )
                WHERE id = ?
            ''', (firmware_id, firmware_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Firmware reported: {firmware_id} - {report_type}")
            
            return {
                'success': True,
                'message': 'Report submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error reporting firmware: {e}")
            return {
                'success': False,
                'error': f'Failed to submit report: {str(e)}'
            }