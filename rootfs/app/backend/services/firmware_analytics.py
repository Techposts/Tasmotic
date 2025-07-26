import asyncio
import json
import logging
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import joblib
import os

logger = logging.getLogger(__name__)

class FirmwareAnalyticsEngine:
    """Advanced analytics and AI matching for firmware"""
    
    def __init__(self, firmware_manager, community_manager):
        self.firmware_manager = firmware_manager
        self.community_manager = community_manager
        self.db_path = '/opt/app/data/firmware_analytics.db'
        self.models_dir = '/opt/app/data/models'
        
        os.makedirs(self.models_dir, exist_ok=True)
        self._init_analytics_database()
        self._load_or_create_models()
    
    def _init_analytics_database(self):
        """Initialize analytics database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Device usage patterns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_usage_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_fingerprint TEXT,
                    firmware_id TEXT,
                    success_rate REAL,
                    usage_duration INTEGER,
                    performance_score REAL,
                    stability_score REAL,
                    feature_usage TEXT,
                    issues_reported TEXT,
                    recommendation_score REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Firmware compatibility matrix
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firmware_compatibility (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firmware_id TEXT,
                    chip_type TEXT,
                    hardware_pattern TEXT,
                    compatibility_score REAL,
                    success_count INTEGER,
                    failure_count INTEGER,
                    last_success TIMESTAMP,
                    last_failure TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            # AI model predictions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_fingerprint TEXT,
                    recommended_firmware TEXT,
                    confidence_score REAL,
                    prediction_features TEXT,
                    model_version TEXT,
                    actual_firmware TEXT,
                    prediction_accuracy REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP
                )
            ''')
            
            # Analytics insights
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight_type TEXT,
                    insight_data TEXT,
                    confidence REAL,
                    impact_score REAL,
                    actionable BOOLEAN,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Analytics database initialized")
        except Exception as e:
            logger.error(f"Analytics database initialization error: {e}")
    
    def _load_or_create_models(self):
        """Load existing ML models or create new ones"""
        try:
            self.vectorizer_path = os.path.join(self.models_dir, 'device_vectorizer.pkl')
            self.compatibility_model_path = os.path.join(self.models_dir, 'compatibility_model.pkl')
            self.clustering_model_path = os.path.join(self.models_dir, 'device_clusters.pkl')
            
            # Load or create TF-IDF vectorizer for device descriptions
            if os.path.exists(self.vectorizer_path):
                self.device_vectorizer = joblib.load(self.vectorizer_path)
            else:
                self.device_vectorizer = TfidfVectorizer(
                    max_features=1000,
                    stop_words='english',
                    ngram_range=(1, 2)
                )
            
            # Load or create device clustering model
            if os.path.exists(self.clustering_model_path):
                self.device_clusters = joblib.load(self.clustering_model_path)
            else:
                self.device_clusters = KMeans(n_clusters=20, random_state=42)
            
            logger.info("ML models loaded/initialized")
        except Exception as e:
            logger.error(f"Error loading ML models: {e}")
    
    async def analyze_device_compatibility(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Deep analysis of device compatibility with available firmware"""
        try:
            analysis = {
                'device_cluster': None,
                'similar_devices': [],
                'compatibility_scores': {},
                'recommended_firmware': [],
                'risk_assessment': {},
                'confidence_metrics': {}
            }
            
            # Create device feature vector
            device_vector = self._create_device_feature_vector(device_info)
            
            # Determine device cluster
            if hasattr(self.device_clusters, 'predict'):
                cluster = self.device_clusters.predict([device_vector])[0]
                analysis['device_cluster'] = int(cluster)
            
            # Find similar devices
            similar_devices = await self._find_similar_devices(device_info, limit=10)
            analysis['similar_devices'] = similar_devices
            
            # Calculate compatibility scores for all firmware
            firmware_list = self.firmware_manager.get_firmware_list(
                chip_type=device_info.get('chip_type')
            )
            community_firmware = self.community_manager.get_community_firmware_list(
                chip_type=device_info.get('chip_type'),
                status='approved'
            )
            
            all_firmware = firmware_list + community_firmware
            
            for firmware in all_firmware:
                compatibility_score = await self._calculate_firmware_compatibility(
                    device_info, firmware
                )
                analysis['compatibility_scores'][firmware['id']] = compatibility_score
            
            # Get top recommendations
            sorted_firmware = sorted(
                all_firmware,
                key=lambda f: analysis['compatibility_scores'].get(f['id'], {}).get('total_score', 0),
                reverse=True
            )
            
            analysis['recommended_firmware'] = sorted_firmware[:5]
            
            # Risk assessment
            analysis['risk_assessment'] = await self._assess_flashing_risks(
                device_info, analysis['recommended_firmware']
            )
            
            # Confidence metrics
            analysis['confidence_metrics'] = self._calculate_confidence_metrics(
                device_info, similar_devices, analysis['compatibility_scores']
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in device compatibility analysis: {e}")
            return {}
    
    def _create_device_feature_vector(self, device_info: Dict[str, Any]) -> List[float]:
        """Create numerical feature vector from device information"""
        try:
            features = []
            
            # Chip type encoding
            chip_encodings = {'ESP32': 1.0, 'ESP8266': 0.5, 'Unknown': 0.0}
            features.append(chip_encodings.get(device_info.get('chip_type', 'Unknown'), 0.0))
            
            # Flash size encoding (normalize to 0-1)
            flash_size = device_info.get('flash_size', 0)
            if isinstance(flash_size, str):
                # Parse flash size string like "4MB"
                size_match = re.search(r'(\d+)', flash_size)
                flash_size = int(size_match.group(1)) if size_match else 0
            features.append(min(flash_size / 16.0, 1.0))  # Normalize with 16MB max
            
            # Hardware revision hash (simple numeric encoding)
            hardware_rev = device_info.get('hardware', '')
            hardware_hash = sum(ord(c) for c in hardware_rev) % 100 if hardware_rev else 0
            features.append(hardware_hash / 100.0)
            
            # MAC prefix encoding (manufacturer indicator)
            mac = device_info.get('mac', '')
            if mac and len(mac) >= 8:
                mac_prefix = mac[:8].replace(':', '')
                try:
                    mac_numeric = int(mac_prefix, 16) % 10000
                    features.append(mac_numeric / 10000.0)
                except ValueError:
                    features.append(0.0)
            else:
                features.append(0.0)
            
            # Current firmware version encoding
            current_fw = device_info.get('current_firmware', '')
            if 'tasmota' in current_fw.lower():
                features.append(1.0)
            elif current_fw:
                features.append(0.5)
            else:
                features.append(0.0)
            
            # GPIO configuration complexity
            gpio_config = device_info.get('gpio_config', {})
            gpio_complexity = len(gpio_config) / 20.0  # Normalize by max expected GPIO count
            features.append(min(gpio_complexity, 1.0))
            
            # Ensure fixed feature vector size
            while len(features) < 10:
                features.append(0.0)
            
            return features[:10]  # Fixed size of 10 features
            
        except Exception as e:
            logger.error(f"Error creating device feature vector: {e}")
            return [0.0] * 10
    
    async def _find_similar_devices(self, device_info: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Find devices similar to the given device"""
        try:
            target_vector = self._create_device_feature_vector(device_info)
            similar_devices = []
            
            # Get device usage patterns from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT device_fingerprint, firmware_id, success_rate, 
                       performance_score, stability_score
                FROM device_usage_patterns
                WHERE success_rate > 0.7
                ORDER BY last_updated DESC
                LIMIT 100
            ''')
            
            patterns = cursor.fetchall()
            conn.close()
            
            # Calculate similarity for each device pattern
            for pattern in patterns:
                try:
                    fingerprint_data = json.loads(pattern[0])
                    pattern_vector = self._create_device_feature_vector(fingerprint_data)
                    
                    # Calculate cosine similarity
                    similarity = cosine_similarity([target_vector], [pattern_vector])[0][0]
                    
                    if similarity > 0.7:  # Threshold for similarity
                        similar_devices.append({
                            'device_fingerprint': fingerprint_data,
                            'firmware_id': pattern[1],
                            'success_rate': pattern[2],
                            'performance_score': pattern[3],
                            'stability_score': pattern[4],
                            'similarity_score': float(similarity)
                        })
                
                except (json.JSONDecodeError, ValueError) as e:
                    continue
            
            # Sort by similarity and return top results
            similar_devices.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_devices[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar devices: {e}")
            return []
    
    async def _calculate_firmware_compatibility(self, device_info: Dict[str, Any], 
                                              firmware: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate detailed compatibility score between device and firmware"""
        try:
            scores = {
                'chip_compatibility': 0.0,
                'hardware_compatibility': 0.0,
                'feature_compatibility': 0.0,
                'historical_success': 0.0,
                'community_rating': 0.0,
                'total_score': 0.0
            }
            
            # Chip type compatibility (mandatory)
            device_chip = device_info.get('chip_type', '').upper()
            firmware_chip = firmware.get('chip_type', '').upper()
            
            if device_chip == firmware_chip:
                scores['chip_compatibility'] = 1.0
            elif device_chip and firmware_chip:
                scores['chip_compatibility'] = 0.0  # Incompatible
            else:
                scores['chip_compatibility'] = 0.5  # Unknown
            
            # Hardware compatibility
            device_hw = device_info.get('hardware', '').lower()
            firmware_compat = firmware.get('compatibility', [])
            
            if any(hw.lower() in device_hw for hw in firmware_compat):
                scores['hardware_compatibility'] = 1.0
            elif firmware_compat:
                scores['hardware_compatibility'] = 0.3  # Not explicitly compatible
            else:
                scores['hardware_compatibility'] = 0.7  # No specific requirements
            
            # Feature compatibility
            device_features = set(device_info.get('required_features', []))
            firmware_features = set(firmware.get('features', []))
            
            if device_features:
                feature_overlap = len(device_features.intersection(firmware_features))
                scores['feature_compatibility'] = feature_overlap / len(device_features)
            else:
                scores['feature_compatibility'] = 0.8  # No specific requirements
            
            # Historical success rate
            historical_score = await self._get_historical_success_rate(
                device_info, firmware['id']
            )
            scores['historical_success'] = historical_score
            
            # Community rating
            if 'avg_rating' in firmware and firmware['avg_rating']:
                scores['community_rating'] = firmware['avg_rating'] / 5.0
            elif 'rating' in firmware and firmware['rating']:
                scores['community_rating'] = firmware['rating'] / 5.0
            else:
                scores['community_rating'] = 0.5  # Neutral
            
            # Calculate weighted total score
            weights = {
                'chip_compatibility': 0.4,
                'hardware_compatibility': 0.25,
                'feature_compatibility': 0.15,
                'historical_success': 0.15,
                'community_rating': 0.05
            }
            
            total_score = sum(scores[key] * weights[key] for key in weights)
            scores['total_score'] = total_score
            
            return scores
            
        except Exception as e:
            logger.error(f"Error calculating firmware compatibility: {e}")
            return {'total_score': 0.0}
    
    async def _get_historical_success_rate(self, device_info: Dict[str, Any], 
                                         firmware_id: str) -> float:
        """Get historical success rate for device type with specific firmware"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Look for similar device patterns
            device_chip = device_info.get('chip_type', '')
            device_hw = device_info.get('hardware', '')
            
            cursor.execute('''
                SELECT AVG(success_rate), COUNT(*)
                FROM device_usage_patterns dup
                JOIN firmware_compatibility fc ON dup.firmware_id = fc.firmware_id
                WHERE fc.firmware_id = ? 
                AND fc.chip_type = ?
                AND (fc.hardware_pattern LIKE ? OR fc.hardware_pattern = '')
            ''', (firmware_id, device_chip, f'%{device_hw}%'))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None and result[1] > 0:
                return float(result[0])
            else:
                return 0.5  # Neutral score when no data available
                
        except Exception as e:
            logger.error(f"Error getting historical success rate: {e}")
            return 0.5
    
    async def _assess_flashing_risks(self, device_info: Dict[str, Any], 
                                   recommended_firmware: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess risks associated with flashing recommended firmware"""
        try:
            risk_assessment = {
                'overall_risk': 'low',
                'risk_factors': [],
                'mitigation_steps': [],
                'brick_probability': 0.0,
                'recovery_difficulty': 'easy'
            }
            
            risk_score = 0.0
            
            # Check for development/beta firmware
            for firmware in recommended_firmware[:3]:  # Check top 3
                if firmware.get('channel') in ['development', 'beta']:
                    risk_score += 0.2
                    risk_assessment['risk_factors'].append(
                        f"Using {firmware['channel']} firmware increases risk"
                    )
            
            # Check for custom/community firmware
            for firmware in recommended_firmware[:3]:
                if 'community' in firmware.get('id', ''):
                    risk_score += 0.15
                    risk_assessment['risk_factors'].append(
                        "Community firmware may have less testing"
                    )
            
            # Check hardware compatibility
            device_hw = device_info.get('hardware', '').lower()
            known_problematic = ['generic', 'unknown', 'custom']
            
            if any(prob in device_hw for prob in known_problematic):
                risk_score += 0.25
                risk_assessment['risk_factors'].append(
                    "Generic/unknown hardware increases flashing risk"
                )
            
            # Check current firmware state
            current_fw = device_info.get('current_firmware', '').lower()
            if not current_fw or 'unknown' in current_fw:
                risk_score += 0.2
                risk_assessment['risk_factors'].append(
                    "Unknown current firmware state"
                )
            
            # Determine overall risk level
            if risk_score <= 0.2:
                risk_assessment['overall_risk'] = 'low'
                risk_assessment['recovery_difficulty'] = 'easy'
            elif risk_score <= 0.5:
                risk_assessment['overall_risk'] = 'medium'
                risk_assessment['recovery_difficulty'] = 'moderate'
            else:
                risk_assessment['overall_risk'] = 'high'
                risk_assessment['recovery_difficulty'] = 'difficult'
            
            risk_assessment['brick_probability'] = min(risk_score, 0.95)
            
            # Add mitigation steps
            mitigation_steps = [
                "Create firmware backup before flashing",
                "Ensure stable power supply during flashing",
                "Use verified firmware sources",
                "Have recovery tools ready (esptool, serial adapter)"
            ]
            
            if risk_score > 0.3:
                mitigation_steps.extend([
                    "Consider using OTA update instead of serial flashing",
                    "Test with similar hardware first if available",
                    "Have hardware recovery method ready"
                ])
            
            risk_assessment['mitigation_steps'] = mitigation_steps
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error assessing flashing risks: {e}")
            return {'overall_risk': 'unknown', 'risk_factors': [], 'mitigation_steps': []}
    
    def _calculate_confidence_metrics(self, device_info: Dict[str, Any],
                                    similar_devices: List[Dict[str, Any]],
                                    compatibility_scores: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confidence metrics for recommendations"""
        try:
            metrics = {
                'data_quality': 0.0,
                'similarity_confidence': 0.0,
                'compatibility_confidence': 0.0,
                'overall_confidence': 0.0
            }
            
            # Data quality score
            required_fields = ['chip_type', 'hardware', 'mac']
            available_fields = sum(1 for field in required_fields if device_info.get(field))
            metrics['data_quality'] = available_fields / len(required_fields)
            
            # Similarity confidence (based on number and quality of similar devices)
            if similar_devices:
                avg_similarity = np.mean([d['similarity_score'] for d in similar_devices])
                device_count_factor = min(len(similar_devices) / 10.0, 1.0)
                metrics['similarity_confidence'] = avg_similarity * device_count_factor
            
            # Compatibility confidence (based on score distribution)
            if compatibility_scores:
                scores = [score.get('total_score', 0) for score in compatibility_scores.values()]
                if scores:
                    max_score = max(scores)
                    score_variance = np.var(scores)
                    # High confidence when there's a clear winner with low variance
                    metrics['compatibility_confidence'] = max_score * (1 - min(score_variance, 1.0))
            
            # Overall confidence (weighted average)
            weights = {'data_quality': 0.3, 'similarity_confidence': 0.4, 'compatibility_confidence': 0.3}
            metrics['overall_confidence'] = sum(
                metrics[key] * weights[key] for key in weights
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating confidence metrics: {e}")
            return {'overall_confidence': 0.0}
    
    async def generate_analytics_insights(self) -> List[Dict[str, Any]]:
        """Generate actionable insights from analytics data"""
        try:
            insights = []
            
            # Firmware popularity trends
            popularity_insight = await self._analyze_firmware_popularity_trends()
            if popularity_insight:
                insights.append(popularity_insight)
            
            # Device compatibility gaps
            compatibility_insight = await self._analyze_compatibility_gaps()
            if compatibility_insight:
                insights.append(compatibility_insight)
            
            # Success rate patterns
            success_insight = await self._analyze_success_patterns()
            if success_insight:
                insights.append(success_insight)
            
            # Community firmware trends
            community_insight = await self._analyze_community_trends()
            if community_insight:
                insights.append(community_insight)
            
            # Save insights to database
            for insight in insights:
                self._save_insight(insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating analytics insights: {e}")
            return []
    
    async def _analyze_firmware_popularity_trends(self) -> Optional[Dict[str, Any]]:
        """Analyze firmware download and usage trends"""
        try:
            conn = sqlite3.connect(self.firmware_manager.db_path)
            cursor = conn.cursor()
            
            # Get download trends over last 30 days
            cursor.execute('''
                SELECT f.variant, f.chip_type, COUNT(fd.id) as downloads
                FROM firmware f
                LEFT JOIN firmware_downloads fd ON f.id = fd.firmware_id
                WHERE fd.downloaded_at > datetime('now', '-30 days')
                GROUP BY f.variant, f.chip_type
                ORDER BY downloads DESC
                LIMIT 10
            ''')
            
            trends = cursor.fetchall()
            conn.close()
            
            if not trends:
                return None
            
            insight_data = {
                'trending_firmware': [
                    {'variant': t[0], 'chip_type': t[1], 'downloads': t[2]}
                    for t in trends
                ],
                'top_variant': trends[0][0] if trends else None,
                'growth_metrics': {}
            }
            
            return {
                'insight_type': 'firmware_popularity_trends',
                'insight_data': json.dumps(insight_data),
                'confidence': 0.8,
                'impact_score': 0.7,
                'actionable': True
            }
            
        except Exception as e:
            logger.error(f"Error analyzing firmware popularity trends: {e}")
            return None
    
    async def _analyze_compatibility_gaps(self) -> Optional[Dict[str, Any]]:
        """Identify hardware with poor firmware compatibility"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT hardware_pattern, chip_type, 
                       AVG(compatibility_score) as avg_compatibility,
                       COUNT(*) as device_count
                FROM firmware_compatibility
                GROUP BY hardware_pattern, chip_type
                HAVING device_count >= 5 AND avg_compatibility < 0.6
                ORDER BY avg_compatibility ASC
                LIMIT 10
            ''')
            
            gaps = cursor.fetchall()
            conn.close()
            
            if not gaps:
                return None
            
            insight_data = {
                'compatibility_gaps': [
                    {
                        'hardware': gap[0],
                        'chip_type': gap[1],
                        'avg_compatibility': gap[2],
                        'device_count': gap[3]
                    }
                    for gap in gaps
                ],
                'recommended_actions': [
                    'Create specialized firmware variants',
                    'Improve hardware detection algorithms',
                    'Add community templates for identified hardware'
                ]
            }
            
            return {
                'insight_type': 'compatibility_gaps',
                'insight_data': json.dumps(insight_data),
                'confidence': 0.9,
                'impact_score': 0.8,
                'actionable': True
            }
            
        except Exception as e:
            logger.error(f"Error analyzing compatibility gaps: {e}")
            return None
    
    def _save_insight(self, insight: Dict[str, Any]):
        """Save insight to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            expires_at = datetime.now() + timedelta(days=7)  # Insights expire in 7 days
            
            cursor.execute('''
                INSERT INTO analytics_insights
                (insight_type, insight_data, confidence, impact_score, actionable, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                insight['insight_type'],
                insight['insight_data'],
                insight['confidence'],
                insight['impact_score'],
                insight['actionable'],
                expires_at
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving insight: {e}")
    
    async def update_device_usage_pattern(self, device_fingerprint: Dict[str, Any],
                                        firmware_id: str, success: bool,
                                        performance_data: Dict[str, Any] = None):
        """Update device usage patterns for learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            fingerprint_json = json.dumps(device_fingerprint)
            
            # Check if pattern exists
            cursor.execute('''
                SELECT id, success_rate, usage_duration 
                FROM device_usage_patterns
                WHERE device_fingerprint = ? AND firmware_id = ?
            ''', (fingerprint_json, firmware_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                pattern_id, current_success_rate, usage_duration = existing
                
                # Update success rate using exponential moving average
                new_success_rate = 0.8 * current_success_rate + 0.2 * (1.0 if success else 0.0)
                
                cursor.execute('''
                    UPDATE device_usage_patterns
                    SET success_rate = ?, usage_duration = ?, 
                        performance_score = ?, stability_score = ?,
                        last_updated = ?
                    WHERE id = ?
                ''', (
                    new_success_rate,
                    usage_duration + 1,
                    performance_data.get('performance_score', 0.5) if performance_data else 0.5,
                    performance_data.get('stability_score', 0.5) if performance_data else 0.5,
                    datetime.now(),
                    pattern_id
                ))
            else:
                # Create new pattern
                cursor.execute('''
                    INSERT INTO device_usage_patterns
                    (device_fingerprint, firmware_id, success_rate, usage_duration,
                     performance_score, stability_score, recommendation_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    fingerprint_json,
                    firmware_id,
                    1.0 if success else 0.0,
                    1,
                    performance_data.get('performance_score', 0.5) if performance_data else 0.5,
                    performance_data.get('stability_score', 0.5) if performance_data else 0.5,
                    0.5
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated device usage pattern: {firmware_id} - {'success' if success else 'failure'}")
            
        except Exception as e:
            logger.error(f"Error updating device usage pattern: {e}")
    
    def get_analytics_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive analytics data for dashboard"""
        try:
            dashboard_data = {
                'firmware_stats': self._get_firmware_statistics(),
                'device_stats': self._get_device_statistics(),
                'compatibility_stats': self._get_compatibility_statistics(),
                'trends': self._get_trend_data(),
                'insights': self._get_recent_insights()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting analytics dashboard data: {e}")
            return {}
    
    def _get_firmware_statistics(self) -> Dict[str, Any]:
        """Get firmware-related statistics"""
        try:
            stats = {}
            
            # Official firmware stats
            conn = sqlite3.connect(self.firmware_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM firmware WHERE verified = 1')
            stats['official_firmware_count'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM firmware WHERE channel = "development"')
            stats['development_firmware_count'] = cursor.fetchone()[0]
            
            conn.close()
            
            # Community firmware stats
            conn = sqlite3.connect(self.community_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM community_firmware WHERE status = "approved"')
            stats['community_firmware_count'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(rating) FROM community_firmware WHERE rating > 0')
            result = cursor.fetchone()
            stats['avg_community_rating'] = result[0] if result[0] else 0.0
            
            conn.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting firmware statistics: {e}")
            return {}
    
    def _get_recent_insights(self) -> List[Dict[str, Any]]:
        """Get recent analytics insights"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT insight_type, insight_data, confidence, impact_score, generated_at
                FROM analytics_insights
                WHERE expires_at > datetime('now')
                ORDER BY generated_at DESC
                LIMIT 10
            ''')
            
            insights = []
            for row in cursor.fetchall():
                insights.append({
                    'type': row[0],
                    'data': json.loads(row[1]),
                    'confidence': row[2],
                    'impact_score': row[3],
                    'generated_at': row[4]
                })
            
            conn.close()
            return insights
            
        except Exception as e:
            logger.error(f"Error getting recent insights: {e}")
            return []