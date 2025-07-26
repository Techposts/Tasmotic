import asyncio
import aiohttp
import hashlib
import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class FirmwareCacheManager:
    """Smart caching system for firmware files"""
    
    def __init__(self, firmware_manager):
        self.firmware_manager = firmware_manager
        self.cache_dir = '/opt/app/data/firmware_cache'
        self.db_path = '/opt/app/data/firmware_cache.db'
        self.max_cache_size = 2 * 1024 * 1024 * 1024  # 2GB
        self.cache_retention_days = 30
        
        os.makedirs(self.cache_dir, exist_ok=True)
        self._init_cache_database()
    
    def _init_cache_database(self):
        """Initialize cache database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firmware_cache (
                    firmware_id TEXT PRIMARY KEY,
                    local_path TEXT NOT NULL,
                    download_url TEXT NOT NULL,
                    file_size INTEGER,
                    md5_hash TEXT,
                    sha256_hash TEXT,
                    download_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_size INTEGER,
                    file_count INTEGER,
                    cache_hits INTEGER,
                    cache_misses INTEGER,
                    last_cleanup TIMESTAMP,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Cache database initialized")
        except Exception as e:
            logger.error(f"Cache database initialization error: {e}")
    
    async def download_and_cache_firmware(self, firmware_id: str, 
                                        download_url: str, 
                                        progress_callback=None) -> Optional[str]:
        """Download and cache firmware file"""
        try:
            # Check if already cached
            cached_path = self.get_cached_firmware_path(firmware_id)
            if cached_path and os.path.exists(cached_path):
                self._update_access_time(firmware_id)
                return cached_path
            
            # Create temp file for download
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
            temp_path = temp_file.name
            temp_file.close()
            
            # Download firmware
            logger.info(f"Downloading firmware: {download_url}")
            file_size, md5_hash, sha256_hash = await self._download_file(
                download_url, temp_path, progress_callback
            )
            
            # Move to cache directory
            cache_filename = f"{firmware_id}.bin"
            cache_path = os.path.join(self.cache_dir, cache_filename)
            shutil.move(temp_path, cache_path)
            
            # Verify file integrity
            if await self._verify_firmware_file(cache_path):
                # Add to cache database
                self._add_to_cache_db(
                    firmware_id, cache_path, download_url, 
                    file_size, md5_hash, sha256_hash
                )
                
                # Update firmware manager with local path
                self._update_firmware_local_path(firmware_id, cache_path)
                
                logger.info(f"Firmware cached successfully: {cache_filename}")
                return cache_path
            else:
                logger.error(f"Firmware verification failed: {cache_filename}")
                os.remove(cache_path)
                return None
                
        except Exception as e:
            logger.error(f"Error downloading/caching firmware: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
    
    async def _download_file(self, url: str, local_path: str, 
                           progress_callback=None) -> Tuple[int, str, str]:
        """Download file with progress tracking"""
        file_size = 0
        md5_hasher = hashlib.md5()
        sha256_hasher = hashlib.sha256()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            file_size += len(chunk)
                            
                            # Update hashes
                            md5_hasher.update(chunk)
                            sha256_hasher.update(chunk)
                            
                            # Report progress
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                await progress_callback(progress, downloaded, total_size)
            
            return file_size, md5_hasher.hexdigest(), sha256_hasher.hexdigest()
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    async def _verify_firmware_file(self, file_path: str) -> bool:
        """Verify firmware file integrity"""
        try:
            # Basic file checks
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size < 100000:  # Less than 100KB is suspicious
                logger.warning(f"Firmware file too small: {file_size} bytes")
                return False
            
            # Check for valid firmware header (basic check)
            with open(file_path, 'rb') as f:
                header = f.read(16)
                
                # ESP32 firmware magic
                if header[:4] == b'\xE9\x00\x00\x00':
                    return True
                
                # ESP8266 firmware magic  
                if header[0] == 0xE9:
                    return True
                
                logger.warning("No valid firmware magic found")
                return False
                
        except Exception as e:
            logger.error(f"Firmware verification error: {e}")
            return False
    
    def _add_to_cache_db(self, firmware_id: str, local_path: str, 
                        download_url: str, file_size: int, 
                        md5_hash: str, sha256_hash: str):
        """Add firmware to cache database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO firmware_cache
                (firmware_id, local_path, download_url, file_size, 
                 md5_hash, sha256_hash, last_accessed, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                firmware_id, local_path, download_url, file_size,
                md5_hash, sha256_hash, datetime.now(), True
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error adding to cache database: {e}")
    
    def get_cached_firmware_path(self, firmware_id: str) -> Optional[str]:
        """Get cached firmware path if available"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT local_path FROM firmware_cache 
                WHERE firmware_id = ? AND verified = 1
            ''', (firmware_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and os.path.exists(result[0]):
                return result[0]
            else:
                # Clean up stale cache entry
                if result:
                    self._remove_from_cache_db(firmware_id)
                return None
                
        except Exception as e:
            logger.error(f"Error getting cached firmware path: {e}")
            return None
    
    def _update_access_time(self, firmware_id: str):
        """Update last accessed time for cache entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE firmware_cache 
                SET last_accessed = ?, download_count = download_count + 1
                WHERE firmware_id = ?
            ''', (datetime.now(), firmware_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating access time: {e}")
    
    def _update_firmware_local_path(self, firmware_id: str, local_path: str):
        """Update firmware manager with local path"""
        try:
            conn = sqlite3.connect(self.firmware_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE firmware SET local_path = ?, updated_at = ?
                WHERE id = ?
            ''', (local_path, datetime.now(), firmware_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating firmware local path: {e}")
    
    async def cleanup_cache(self, force: bool = False):
        """Clean up old and unused cache files"""
        try:
            current_size = self._get_cache_size()
            logger.info(f"Current cache size: {current_size / 1024 / 1024:.1f} MB")
            
            # Check if cleanup is needed
            if not force and current_size < self.max_cache_size * 0.8:
                return
            
            logger.info("Starting cache cleanup...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get files to remove (oldest first, least accessed)
            cutoff_date = datetime.now() - timedelta(days=self.cache_retention_days)
            
            cursor.execute('''
                SELECT firmware_id, local_path, file_size 
                FROM firmware_cache
                WHERE last_accessed < ? OR download_count = 0
                ORDER BY last_accessed ASC, download_count ASC
            ''', (cutoff_date,))
            
            candidates = cursor.fetchall()
            removed_size = 0
            removed_count = 0
            
            for firmware_id, local_path, file_size in candidates:
                if current_size - removed_size < self.max_cache_size * 0.7:
                    break
                
                try:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    
                    self._remove_from_cache_db(firmware_id)
                    removed_size += file_size or 0
                    removed_count += 1
                    
                    logger.debug(f"Removed cached firmware: {firmware_id}")
                    
                except Exception as e:
                    logger.error(f"Error removing cached file {local_path}: {e}")
            
            conn.close()
            
            logger.info(f"Cache cleanup completed: removed {removed_count} files, "
                       f"freed {removed_size / 1024 / 1024:.1f} MB")
            
            # Record cleanup stats
            self._record_cleanup_stats(removed_count, removed_size)
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    def _get_cache_size(self) -> int:
        """Get total cache size in bytes"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error calculating cache size: {e}")
        
        return total_size
    
    def _remove_from_cache_db(self, firmware_id: str):
        """Remove firmware from cache database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM firmware_cache WHERE firmware_id = ?', (firmware_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error removing from cache database: {e}")
    
    def _record_cleanup_stats(self, removed_count: int, removed_size: int):
        """Record cleanup statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current stats
            total_size = self._get_cache_size()
            file_count = len([f for f in os.listdir(self.cache_dir) if f.endswith('.bin')])
            
            cursor.execute('''
                INSERT INTO cache_stats 
                (total_size, file_count, last_cleanup)
                VALUES (?, ?, ?)
            ''', (total_size, file_count, datetime.now()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error recording cleanup stats: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            stats = {
                'total_size': self._get_cache_size(),
                'file_count': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'last_cleanup': None
            }
            
            # Count files
            stats['file_count'] = len([f for f in os.listdir(self.cache_dir) 
                                     if f.endswith('.bin')])
            
            # Get database stats
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT SUM(download_count) FROM firmware_cache')
            result = cursor.fetchone()
            stats['total_downloads'] = result[0] or 0
            
            cursor.execute('SELECT last_cleanup FROM cache_stats ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()
            if result:
                stats['last_cleanup'] = result[0]
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

class FirmwareRecommendationEngine:
    """AI-powered firmware recommendation system"""
    
    def __init__(self, firmware_manager):
        self.firmware_manager = firmware_manager
        self.db_path = '/opt/app/data/recommendations.db'
        self._init_recommendations_database()
    
    def _init_recommendations_database(self):
        """Initialize recommendations database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT,
                    chip_type TEXT,
                    flash_size INTEGER,
                    hardware_revision TEXT,
                    mac_prefix TEXT,
                    current_firmware TEXT,
                    gpio_config TEXT,
                    success_firmware TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recommendation_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_fingerprint TEXT,
                    recommended_firmware TEXT,
                    actual_firmware TEXT,
                    success BOOLEAN,
                    user_rating INTEGER,
                    feedback_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Recommendations database initialization error: {e}")
    
    def get_firmware_recommendations(self, device_info: Dict[str, Any], 
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """Get AI-powered firmware recommendations"""
        try:
            recommendations = []
            
            # Get device fingerprint
            fingerprint = self._create_device_fingerprint(device_info)
            
            # Rule-based recommendations
            rule_based = self._get_rule_based_recommendations(fingerprint, limit)
            recommendations.extend(rule_based)
            
            # Collaborative filtering
            collaborative = self._get_collaborative_recommendations(fingerprint, limit)
            recommendations.extend(collaborative)
            
            # Popular firmware for chip type
            popular = self._get_popular_recommendations(fingerprint, limit)
            recommendations.extend(popular)
            
            # Remove duplicates and sort by confidence
            seen = set()
            unique_recommendations = []
            
            for rec in recommendations:
                if rec['firmware_id'] not in seen:
                    seen.add(rec['firmware_id'])
                    unique_recommendations.append(rec)
            
            # Sort by confidence score
            unique_recommendations.sort(key=lambda x: x['confidence'], reverse=True)
            
            return unique_recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting firmware recommendations: {e}")
            return []
    
    def _create_device_fingerprint(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create device fingerprint for matching"""
        return {
            'chip_type': device_info.get('chip_type', ''),
            'flash_size': device_info.get('flash_size', 0),
            'hardware_revision': device_info.get('hardware', ''),
            'mac_prefix': device_info.get('mac', '')[:8] if device_info.get('mac') else '',
            'current_firmware': device_info.get('current_firmware', ''),
            'gpio_config': json.dumps(device_info.get('gpio_config', {}))
        }
    
    def _get_rule_based_recommendations(self, fingerprint: Dict[str, Any], 
                                      limit: int) -> List[Dict[str, Any]]:
        """Get rule-based firmware recommendations"""
        recommendations = []
        
        # Get available firmware for chip type
        firmware_list = self.firmware_manager.get_firmware_list(
            chip_type=fingerprint['chip_type'],
            verified_only=True
        )
        
        for firmware in firmware_list[:limit]:
            confidence = 0.5  # Base confidence
            reasons = []
            
            # Boost confidence for exact hardware matches
            if fingerprint['hardware_revision'] in firmware.get('compatibility', []):
                confidence += 0.3
                reasons.append("Hardware compatibility")
            
            # Boost confidence for stable channel
            if firmware['channel'] == 'stable':
                confidence += 0.2
                reasons.append("Stable release")
            
            # Boost confidence for popular firmware
            if firmware.get('total_downloads', 0) > 1000:
                confidence += 0.1
                reasons.append("Popular choice")
            
            # Boost confidence for high ratings
            if firmware.get('avg_rating', 0) > 4.0:
                confidence += 0.1
                reasons.append("Highly rated")
            
            recommendations.append({
                'firmware_id': firmware['id'],
                'firmware': firmware,
                'confidence': min(confidence, 1.0),
                'reasons': reasons,
                'recommendation_type': 'rule_based'
            })
        
        return recommendations
    
    def _get_collaborative_recommendations(self, fingerprint: Dict[str, Any], 
                                         limit: int) -> List[Dict[str, Any]]:
        """Get collaborative filtering recommendations"""
        recommendations = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find similar devices
            cursor.execute('''
                SELECT success_firmware, COUNT(*) as usage_count
                FROM device_fingerprints
                WHERE chip_type = ? AND hardware_revision = ?
                GROUP BY success_firmware
                ORDER BY usage_count DESC
                LIMIT ?
            ''', (fingerprint['chip_type'], fingerprint['hardware_revision'], limit))
            
            similar_devices = cursor.fetchall()
            conn.close()
            
            for firmware_id, usage_count in similar_devices:
                firmware = self._get_firmware_by_id(firmware_id)
                if firmware:
                    confidence = min(0.3 + (usage_count * 0.1), 0.8)
                    
                    recommendations.append({
                        'firmware_id': firmware_id,
                        'firmware': firmware,
                        'confidence': confidence,
                        'reasons': [f"Used successfully by {usage_count} similar devices"],
                        'recommendation_type': 'collaborative'
                    })
            
        except Exception as e:
            logger.error(f"Error in collaborative recommendations: {e}")
        
        return recommendations
    
    def _get_popular_recommendations(self, fingerprint: Dict[str, Any], 
                                   limit: int) -> List[Dict[str, Any]]:
        """Get popular firmware recommendations"""
        recommendations = []
        
        # Get most downloaded firmware for chip type
        firmware_list = self.firmware_manager.get_firmware_list(
            chip_type=fingerprint['chip_type'],
            verified_only=True
        )
        
        # Sort by download count
        popular_firmware = sorted(
            firmware_list, 
            key=lambda x: x.get('total_downloads', 0), 
            reverse=True
        )
        
        for firmware in popular_firmware[:limit]:
            confidence = 0.2 + min(firmware.get('total_downloads', 0) / 10000, 0.3)
            
            recommendations.append({
                'firmware_id': firmware['id'],
                'firmware': firmware,
                'confidence': confidence,
                'reasons': [f"Popular choice ({firmware.get('total_downloads', 0)} downloads)"],
                'recommendation_type': 'popular'
            })
        
        return recommendations
    
    def _get_firmware_by_id(self, firmware_id: str) -> Optional[Dict[str, Any]]:
        """Get firmware details by ID"""
        firmware_list = self.firmware_manager.get_firmware_list()
        for firmware in firmware_list:
            if firmware['id'] == firmware_id:
                return firmware
        return None
    
    def record_recommendation_feedback(self, device_fingerprint: str, 
                                     recommended_firmware: str,
                                     actual_firmware: str, 
                                     success: bool,
                                     user_rating: int = None,
                                     feedback_text: str = None):
        """Record feedback on recommendations for learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO recommendation_feedback
                (device_fingerprint, recommended_firmware, actual_firmware, 
                 success, user_rating, feedback_text)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                device_fingerprint, recommended_firmware, actual_firmware,
                success, user_rating, feedback_text
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded recommendation feedback: {success}")
            
        except Exception as e:
            logger.error(f"Error recording recommendation feedback: {e}")