import asyncio
import logging
import schedule
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    """Background task scheduler for firmware management"""
    
    def __init__(self, firmware_manager, cache_manager, community_manager, analytics_engine):
        self.firmware_manager = firmware_manager
        self.cache_manager = cache_manager
        self.community_manager = community_manager
        self.analytics_engine = analytics_engine
        
        self.scheduler = AsyncIOScheduler()
        self.running = False
        
        # Task status tracking
        self.task_status = {
            'last_firmware_check': None,
            'last_cache_cleanup': None,
            'last_analytics_update': None,
            'last_community_review': None,
            'errors': []
        }
    
    def start(self):
        """Start the background scheduler"""
        if self.running:
            return
        
        logger.info("Starting background scheduler...")
        
        # Schedule firmware update checks
        self.scheduler.add_job(
            self._check_firmware_updates,
            CronTrigger(hour=2, minute=0),  # Daily at 2 AM
            id='firmware_updates_daily',
            name='Daily Firmware Updates Check',
            max_instances=1
        )
        
        # Schedule development firmware checks (more frequent)
        self.scheduler.add_job(
            self._check_development_firmware,
            IntervalTrigger(hours=6),  # Every 6 hours
            id='firmware_dev_check',
            name='Development Firmware Check',
            max_instances=1
        )
        
        # Schedule cache cleanup
        self.scheduler.add_job(
            self._cleanup_firmware_cache,
            CronTrigger(hour=3, minute=0),  # Daily at 3 AM
            id='cache_cleanup_daily',
            name='Daily Cache Cleanup',
            max_instances=1
        )
        
        # Schedule analytics updates
        self.scheduler.add_job(
            self._update_analytics,
            CronTrigger(hour=4, minute=0),  # Daily at 4 AM
            id='analytics_daily',
            name='Daily Analytics Update',
            max_instances=1
        )
        
        # Schedule community firmware review
        self.scheduler.add_job(
            self._review_community_firmware,
            CronTrigger(hour=1, minute=0),  # Daily at 1 AM
            id='community_review_daily',
            name='Daily Community Firmware Review',
            max_instances=1
        )
        
        # Schedule popular firmware pre-caching
        self.scheduler.add_job(
            self._precache_popular_firmware,
            CronTrigger(hour=5, minute=0),  # Daily at 5 AM
            id='precache_popular',
            name='Pre-cache Popular Firmware',
            max_instances=1
        )
        
        # Schedule model retraining (weekly)
        self.scheduler.add_job(
            self._retrain_ml_models,
            CronTrigger(day_of_week='sun', hour=6, minute=0),  # Weekly on Sunday
            id='retrain_models_weekly',
            name='Weekly ML Model Retraining',
            max_instances=1
        )
        
        # Schedule health checks (hourly)
        self.scheduler.add_job(
            self._system_health_check,
            IntervalTrigger(hours=1),  # Every hour
            id='health_check_hourly',
            name='Hourly System Health Check',
            max_instances=1
        )
        
        self.scheduler.start()
        self.running = True
        
        logger.info("Background scheduler started with 8 scheduled tasks")
    
    def stop(self):
        """Stop the background scheduler"""
        if not self.running:
            return
        
        logger.info("Stopping background scheduler...")
        self.scheduler.shutdown(wait=True)
        self.running = False
        logger.info("Background scheduler stopped")
    
    async def _check_firmware_updates(self):
        """Check for new firmware updates from all sources"""
        try:
            logger.info("Starting scheduled firmware updates check...")
            start_time = datetime.now()
            
            # Check all sources for updates
            update_results = await self.firmware_manager.check_all_sources_for_updates()
            
            # Save new firmware to database
            all_updates = []
            for source, results in update_results['sources'].items():
                all_updates.extend(results.get('firmware', []))
            
            if all_updates:
                saved_count = await self.firmware_manager.save_firmware_updates(all_updates)
                logger.info(f"Saved {saved_count} new firmware updates")
                
                # Trigger popular firmware pre-caching
                if saved_count > 0:
                    await self._precache_new_firmware(all_updates[:5])  # Cache top 5
            
            duration = (datetime.now() - start_time).total_seconds()
            self.task_status['last_firmware_check'] = {
                'timestamp': datetime.now().isoformat(),
                'duration': duration,
                'updates_found': len(all_updates),
                'sources_checked': len(update_results['sources']),
                'errors': update_results.get('errors', [])
            }
            
            logger.info(f"Firmware updates check completed in {duration:.2f}s")
            
        except Exception as e:
            error_msg = f"Firmware updates check failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('firmware_updates', error_msg)
    
    async def _check_development_firmware(self):
        """Check for development/beta firmware updates"""
        try:
            logger.info("Checking development firmware updates...")
            
            # Focus on development sources
            dev_sources = {
                'github_artifacts': self.firmware_manager.sources['github_artifacts'],
                'ota_esp8266_dev': self.firmware_manager.sources['ota_esp8266_dev'],
                'ota_esp32_dev': self.firmware_manager.sources['ota_esp32_dev']
            }
            
            updates = []
            for source_name, source_config in dev_sources.items():
                try:
                    if source_config['type'] == 'github_api':
                        source_updates = await self.firmware_manager._check_github_source(
                            source_name, source_config
                        )
                    elif source_config['type'] == 'ota_server':
                        source_updates = await self.firmware_manager._check_ota_source(
                            source_name, source_config
                        )
                    else:
                        continue
                    
                    updates.extend(source_updates)
                    
                except Exception as e:
                    logger.error(f"Error checking development source {source_name}: {e}")
            
            if updates:
                saved_count = await self.firmware_manager.save_firmware_updates(updates)
                logger.info(f"Saved {saved_count} development firmware updates")
            
        except Exception as e:
            error_msg = f"Development firmware check failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('development_firmware', error_msg)
    
    async def _cleanup_firmware_cache(self):
        """Clean up old and unused firmware cache"""
        try:
            logger.info("Starting scheduled cache cleanup...")
            start_time = datetime.now()
            
            # Perform cache cleanup
            await self.cache_manager.cleanup_cache(force=False)
            
            # Get cache statistics
            cache_stats = self.cache_manager.get_cache_stats()
            
            duration = (datetime.now() - start_time).total_seconds()
            self.task_status['last_cache_cleanup'] = {
                'timestamp': datetime.now().isoformat(),
                'duration': duration,
                'cache_size_mb': cache_stats.get('total_size', 0) / 1024 / 1024,
                'file_count': cache_stats.get('file_count', 0)
            }
            
            logger.info(f"Cache cleanup completed in {duration:.2f}s")
            
        except Exception as e:
            error_msg = f"Cache cleanup failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('cache_cleanup', error_msg)
    
    async def _update_analytics(self):
        """Update analytics data and generate insights"""
        try:
            logger.info("Starting scheduled analytics update...")
            start_time = datetime.now()
            
            # Generate new insights
            insights = await self.analytics_engine.generate_analytics_insights()
            
            # Update ML models if needed
            await self._update_ml_models_if_needed()
            
            duration = (datetime.now() - start_time).total_seconds()
            self.task_status['last_analytics_update'] = {
                'timestamp': datetime.now().isoformat(),
                'duration': duration,
                'insights_generated': len(insights)
            }
            
            logger.info(f"Analytics update completed in {duration:.2f}s, generated {len(insights)} insights")
            
        except Exception as e:
            error_msg = f"Analytics update failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('analytics_update', error_msg)
    
    async def _review_community_firmware(self):
        """Review pending community firmware submissions"""
        try:
            logger.info("Starting community firmware review...")
            
            # Get pending community firmware
            pending_firmware = self.community_manager.get_community_firmware_list(
                status='pending',
                limit=50
            )
            
            reviewed_count = 0
            for firmware in pending_firmware:
                try:
                    # Basic automated review checks
                    review_result = await self._automated_firmware_review(firmware)
                    
                    if review_result['auto_approve']:
                        # Auto-approve safe firmware
                        await self._approve_community_firmware(firmware['id'], 'automated_review')
                        reviewed_count += 1
                    elif review_result['auto_reject']:
                        # Auto-reject problematic firmware
                        await self._reject_community_firmware(
                            firmware['id'], 
                            'automated_review',
                            review_result['rejection_reason']
                        )
                        reviewed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error reviewing firmware {firmware['id']}: {e}")
            
            self.task_status['last_community_review'] = {
                'timestamp': datetime.now().isoformat(),
                'pending_count': len(pending_firmware),
                'reviewed_count': reviewed_count
            }
            
            logger.info(f"Community firmware review completed: {reviewed_count}/{len(pending_firmware)} reviewed")
            
        except Exception as e:
            error_msg = f"Community firmware review failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('community_review', error_msg)
    
    async def _precache_popular_firmware(self):
        """Pre-cache popular firmware for faster downloads"""
        try:
            logger.info("Starting popular firmware pre-caching...")
            
            # Get most popular firmware from last 7 days
            popular_firmware = await self._get_popular_firmware(days=7, limit=20)
            
            cached_count = 0
            for firmware in popular_firmware:
                try:
                    # Check if already cached
                    cached_path = self.cache_manager.get_cached_firmware_path(firmware['id'])
                    if not cached_path:
                        # Download and cache
                        cached_path = await self.cache_manager.download_and_cache_firmware(
                            firmware['id'],
                            firmware['download_url']
                        )
                        if cached_path:
                            cached_count += 1
                            logger.debug(f"Pre-cached firmware: {firmware['name']}")
                
                except Exception as e:
                    logger.error(f"Error pre-caching firmware {firmware['id']}: {e}")
            
            logger.info(f"Pre-cached {cached_count} popular firmware files")
            
        except Exception as e:
            error_msg = f"Popular firmware pre-caching failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('precache_popular', error_msg)
    
    async def _precache_new_firmware(self, firmware_list: list):
        """Pre-cache newly discovered firmware"""
        try:
            cached_count = 0
            for firmware in firmware_list:
                try:
                    cached_path = await self.cache_manager.download_and_cache_firmware(
                        firmware['id'],
                        firmware['download_url']
                    )
                    if cached_path:
                        cached_count += 1
                
                except Exception as e:
                    logger.error(f"Error pre-caching new firmware {firmware['id']}: {e}")
            
            logger.info(f"Pre-cached {cached_count} new firmware files")
            
        except Exception as e:
            logger.error(f"New firmware pre-caching failed: {str(e)}")
    
    async def _retrain_ml_models(self):
        """Retrain ML models with new data"""
        try:
            logger.info("Starting weekly ML model retraining...")
            start_time = datetime.now()
            
            # Check if retraining is needed (enough new data)
            if await self._should_retrain_models():
                # Retrain recommendation models
                await self._retrain_recommendation_models()
                
                # Retrain device clustering
                await self._retrain_device_clustering()
                
                # Update model files
                await self._save_updated_models()
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"ML model retraining completed in {duration:.2f}s")
            else:
                logger.info("ML model retraining skipped - insufficient new data")
            
        except Exception as e:
            error_msg = f"ML model retraining failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('ml_retraining', error_msg)
    
    async def _system_health_check(self):
        """Perform system health checks"""
        try:
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'services': {},
                'resources': {},
                'alerts': []
            }
            
            # Check database connections
            try:
                # Test firmware database
                firmware_list = self.firmware_manager.get_firmware_list(limit=1)
                health_status['services']['firmware_db'] = 'healthy'
            except Exception as e:
                health_status['services']['firmware_db'] = 'error'
                health_status['alerts'].append(f"Firmware database error: {str(e)}")
            
            # Check cache status
            try:
                cache_stats = self.cache_manager.get_cache_stats()
                cache_usage = cache_stats.get('total_size', 0) / (2 * 1024 * 1024 * 1024)  # % of 2GB
                
                if cache_usage > 0.9:
                    health_status['alerts'].append("Cache usage above 90%")
                
                health_status['services']['cache'] = 'healthy'
                health_status['resources']['cache_usage_percent'] = cache_usage * 100
            except Exception as e:
                health_status['services']['cache'] = 'error'
                health_status['alerts'].append(f"Cache system error: {str(e)}")
            
            # Check scheduler status
            health_status['services']['scheduler'] = 'healthy' if self.running else 'stopped'
            
            # Log alerts if any
            if health_status['alerts']:
                for alert in health_status['alerts']:
                    logger.warning(f"Health check alert: {alert}")
            
            # Store health status for API access
            self.task_status['last_health_check'] = health_status
            
        except Exception as e:
            error_msg = f"System health check failed: {str(e)}"
            logger.error(error_msg)
            self._record_error('health_check', error_msg)
    
    async def _automated_firmware_review(self, firmware: Dict[str, Any]) -> Dict[str, Any]:
        """Perform automated review of community firmware"""
        review_result = {
            'auto_approve': False,
            'auto_reject': False,
            'rejection_reason': None,
            'confidence': 0.0
        }
        
        try:
            # Check file size (reasonable limits)
            file_size = firmware.get('file_size', 0)
            if file_size < 100000 or file_size > 8 * 1024 * 1024:  # 100KB - 8MB
                review_result['auto_reject'] = True
                review_result['rejection_reason'] = 'Invalid file size'
                return review_result
            
            # Check for required metadata
            required_fields = ['chip_type', 'variant', 'author_name']
            missing_fields = [field for field in required_fields if not firmware.get(field)]
            
            if missing_fields:
                review_result['auto_reject'] = True
                review_result['rejection_reason'] = f'Missing required fields: {", ".join(missing_fields)}'
                return review_result
            
            # Check for suspicious patterns
            description = firmware.get('description', '').lower()
            name = firmware.get('name', '').lower()
            
            suspicious_keywords = ['hack', 'crack', 'exploit', 'backdoor', 'virus']
            if any(keyword in description or keyword in name for keyword in suspicious_keywords):
                review_result['auto_reject'] = True
                review_result['rejection_reason'] = 'Suspicious content detected'
                return review_result
            
            # Check author reputation (if available)
            author_firmware_count = len(self.community_manager.get_community_firmware_list(
                author=firmware.get('author_name'),
                status='approved'
            ))
            
            # Auto-approve criteria
            if (file_size > 500000 and  # Reasonable size
                firmware.get('chip_type') in ['ESP32', 'ESP8266'] and  # Valid chip type
                len(firmware.get('description', '')) > 50 and  # Decent description
                author_firmware_count >= 3):  # Trusted author
                review_result['auto_approve'] = True
                review_result['confidence'] = 0.8
            
            return review_result
            
        except Exception as e:
            logger.error(f"Automated firmware review error: {e}")
            return review_result
    
    def _record_error(self, task_name: str, error_message: str):
        """Record task errors for monitoring"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'task': task_name,
            'error': error_message
        }
        
        self.task_status['errors'].append(error_record)
        
        # Keep only last 50 errors
        if len(self.task_status['errors']) > 50:
            self.task_status['errors'] = self.task_status['errors'][-50:]
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            'running': self.running,
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
                for job in self.scheduler.get_jobs()
            ],
            'task_status': self.task_status
        }
    
    async def trigger_task_manually(self, task_name: str) -> Dict[str, Any]:
        """Manually trigger a scheduled task"""
        task_map = {
            'firmware_updates': self._check_firmware_updates,
            'development_firmware': self._check_development_firmware,
            'cache_cleanup': self._cleanup_firmware_cache,
            'analytics_update': self._update_analytics,
            'community_review': self._review_community_firmware,
            'precache_popular': self._precache_popular_firmware,
            'retrain_models': self._retrain_ml_models,
            'health_check': self._system_health_check
        }
        
        if task_name not in task_map:
            return {
                'success': False,
                'error': f'Unknown task: {task_name}'
            }
        
        try:
            logger.info(f"Manually triggering task: {task_name}")
            start_time = datetime.now()
            
            await task_map[task_name]()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'message': f'Task {task_name} completed successfully',
                'duration': duration
            }
            
        except Exception as e:
            error_msg = f'Manual task execution failed: {str(e)}'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }