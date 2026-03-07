"""
Unit tests for structured logging with PII sanitization.

Tests:
- PII sanitization in log messages
- Structured JSON formatting
- Console formatting
- Log rotation configuration
- Context-aware logging
"""

import pytest
import logging
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from app.core.logging_config import (
    PIISanitizer,
    StructuredFormatter,
    ConsoleFormatter,
    setup_logging,
    get_logger,
    LoggerAdapter,
)


class TestPIISanitizer:
    """Test PII sanitization functionality"""
    
    def test_sanitize_aadhaar_number(self):
        """Test Aadhaar number sanitization"""
        message = "User Aadhaar: 1234 5678 9012"
        sanitized = PIISanitizer.sanitize(message)
        assert "[AADHAAR-REDACTED]" in sanitized
        assert "1234 5678 9012" not in sanitized
    
    def test_sanitize_aadhaar_without_spaces(self):
        """Test Aadhaar number sanitization without spaces"""
        message = "Aadhaar: 123456789012"
        sanitized = PIISanitizer.sanitize(message)
        assert "[AADHAAR-REDACTED]" in sanitized
        assert "123456789012" not in sanitized
    
    def test_sanitize_pan_number(self):
        """Test PAN number sanitization"""
        message = "PAN: ABCDE1234F"
        sanitized = PIISanitizer.sanitize(message)
        assert "[PAN-REDACTED]" in sanitized
        assert "ABCDE1234F" not in sanitized
    
    def test_sanitize_phone_number(self):
        """Test phone number sanitization"""
        message = "Contact: 9876543210"
        sanitized = PIISanitizer.sanitize(message)
        assert "[PHONE-REDACTED]" in sanitized
        assert "9876543210" not in sanitized
    
    def test_sanitize_email(self):
        """Test email sanitization"""
        message = "Email: user@example.com"
        sanitized = PIISanitizer.sanitize(message)
        assert "[EMAIL-REDACTED]" in sanitized
        assert "user@example.com" not in sanitized
    
    def test_sanitize_password(self):
        """Test password sanitization"""
        test_cases = [
            "password: secret123",
            "Password=mypass",
            "pwd: test",
        ]
        for message in test_cases:
            sanitized = PIISanitizer.sanitize(message)
            assert "[PASSWORD-REDACTED]" in sanitized
    
    def test_sanitize_token(self):
        """Test token sanitization"""
        message = "Bearer token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = PIISanitizer.sanitize(message)
        assert "[TOKEN-REDACTED]" in sanitized or "[BEARER-TOKEN-REDACTED]" in sanitized
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
    
    def test_sanitize_api_key(self):
        """Test API key sanitization"""
        message = "api_key: sk_test_1234567890"
        sanitized = PIISanitizer.sanitize(message)
        assert "[APIKEY-REDACTED]" in sanitized
        assert "sk_test_1234567890" not in sanitized
    
    def test_sanitize_multiple_pii(self):
        """Test sanitization of multiple PII types in one message"""
        message = "User 9876543210 with email user@test.com and Aadhaar 1234 5678 9012"
        sanitized = PIISanitizer.sanitize(message)
        assert "[PHONE-REDACTED]" in sanitized
        assert "[EMAIL-REDACTED]" in sanitized
        assert "[AADHAAR-REDACTED]" in sanitized
        assert "9876543210" not in sanitized
        assert "user@test.com" not in sanitized
        assert "1234 5678 9012" not in sanitized
    
    def test_sanitize_dict_with_sensitive_keys(self):
        """Test dictionary sanitization with sensitive keys"""
        data = {
            'username': 'john',
            'password': 'secret123',
            'email': 'john@example.com',
            'aadhaar': '123456789012',
            'normal_field': 'safe_value'
        }
        sanitized = PIISanitizer.sanitize_dict(data)
        
        assert sanitized['username'] == 'john'
        assert sanitized['password'] == '[REDACTED]'
        assert sanitized['email'] == '[REDACTED]'
        assert sanitized['aadhaar'] == '[REDACTED]'
        assert sanitized['normal_field'] == 'safe_value'
    
    def test_sanitize_nested_dict(self):
        """Test nested dictionary sanitization"""
        data = {
            'user': {
                'name': 'John',
                'password': 'secret',
                'contact': {
                    'phone': '9876543210',
                    'email': 'john@test.com'
                }
            }
        }
        sanitized = PIISanitizer.sanitize_dict(data)
        
        assert sanitized['user']['name'] == 'John'
        assert sanitized['user']['password'] == '[REDACTED]'
        assert sanitized['user']['contact']['phone'] == '[REDACTED]'
        assert sanitized['user']['contact']['email'] == '[REDACTED]'
    
    def test_sanitize_dict_with_string_values(self):
        """Test dictionary with string values containing PII"""
        data = {
            'message': 'User Aadhaar is 1234 5678 9012',
            'description': 'Contact at user@example.com'
        }
        sanitized = PIISanitizer.sanitize_dict(data)
        
        assert '[AADHAAR-REDACTED]' in sanitized['message']
        assert '[EMAIL-REDACTED]' in sanitized['description']
    
    def test_sanitize_list_in_dict(self):
        """Test dictionary with list containing dictionaries"""
        data = {
            'users': [
                {'name': 'John', 'password': 'secret1'},
                {'name': 'Jane', 'password': 'secret2'}
            ]
        }
        sanitized = PIISanitizer.sanitize_dict(data)
        
        assert sanitized['users'][0]['password'] == '[REDACTED]'
        assert sanitized['users'][1]['password'] == '[REDACTED]'


class TestStructuredFormatter:
    """Test structured JSON formatter"""
    
    def test_basic_log_formatting(self):
        """Test basic log record formatting"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['level'] == 'INFO'
        assert log_data['logger'] == 'test.logger'
        assert log_data['message'] == 'Test message'
        assert log_data['line'] == 10
        assert 'timestamp' in log_data
    
    def test_log_with_pii_sanitization(self):
        """Test log formatting with PII sanitization"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='User Aadhaar: 1234 5678 9012',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert '[AADHAAR-REDACTED]' in log_data['message']
        assert '1234 5678 9012' not in log_data['message']
    
    def test_log_with_context(self):
        """Test log formatting with context"""
        formatter = StructuredFormatter(include_context=True)
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.request_id = 'req-123'
        record.user_id = 'user-456'
        record.operation = 'test_operation'
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert 'context' in log_data
        assert log_data['context']['request_id'] == 'req-123'
        assert log_data['context']['user_id'] == 'user-456'
        assert log_data['context']['operation'] == 'test_operation'
    
    def test_log_with_extra_data(self):
        """Test log formatting with extra data"""
        formatter = StructuredFormatter(include_context=True)
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.extra_data = {
            'key1': 'value1',
            'password': 'secret'
        }
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert 'context' in log_data
        assert 'data' in log_data['context']
        assert log_data['context']['data']['key1'] == 'value1'
        assert log_data['context']['data']['password'] == '[REDACTED]'
    
    def test_log_with_exception(self):
        """Test log formatting with exception"""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test error with Aadhaar 1234 5678 9012")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name='test.logger',
            level=logging.ERROR,
            pathname='test.py',
            lineno=10,
            msg='Error occurred',
            args=(),
            exc_info=exc_info
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert 'exception' in log_data
        assert log_data['exception']['type'] == 'ValueError'
        assert '[AADHAAR-REDACTED]' in log_data['exception']['message']


class TestConsoleFormatter:
    """Test console formatter"""
    
    def test_basic_console_formatting(self):
        """Test basic console log formatting"""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert 'INFO' in formatted
        assert 'test.logger' in formatted
        assert 'Test message' in formatted
    
    def test_console_pii_sanitization(self):
        """Test console formatting with PII sanitization"""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='User email: user@example.com',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert '[EMAIL-REDACTED]' in formatted
        assert 'user@example.com' not in formatted
    
    def test_console_with_context(self):
        """Test console formatting with context"""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.request_id = 'req-123456'
        record.user_id = 'user-789'
        
        formatted = formatter.format(record)
        
        assert 'req=req-1234' in formatted  # First 8 chars
        assert 'user=user-789' in formatted


class TestLoggingSetup:
    """Test logging setup and configuration"""
    
    def test_setup_logging_creates_directory(self):
        """Test that setup_logging creates log directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "test_logs"
            
            setup_logging(
                log_level="INFO",
                log_dir=str(log_dir),
                enable_console=False,
                enable_file=True,
                enable_json=True
            )
            
            assert log_dir.exists()
            assert log_dir.is_dir()
    
    def test_setup_logging_creates_log_files(self):
        """Test that setup_logging creates log files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "test_logs"
            
            setup_logging(
                log_level="INFO",
                log_dir=str(log_dir),
                enable_console=False,
                enable_file=True,
                enable_json=True
            )
            
            # Write a log message
            logger = logging.getLogger('test')
            logger.info("Test message")
            
            # Check files exist
            assert (log_dir / "application.log").exists()
            assert (log_dir / "application.json").exists()
            assert (log_dir / "errors.log").exists()
    
    def test_get_logger_without_context(self):
        """Test getting logger without context"""
        logger = get_logger('test.module')
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test.module'
    
    def test_get_logger_with_context(self):
        """Test getting logger with context"""
        logger = get_logger('test.module', request_id='req-123', user_id='user-456')
        assert isinstance(logger, LoggerAdapter)
        assert logger.extra['request_id'] == 'req-123'
        assert logger.extra['user_id'] == 'user-456'


class TestLoggerAdapter:
    """Test logger adapter functionality"""
    
    def test_logger_adapter_adds_context(self):
        """Test that logger adapter adds context to logs"""
        base_logger = logging.getLogger('test')
        adapter = LoggerAdapter(base_logger, {'request_id': 'req-123'})
        
        msg, kwargs = adapter.process('Test message', {})
        
        assert 'extra' in kwargs
        assert kwargs['extra']['request_id'] == 'req-123'
    
    def test_logger_adapter_merges_extra(self):
        """Test that logger adapter merges extra data"""
        base_logger = logging.getLogger('test')
        adapter = LoggerAdapter(base_logger, {'request_id': 'req-123'})
        
        msg, kwargs = adapter.process('Test message', {'extra': {'user_id': 'user-456'}})
        
        assert kwargs['extra']['request_id'] == 'req-123'
        assert kwargs['extra']['user_id'] == 'user-456'


class TestLogRotation:
    """Test log rotation configuration"""
    
    def test_log_rotation_settings(self):
        """Test that log rotation is configured correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "test_logs"
            
            max_bytes = 1024  # 1KB for testing
            backup_count = 3
            
            setup_logging(
                log_level="INFO",
                log_dir=str(log_dir),
                enable_console=False,
                enable_file=True,
                enable_json=False,
                max_bytes=max_bytes,
                backup_count=backup_count
            )
            
            # Get root logger and check handlers
            root_logger = logging.getLogger()
            
            # Find rotating file handlers
            rotating_handlers = [
                h for h in root_logger.handlers
                if isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            
            assert len(rotating_handlers) > 0
            
            for handler in rotating_handlers:
                assert handler.maxBytes == max_bytes
                assert handler.backupCount == backup_count


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
