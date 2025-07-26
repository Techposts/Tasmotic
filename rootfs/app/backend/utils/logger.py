#!/usr/bin/env python3

import logging
import json
import uuid
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from functools import wraps
import threading

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get() or 'no-correlation-id'
        return True

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'no-correlation-id'),
            'thread_id': threading.get_ident(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_entry)

class TasmotaLogger:
    """Enhanced logger for Tasmota Master with structured logging"""
    
    def __init__(self, name: str = 'tasmota-master'):
        self.logger = logging.getLogger(name)
        self._setup_logger()
        
    def _setup_logger(self):
        """Setup structured logging with correlation IDs"""
        if self.logger.handlers:
            return  # Already configured
            
        # Set level from environment or default to INFO
        level = logging.INFO
        
        # Create handler
        handler = logging.StreamHandler()
        
        # Add correlation ID filter
        correlation_filter = CorrelationIDFilter()
        handler.addFilter(correlation_filter)
        
        # Set formatter
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        
        # Configure logger
        self.logger.addHandler(handler)
        self.logger.setLevel(level)
        self.logger.propagate = False
        
    def set_correlation_id(self, cid: str = None) -> str:
        """Set correlation ID for current context"""
        if not cid:
            cid = str(uuid.uuid4())[:8]
        correlation_id.set(cid)
        return cid
        
    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID"""
        return correlation_id.get()
        
    def log_with_context(self, level: int, message: str, **kwargs):
        """Log with additional context"""
        extra_fields = {k: v for k, v in kwargs.items() if k != 'exc_info'}
        self.logger.log(level, message, extra={'extra_fields': extra_fields}, 
                       exc_info=kwargs.get('exc_info', False))
        
    def debug(self, message: str, **kwargs):
        self.log_with_context(logging.DEBUG, message, **kwargs)
        
    def info(self, message: str, **kwargs):
        self.log_with_context(logging.INFO, message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        self.log_with_context(logging.WARNING, message, **kwargs)
        
    def error(self, message: str, **kwargs):
        self.log_with_context(logging.ERROR, message, **kwargs)
        
    def critical(self, message: str, **kwargs):
        self.log_with_context(logging.CRITICAL, message, **kwargs)

# Global logger instance
logger = TasmotaLogger()

def with_correlation_id(func):
    """Decorator to add correlation ID to function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Generate correlation ID if not present
        cid = logger.get_correlation_id()
        if not cid:
            cid = logger.set_correlation_id()
            
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", 
                        function=func.__name__, 
                        args_count=len(args),
                        kwargs_keys=list(kwargs.keys()),
                        exc_info=True)
            raise
    return wrapper

def log_api_call(endpoint: str = None):
    """Decorator for API endpoint logging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set new correlation ID for each API call
            cid = logger.set_correlation_id()
            start_time = time.time()
            
            endpoint_name = endpoint or func.__name__
            logger.info(f"API call started: {endpoint_name}", 
                       endpoint=endpoint_name,
                       correlation_id=cid)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(f"API call completed: {endpoint_name}",
                           endpoint=endpoint_name,
                           duration_ms=round(duration * 1000, 2),
                           success=True)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"API call failed: {endpoint_name}",
                            endpoint=endpoint_name,
                            duration_ms=round(duration * 1000, 2),
                            error_type=type(e).__name__,
                            error_message=str(e),
                            success=False,
                            exc_info=True)
                raise
                
        return wrapper
    return decorator

class ServiceHealth:
    """Service health tracking and logging"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.start_time = time.time()
        self.error_count = 0
        self.last_error = None
        self.status = "healthy"
        
    def mark_healthy(self):
        """Mark service as healthy"""
        self.status = "healthy"
        logger.debug(f"Service marked healthy: {self.service_name}",
                    service=self.service_name,
                    status=self.status)
        
    def mark_degraded(self, reason: str):
        """Mark service as degraded"""
        self.status = "degraded"
        logger.warning(f"Service degraded: {self.service_name}",
                      service=self.service_name,
                      status=self.status,
                      reason=reason)
        
    def mark_unhealthy(self, error: Exception):
        """Mark service as unhealthy"""
        self.status = "unhealthy"
        self.error_count += 1
        self.last_error = str(error)
        
        logger.error(f"Service unhealthy: {self.service_name}",
                    service=self.service_name,
                    status=self.status,
                    error_count=self.error_count,
                    last_error=self.last_error,
                    exc_info=True)
        
    def get_health_info(self) -> Dict[str, Any]:
        """Get service health information"""
        uptime = time.time() - self.start_time
        return {
            'service': self.service_name,
            'status': self.status,
            'uptime_seconds': round(uptime, 2),
            'error_count': self.error_count,
            'last_error': self.last_error
        }

class ErrorHandler:
    """Centralized error handling with user-friendly messages"""
    
    ERROR_CODES = {
        'MQTT_CONNECTION_FAILED': {
            'user_message': 'Unable to connect to MQTT broker. Please check your MQTT settings.',
            'technical_details': 'MQTT connection failed - verify host, port, and credentials'
        },
        'DEVICE_NOT_FOUND': {
            'user_message': 'Device not found. It may have been disconnected or moved.',
            'technical_details': 'Requested device ID not found in device registry'
        },
        'FIRMWARE_DOWNLOAD_FAILED': {
            'user_message': 'Unable to download firmware. Please check your internet connection.',
            'technical_details': 'Firmware download failed - network or server issue'
        },
        'INVALID_CONFIGURATION': {
            'user_message': 'Configuration error. Please check your settings and try again.',
            'technical_details': 'Configuration validation failed'
        },
        'FLASH_OPERATION_FAILED': {
            'user_message': 'Device flashing failed. Please check device connection and try again.',
            'technical_details': 'ESP flashing operation failed'
        },
        'SERVICE_UNAVAILABLE': {
            'user_message': 'Service temporarily unavailable. Please try again in a moment.',
            'technical_details': 'Required service is not available or responding'
        }
    }
    
    @classmethod
    def handle_error(cls, error_code: str, exception: Exception = None, **context) -> Dict[str, Any]:
        """Handle error with structured response"""
        error_info = cls.ERROR_CODES.get(error_code, {
            'user_message': 'An unexpected error occurred. Please try again.',
            'technical_details': 'Unknown error type'
        })
        
        error_response = {
            'success': False,
            'error_code': error_code,
            'user_message': error_info['user_message'],
            'correlation_id': logger.get_correlation_id(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Log the error
        logger.error(f"Error handled: {error_code}",
                    error_code=error_code,
                    user_message=error_info['user_message'],
                    technical_details=error_info['technical_details'],
                    context=context,
                    exc_info=exception is not None)
        
        return error_response

# Service health tracking instances
service_health = {}

def get_service_health(service_name: str) -> ServiceHealth:
    """Get or create service health tracker"""
    if service_name not in service_health:
        service_health[service_name] = ServiceHealth(service_name)
    return service_health[service_name]

def log_service_startup(service_name: str, **context):
    """Log service startup"""
    health = get_service_health(service_name)
    health.mark_healthy()
    
    logger.info(f"Service started: {service_name}",
               service=service_name,
               startup_time=datetime.utcnow().isoformat(),
               **context)