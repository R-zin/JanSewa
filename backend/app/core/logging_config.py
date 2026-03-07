"""
Structured logging configuration with PII sanitization.

This module provides:
- Structured JSON logging for all components
- PII sanitization in logs
- Log rotation and retention policies
- Context-aware logging with request IDs
"""

import logging
import logging.handlers
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path

from app.services.privacy_controls import SensitiveDataType


class PIISanitizer:
    """Sanitizes PII from log messages"""
    
    # PII patterns to detect and sanitize
    PII_PATTERNS = {
        'aadhaar': (r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR-REDACTED]'),
        'pan': (r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN-REDACTED]'),
        'phone': (r'\b\d{10}\b', '[PHONE-REDACTED]'),
        'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL-REDACTED]'),
        'password': (r'(?i)(password|passwd|pwd)[\s:=]+\S+', '[PASSWORD-REDACTED]'),
        'bearer_token': (r'(?i)bearer\s+(token[\s:=]+)?\S+', '[BEARER-TOKEN-REDACTED]'),
        'token': (r'(?i)(token|jwt)[\s:=]+\S+', '[TOKEN-REDACTED]'),
        'api_key': (r'(?i)(api[_-]?key|apikey)[\s:=]+\S+', '[APIKEY-REDACTED]'),
    }
    
    @classmethod
    def sanitize(cls, message: str) -> str:
        """
        Sanitize PII from log message.
        
        Args:
            message: Original log message
            
        Returns:
            Sanitized log message with PII redacted
        """
        sanitized = message
        
        for pattern_name, (pattern, replacement) in cls.PII_PATTERNS.items():
            sanitized = re.sub(pattern, replacement, sanitized)
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize PII from dictionary.
        
        Args:
            data: Dictionary potentially containing PII
            
        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        sensitive_keys = {
            'password', 'passwd', 'pwd', 'token', 'api_key', 'apikey',
            'secret', 'aadhaar', 'pan', 'phone', 'email', 'address'
        }
        
        for key, value in data.items():
            # Check if key indicates sensitive data
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize(value)
            else:
                sanitized[key] = value
        
        return sanitized


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON with PII sanitization.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Base log structure
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': PIISanitizer.sanitize(record.getMessage()),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': PIISanitizer.sanitize(str(record.exc_info[1])) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add context from extra fields
        if self.include_context:
            context = {}
            
            # Request context
            if hasattr(record, 'request_id'):
                context['request_id'] = record.request_id
            if hasattr(record, 'user_id'):
                context['user_id'] = record.user_id
            if hasattr(record, 'session_id'):
                context['session_id'] = record.session_id
            if hasattr(record, 'service_id'):
                context['service_id'] = record.service_id
            
            # Operation context
            if hasattr(record, 'operation'):
                context['operation'] = record.operation
            if hasattr(record, 'duration_ms'):
                context['duration_ms'] = record.duration_ms
            
            # Additional data
            if hasattr(record, 'extra_data'):
                context['data'] = PIISanitizer.sanitize_dict(record.extra_data)
            
            if context:
                log_data['context'] = context
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for console output"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record for console with colors and PII sanitization.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string
        """
        # Sanitize message
        message = PIISanitizer.sanitize(record.getMessage())
        
        # Add color
        color = self.COLORS.get(record.levelname, '')
        level = f"{color}{record.levelname:8}{self.RESET}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build log line
        log_line = f"{timestamp} | {level} | {record.name:30} | {message}"
        
        # Add context if available
        context_parts = []
        if hasattr(record, 'request_id'):
            context_parts.append(f"req={record.request_id[:8]}")
        if hasattr(record, 'user_id'):
            context_parts.append(f"user={record.user_id}")
        if hasattr(record, 'operation'):
            context_parts.append(f"op={record.operation}")
        
        if context_parts:
            log_line += f" [{', '.join(context_parts)}]"
        
        # Add exception if present
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"
        
        return log_line


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configure application logging with structured output and PII sanitization.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: ./logs)
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_json: Enable JSON structured logging to file
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup log files to keep
    """
    # Create log directory
    if log_dir is None:
        log_dir = "logs"
    
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with human-readable format
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ConsoleFormatter())
        root_logger.addHandler(console_handler)
    
    # File handler with human-readable format
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "application.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(ConsoleFormatter())
        root_logger.addHandler(file_handler)
    
    # JSON file handler for structured logging
    if enable_json:
        json_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "application.json",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(StructuredFormatter(include_context=True))
        root_logger.addHandler(json_handler)
    
    # Error log file (only errors and critical)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter(include_context=True))
    root_logger.addHandler(error_handler)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={log_level}, console={enable_console}, "
        f"file={enable_file}, json={enable_json}, dir={log_dir}"
    )


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context to all log messages.
    
    Usage:
        logger = LoggerAdapter(logging.getLogger(__name__), {
            'request_id': '12345',
            'user_id': 'user_123'
        })
        logger.info("Processing request")
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process log message and add context.
        
        Args:
            msg: Log message
            kwargs: Additional keyword arguments
            
        Returns:
            Tuple of (message, kwargs) with context added
        """
        # Add context to extra
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        
        return msg, kwargs


def get_logger(name: str, **context) -> logging.Logger:
    """
    Get a logger with optional context.
    
    Args:
        name: Logger name (usually __name__)
        **context: Context to add to all log messages
        
    Returns:
        Logger or LoggerAdapter with context
    """
    logger = logging.getLogger(name)
    
    if context:
        return LoggerAdapter(logger, context)
    
    return logger
