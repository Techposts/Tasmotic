#!/usr/bin/env python3

import time
import hashlib
import secrets
import re
from collections import defaultdict, deque
from typing import Dict, Any, Optional, List
from functools import wraps
from flask import request, jsonify, session
from datetime import datetime, timedelta
import ipaddress
import json

from .logger import logger, ErrorHandler

class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self):
        # Store request history per IP
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        # Store blocked IPs with expiry
        self.blocked_ips: Dict[str, datetime] = {}
        # Store failed attempts per IP
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        
    def is_rate_limited(self, identifier: str, limit: int, window_seconds: int) -> bool:
        """Check if request is rate limited"""
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old requests
        requests = self.request_history[identifier]
        while requests and requests[0] < window_start:
            requests.popleft()
            
        # Check if limit exceeded
        if len(requests) >= limit:
            return True
            
        # Add current request
        requests.append(now)
        return False
        
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is temporarily blocked"""
        if ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[ip]:
                return True
            else:
                # Unblock expired IPs
                del self.blocked_ips[ip]
                if ip in self.failed_attempts:
                    del self.failed_attempts[ip]
                    
        return False
        
    def record_failed_attempt(self, ip: str):
        """Record a failed attempt and potentially block IP"""
        self.failed_attempts[ip] += 1
        
        # Progressive blocking based on failed attempts
        if self.failed_attempts[ip] >= 10:
            # Block for 1 hour after 10 failures
            self.blocked_ips[ip] = datetime.now() + timedelta(hours=1)
            logger.warning(f"IP blocked for 1 hour due to repeated failures", 
                         blocked_ip=ip, 
                         failed_attempts=self.failed_attempts[ip])
        elif self.failed_attempts[ip] >= 5:
            # Block for 10 minutes after 5 failures
            self.blocked_ips[ip] = datetime.now() + timedelta(minutes=10)
            logger.warning(f"IP blocked for 10 minutes due to failures", 
                         blocked_ip=ip, 
                         failed_attempts=self.failed_attempts[ip])
            
    def get_client_identifier(self) -> str:
        """Get client identifier for rate limiting"""
        # Use X-Forwarded-For header if present (behind proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.remote_addr or 'unknown'

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(limit: int = 60, window: int = 60, block_on_exceed: bool = True):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_ip = rate_limiter.get_client_identifier()
            
            # Check if IP is blocked
            if rate_limiter.is_ip_blocked(client_ip):
                logger.warning(f"Blocked IP attempted access", 
                             blocked_ip=client_ip, 
                             endpoint=request.endpoint)
                return jsonify(ErrorHandler.handle_error('RATE_LIMIT_EXCEEDED', 
                    Exception('IP temporarily blocked'))), 429
            
            # Check rate limiting
            if rate_limiter.is_rate_limited(client_ip, limit, window):
                if block_on_exceed:
                    rate_limiter.record_failed_attempt(client_ip)
                    
                logger.warning(f"Rate limit exceeded", 
                             client_ip=client_ip, 
                             endpoint=request.endpoint,
                             limit=limit, 
                             window=window)
                             
                return jsonify(ErrorHandler.handle_error('RATE_LIMIT_EXCEEDED', 
                    Exception(f'Rate limit exceeded: {limit} requests per {window} seconds'))), 429
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    # Regex patterns for validation
    PATTERNS = {
        'device_id': re.compile(r'^[a-zA-Z0-9_-]{1,50}$'),
        'ip_address': re.compile(r'^(\d{1,3}\.){3}\d{1,3}$'),
        'hostname': re.compile(r'^[a-zA-Z0-9-]{1,63}(\.[a-zA-Z0-9-]{1,63})*$'),
        'mac_address': re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'),
        'firmware_version': re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$'),
        'topic': re.compile(r'^[a-zA-Z0-9/_-]{1,100}$'),
        'safe_string': re.compile(r'^[a-zA-Z0-9\s\._-]{1,200}$'),
        'filename': re.compile(r'^[a-zA-Z0-9\._-]{1,100}\.[a-zA-Z0-9]{1,10}$')
    }
    
    # Maximum lengths for different field types
    MAX_LENGTHS = {
        'short_string': 50,
        'medium_string': 200,
        'long_string': 1000,
        'json_payload': 10000,
        'firmware_file': 50 * 1024 * 1024  # 50MB
    }
    
    @classmethod
    def validate_string(cls, value: str, pattern_name: str = 'safe_string', 
                       max_length: int = None) -> bool:
        """Validate string against pattern and length"""
        if not isinstance(value, str):
            return False
            
        if max_length and len(value) > max_length:
            return False
            
        if pattern_name in cls.PATTERNS:
            return bool(cls.PATTERNS[pattern_name].match(value))
            
        return True
        
    @classmethod
    def validate_ip_address(cls, ip_str: str) -> bool:
        """Validate IP address"""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
            
    @classmethod
    def validate_json_payload(cls, data: Dict[str, Any], max_size: int = None) -> bool:
        """Validate JSON payload size and structure"""
        try:
            json_str = json.dumps(data)
            max_size = max_size or cls.MAX_LENGTHS['json_payload']
            return len(json_str) <= max_size
        except (TypeError, ValueError):
            return False
            
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 200) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
            
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>\"\'&;]', '', value)
        
        # Limit length
        return sanitized[:max_length].strip()
        
    @classmethod
    def validate_device_config(cls, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate device configuration"""
        required_fields = ['device_id', 'name']
        
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"
                
        # Validate device_id
        if not cls.validate_string(config['device_id'], 'device_id'):
            return False, "Invalid device_id format"
            
        # Validate name
        if not cls.validate_string(config['name'], 'safe_string', 100):
            return False, "Invalid device name format"
            
        # Validate IP if present
        if 'ip' in config and not cls.validate_ip_address(config['ip']):
            return False, "Invalid IP address format"
            
        return True, None
        
    @classmethod
    def validate_firmware_upload(cls, filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """Validate firmware upload"""
        # Check filename
        if not cls.validate_string(filename, 'filename'):
            return False, "Invalid filename format"
            
        # Check file extension
        allowed_extensions = ['.bin', '.ino.bin', '.firmware']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            return False, "Invalid file extension"
            
        # Check file size
        if file_size > cls.MAX_LENGTHS['firmware_file']:
            return False, "File size exceeds maximum allowed"
            
        return True, None

def validate_input(**validators):
    """Decorator for input validation"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate JSON payload if present
            if request.is_json:
                data = request.get_json()
                if data is None:
                    return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                        Exception('Invalid JSON payload'))), 400
                        
                if not InputValidator.validate_json_payload(data):
                    return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                        Exception('JSON payload too large'))), 400
                        
                # Apply specific validators
                for field, validator_name in validators.items():
                    if field in data:
                        value = data[field]
                        if validator_name == 'device_id':
                            if not InputValidator.validate_string(value, 'device_id'):
                                return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                                    Exception(f'Invalid {field} format'))), 400
                        elif validator_name == 'ip_address':
                            if not InputValidator.validate_ip_address(value):
                                return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                                    Exception(f'Invalid {field} format'))), 400
                        elif validator_name == 'safe_string':
                            if not InputValidator.validate_string(value, 'safe_string'):
                                return jsonify(ErrorHandler.handle_error('INVALID_INPUT', 
                                    Exception(f'Invalid {field} format'))), 400
                                    
            return func(*args, **kwargs)
        return wrapper
    return decorator

class CSRFProtection:
    """CSRF protection for web interface"""
    
    @staticmethod
    def generate_token() -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)
        
    @staticmethod
    def get_token_from_request() -> Optional[str]:
        """Get CSRF token from request"""
        # Try header first
        token = request.headers.get('X-CSRF-Token')
        if token:
            return token
            
        # Try form data
        if request.form:
            return request.form.get('csrf_token')
            
        # Try JSON data
        if request.is_json:
            data = request.get_json()
            return data.get('csrf_token') if data else None
            
        return None
        
    @staticmethod
    def validate_token(token: str) -> bool:
        """Validate CSRF token"""
        session_token = session.get('csrf_token')
        if not session_token or not token:
            return False
            
        return secrets.compare_digest(session_token, token)

def csrf_protect(func):
    """CSRF protection decorator"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = CSRFProtection.get_token_from_request()
            if not token or not CSRFProtection.validate_token(token):
                logger.warning("CSRF token validation failed", 
                             endpoint=request.endpoint,
                             method=request.method,
                             client_ip=rate_limiter.get_client_identifier())
                return jsonify(ErrorHandler.handle_error('CSRF_TOKEN_INVALID', 
                    Exception('CSRF token validation failed'))), 403
                    
        return func(*args, **kwargs)
    return wrapper

class SecurityHeaders:
    """Security headers middleware"""
    
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    @classmethod
    def add_security_headers(cls, response):
        """Add security headers to response"""
        for header, value in cls.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

def add_security_headers(func):
    """Decorator to add security headers"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        return SecurityHeaders.add_security_headers(response)
    return wrapper

# Update ErrorHandler with security-related errors
ErrorHandler.ERROR_CODES.update({
    'RATE_LIMIT_EXCEEDED': {
        'user_message': 'Too many requests. Please wait a moment before trying again.',
        'technical_details': 'Rate limit exceeded for client IP'
    },
    'INVALID_INPUT': {
        'user_message': 'Invalid input provided. Please check your data and try again.',
        'technical_details': 'Input validation failed'
    },
    'CSRF_TOKEN_INVALID': {
        'user_message': 'Security validation failed. Please refresh the page and try again.',
        'technical_details': 'CSRF token validation failed'
    },
    'IP_BLOCKED': {
        'user_message': 'Access temporarily restricted. Please try again later.',
        'technical_details': 'IP address temporarily blocked due to suspicious activity'
    }
})