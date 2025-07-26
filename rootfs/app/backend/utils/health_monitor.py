#!/usr/bin/env python3

import time
import threading
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict

from .logger import logger, ServiceHealth

@dataclass
class HealthMetric:
    """Individual health metric data"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    status: str  # 'healthy', 'warning', 'critical'
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

@dataclass
class ServiceDependency:
    """Service dependency definition"""
    name: str
    check_function: callable
    critical: bool = True
    timeout: float = 5.0

class HealthMonitoringSystem:
    """Comprehensive health monitoring system"""
    
    def __init__(self):
        self.services: Dict[str, ServiceHealth] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.dependencies: List[ServiceDependency] = []
        self.monitoring_active = False
        self.monitor_thread = None
        self.alert_callbacks = []
        
        # Performance thresholds
        self.thresholds = {
            'cpu_percent': {'warning': 80.0, 'critical': 95.0},
            'memory_percent': {'warning': 85.0, 'critical': 95.0},
            'disk_percent': {'warning': 90.0, 'critical': 98.0},
            'response_time_ms': {'warning': 1000.0, 'critical': 5000.0},
            'error_rate_percent': {'warning': 5.0, 'critical': 10.0}
        }
        
    def register_service(self, service_name: str) -> ServiceHealth:
        """Register a service for health monitoring"""
        if service_name not in self.services:
            self.services[service_name] = ServiceHealth(service_name)
            logger.info("Service registered for health monitoring", 
                       service=service_name)
        return self.services[service_name]
        
    def add_dependency(self, name: str, check_function: callable, 
                      critical: bool = True, timeout: float = 5.0):
        """Add a service dependency check"""
        dependency = ServiceDependency(name, check_function, critical, timeout)
        self.dependencies.append(dependency)
        logger.info("Dependency added", 
                   dependency=name, 
                   critical=critical, 
                   timeout=timeout)
        
    def add_alert_callback(self, callback: callable):
        """Add callback for health alerts"""
        self.alert_callbacks.append(callback)
        
    def record_metric(self, name: str, value: float, unit: str = ""):
        """Record a health metric"""
        # Determine status based on thresholds
        status = 'healthy'
        threshold_warning = None
        threshold_critical = None
        
        if name in self.thresholds:
            thresholds = self.thresholds[name]
            threshold_warning = thresholds.get('warning')
            threshold_critical = thresholds.get('critical')
            
            if threshold_critical and value >= threshold_critical:
                status = 'critical'
            elif threshold_warning and value >= threshold_warning:
                status = 'warning'
                
        metric = HealthMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            status=status,
            threshold_warning=threshold_warning,
            threshold_critical=threshold_critical
        )
        
        self.metrics_history[name].append(metric)
        
        # Alert on status changes
        if status in ['warning', 'critical']:
            self._trigger_alert(f"Metric {name} is {status}", {
                'metric': name,
                'value': value,
                'status': status,
                'unit': unit
            })
            
    def get_system_metrics(self) -> Dict[str, HealthMetric]:
        """Get current system performance metrics"""
        metrics = {}
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric('cpu_percent', cpu_percent, '%')
            metrics['cpu'] = self.metrics_history['cpu_percent'][-1]
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric('memory_percent', memory.percent, '%')
            metrics['memory'] = self.metrics_history['memory_percent'][-1]
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric('disk_percent', disk_percent, '%')
            metrics['disk'] = self.metrics_history['disk_percent'][-1]
            
            # Network I/O
            net_io = psutil.net_io_counters()
            metrics['network_bytes_sent'] = net_io.bytes_sent
            metrics['network_bytes_recv'] = net_io.bytes_recv
            
        except Exception as e:
            logger.error("Failed to collect system metrics", exc_info=True)
            
        return metrics
        
    def check_service_dependencies(self) -> Dict[str, Any]:
        """Check all service dependencies"""
        results = {}
        overall_status = 'healthy'
        
        for dep in self.dependencies:
            try:
                start_time = time.time()
                
                # Run dependency check with timeout
                if asyncio.iscoroutinefunction(dep.check_function):
                    # Handle async functions
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            asyncio.wait_for(dep.check_function(), timeout=dep.timeout)
                        )
                    finally:
                        loop.close()
                else:
                    # Handle sync functions
                    result = dep.check_function()
                    
                response_time = (time.time() - start_time) * 1000  # ms
                
                results[dep.name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'response_time_ms': response_time,
                    'critical': dep.critical,
                    'last_check': datetime.now().isoformat()
                }
                
                # Update overall status
                if not result and dep.critical:
                    overall_status = 'critical'
                elif not result and overall_status == 'healthy':
                    overall_status = 'degraded'
                    
            except asyncio.TimeoutError:
                results[dep.name] = {
                    'status': 'timeout',
                    'response_time_ms': dep.timeout * 1000,
                    'critical': dep.critical,
                    'error': 'Dependency check timed out',
                    'last_check': datetime.now().isoformat()
                }
                if dep.critical:
                    overall_status = 'critical'
                    
            except Exception as e:
                results[dep.name] = {
                    'status': 'error',
                    'critical': dep.critical,
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }
                if dep.critical:
                    overall_status = 'critical'
                    
                logger.error(f"Dependency check failed: {dep.name}", 
                           dependency=dep.name, 
                           exc_info=True)
                           
        return {
            'overall_status': overall_status,
            'dependencies': results,
            'check_timestamp': datetime.now().isoformat()
        }
        
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        # System metrics
        system_metrics = self.get_system_metrics()
        
        # Service health
        service_health = {}
        for name, service in self.services.items():
            service_health[name] = service.get_health_info()
            
        # Dependency checks
        dependency_status = self.check_service_dependencies()
        
        # Calculate overall health
        overall_status = 'healthy'
        
        # Check system metrics
        for metric in system_metrics.values():
            if hasattr(metric, 'status'):
                if metric.status == 'critical':
                    overall_status = 'critical'
                    break
                elif metric.status == 'warning' and overall_status == 'healthy':
                    overall_status = 'degraded'
                    
        # Check service health
        for service_info in service_health.values():
            if service_info['status'] == 'unhealthy':
                overall_status = 'critical'
                break
            elif service_info['status'] == 'degraded' and overall_status == 'healthy':
                overall_status = 'degraded'
                
        # Check dependencies
        if dependency_status['overall_status'] == 'critical':
            overall_status = 'critical'
        elif dependency_status['overall_status'] == 'degraded' and overall_status == 'healthy':
            overall_status = 'degraded'
            
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'system_metrics': {k: asdict(v) if hasattr(v, '__dict__') else v 
                             for k, v in system_metrics.items()},
            'services': service_health,
            'dependencies': dependency_status,
            'uptime_seconds': time.time() - (self.services.get('app', ServiceHealth('app')).start_time if self.services.get('app') else time.time())
        }
        
    def start_monitoring(self, interval: int = 60):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            logger.warning("Health monitoring already active")
            return
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, 
            args=(interval,)
        )
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Health monitoring started", interval=interval)
        
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            
        logger.info("Health monitoring stopped")
        
    def _monitoring_loop(self, interval: int):
        """Continuous monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect comprehensive health data
                health_data = self.get_comprehensive_health()
                
                # Log health summary
                logger.info("Health check completed", 
                           overall_status=health_data['overall_status'],
                           services_count=len(health_data['services']),
                           dependencies_count=len(health_data['dependencies']['dependencies']))
                           
                # Check for alerts
                if health_data['overall_status'] in ['degraded', 'critical']:
                    self._trigger_alert(
                        f"System health is {health_data['overall_status']}",
                        health_data
                    )
                    
            except Exception as e:
                logger.error("Health monitoring loop error", exc_info=True)
                
            time.sleep(interval)
            
    def _trigger_alert(self, message: str, context: Dict[str, Any]):
        """Trigger health alert"""
        logger.warning(f"Health alert: {message}", **context)
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(message, context)
            except Exception as e:
                logger.error("Alert callback failed", 
                           callback=callback.__name__, 
                           exc_info=True)
                           
    def get_metrics_history(self, metric_name: str, 
                           hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics data"""
        if metric_name not in self.metrics_history:
            return []
            
        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = []
        
        for metric in self.metrics_history[metric_name]:
            if metric.timestamp >= cutoff_time:
                history.append(asdict(metric))
                
        return history
        
    def reset_metrics(self):
        """Reset all metrics history"""
        self.metrics_history.clear()
        logger.info("Health metrics history cleared")

# Global health monitor instance
health_monitor = HealthMonitoringSystem()