"""
Unit Tests for SessionManager Component

**Validates: Requirements 10.1**

Tests session creation, cleanup, context storage/retrieval, and timeout scenarios.
"""

import pytest
import fakeredis
from unittest.mock import patch
from datetime import timedelta
import json
import time

from app.services.session_manager import SessionManager


# Create a fake Redis server for testing
fake_redis_server = fakeredis.FakeServer()


@pytest.fixture
def mock_redis():
    """Fixture to provide a fresh fake Redis client for each test"""
    client = fakeredis.FakeRedis(server=fake_redis_server, decode_responses=True)
    # Clear all keys before each test
    client.flushall()
    return client


@pytest.fixture
def session_manager(mock_redis):
    """Fixture to provide a SessionManager with mocked Redis"""
    with patch.object(SessionManager, '__init__', lambda self: None):
        manager = SessionManager()
        manager.redis_client = mock_redis
        manager.session_timeout = timedelta(minutes=30)
        return manager


class TestSessionCreation:
    """Test session creation functionality"""
    
    def test_create_session_basic(self, session_manager):
        """Test basic session creation"""
        user_id = 123
        language = "en"
        
        session_id = session_manager.create_session(user_id, language)
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
    
    def test_create_session_stores_data(self, session_manager):
        """Test that session creation stores correct data"""
        user_id = 456
        language = "hi"
        
        session_id = session_manager.create_session(user_id, language)
        session_data = session_manager.get_session(session_id)
        
        assert session_data is not None
        assert session_data["session_id"] == session_id
        assert session_data["user_id"] == user_id
        assert session_data["language"] == language
        assert "start_time" in session_data
        assert "conversation_history" in session_data
        assert "temporary_context" in session_data
        assert isinstance(session_data["conversation_history"], list)
        assert isinstance(session_data["temporary_context"], dict)
    
    def test_create_session_default_language(self, session_manager):
        """Test session creation with default language"""
        user_id = 789
        
        session_id = session_manager.create_session(user_id)
        session_data = session_manager.get_session(session_id)
        
        assert session_data["language"] == "en"
    
    def test_create_multiple_sessions(self, session_manager):
        """Test creating multiple sessions for different users"""
        session_id_1 = session_manager.create_session(100, "en")
        session_id_2 = session_manager.create_session(200, "hi")
        session_id_3 = session_manager.create_session(300, "ta")
        
        # All sessions should have unique IDs
        assert session_id_1 != session_id_2
        assert session_id_2 != session_id_3
        assert session_id_1 != session_id_3
        
        # All sessions should be retrievable
        assert session_manager.get_session(session_id_1) is not None
        assert session_manager.get_session(session_id_2) is not None
        assert session_manager.get_session(session_id_3) is not None


class TestContextStorageAndRetrieval:
    """Test context storage and retrieval functionality"""
    
    def test_update_context_basic(self, session_manager):
        """Test basic context update"""
        session_id = session_manager.create_session(123, "en")
        
        result = session_manager.update_context(session_id, "service_id", "aadhaar_update")
        
        assert result is True
        value = session_manager.get_context(session_id, "service_id")
        assert value == "aadhaar_update"
    
    def test_update_context_multiple_keys(self, session_manager):
        """Test updating multiple context keys"""
        session_id = session_manager.create_session(456, "hi")
        
        session_manager.update_context(session_id, "service_id", "pan_card")
        session_manager.update_context(session_id, "step", 3)
        session_manager.update_context(session_id, "form_data", {"name": "Test User"})
        
        assert session_manager.get_context(session_id, "service_id") == "pan_card"
        assert session_manager.get_context(session_id, "step") == 3
        assert session_manager.get_context(session_id, "form_data") == {"name": "Test User"}
    
    def test_update_context_overwrite(self, session_manager):
        """Test that updating context overwrites previous value"""
        session_id = session_manager.create_session(789, "en")
        
        session_manager.update_context(session_id, "status", "pending")
        assert session_manager.get_context(session_id, "status") == "pending"
        
        session_manager.update_context(session_id, "status", "completed")
        assert session_manager.get_context(session_id, "status") == "completed"
    
    def test_get_context_nonexistent_key(self, session_manager):
        """Test getting context for a key that doesn't exist"""
        session_id = session_manager.create_session(111, "en")
        
        value = session_manager.get_context(session_id, "nonexistent_key")
        
        assert value is None
    
    def test_update_context_invalid_session(self, session_manager):
        """Test updating context for non-existent session"""
        result = session_manager.update_context("invalid_session_id", "key", "value")
        
        assert result is False
    
    def test_get_context_invalid_session(self, session_manager):
        """Test getting context for non-existent session"""
        value = session_manager.get_context("invalid_session_id", "key")
        
        assert value is None
    
    def test_context_with_complex_data_types(self, session_manager):
        """Test storing complex data types in context"""
        session_id = session_manager.create_session(222, "en")
        
        # Test with list
        session_manager.update_context(session_id, "documents", ["doc1", "doc2", "doc3"])
        assert session_manager.get_context(session_id, "documents") == ["doc1", "doc2", "doc3"]
        
        # Test with nested dict
        complex_data = {
            "user": {"name": "Test", "age": 30},
            "preferences": {"language": "en", "notifications": True}
        }
        session_manager.update_context(session_id, "user_data", complex_data)
        assert session_manager.get_context(session_id, "user_data") == complex_data


class TestSensitiveDataClearing:
    """Test sensitive data clearing functionality"""
    
    def test_clear_sensitive_data_basic(self, session_manager):
        """Test clearing sensitive data from session"""
        session_id = session_manager.create_session(333, "en")
        
        # Add sensitive data
        session_manager.update_context(session_id, "aadhaar_number", "123456789012")
        session_manager.update_context(session_id, "phone", "9876543210")
        session_manager.update_context(session_id, "address", "123 Test Street")
        
        # Add non-sensitive data
        session_manager.update_context(session_id, "service_id", "aadhaar_update")
        
        # Clear sensitive data
        result = session_manager.clear_sensitive_data(session_id)
        
        assert result is True
        
        # Verify sensitive data is removed
        assert session_manager.get_context(session_id, "aadhaar_number") is None
        assert session_manager.get_context(session_id, "phone") is None
        assert session_manager.get_context(session_id, "address") is None
        
        # Verify non-sensitive data remains
        assert session_manager.get_context(session_id, "service_id") == "aadhaar_update"
    
    def test_clear_sensitive_data_all_types(self, session_manager):
        """Test clearing all types of sensitive data"""
        session_id = session_manager.create_session(444, "hi")
        
        sensitive_keys = {
            "aadhaar_number": "123456789012",
            "pan_number": "ABCDE1234F",
            "phone": "9876543210",
            "address": "Test Address",
            "personal_info": {"dob": "1990-01-01"}
        }
        
        for key, value in sensitive_keys.items():
            session_manager.update_context(session_id, key, value)
        
        # Clear sensitive data
        session_manager.clear_sensitive_data(session_id)
        
        # Verify all sensitive keys are removed
        for key in sensitive_keys.keys():
            assert session_manager.get_context(session_id, key) is None
    
    def test_clear_sensitive_data_session_remains_active(self, session_manager):
        """Test that session remains active after clearing sensitive data"""
        session_id = session_manager.create_session(555, "en")
        
        session_manager.update_context(session_id, "aadhaar_number", "123456789012")
        session_manager.update_context(session_id, "service_id", "test_service")
        
        session_manager.clear_sensitive_data(session_id)
        
        # Session should still exist
        session_data = session_manager.get_session(session_id)
        assert session_data is not None
        assert session_data["session_id"] == session_id
        
        # Non-sensitive data should still be accessible
        assert session_manager.get_context(session_id, "service_id") == "test_service"
    
    def test_clear_sensitive_data_invalid_session(self, session_manager):
        """Test clearing sensitive data for non-existent session"""
        result = session_manager.clear_sensitive_data("invalid_session_id")
        
        assert result is False


class TestSessionCleanup:
    """Test session cleanup and termination"""
    
    def test_end_session_basic(self, session_manager):
        """Test basic session termination"""
        session_id = session_manager.create_session(666, "en")
        
        # Verify session exists
        assert session_manager.get_session(session_id) is not None
        
        # End session
        result = session_manager.end_session(session_id)
        
        assert result is True
        
        # Verify session is removed
        assert session_manager.get_session(session_id) is None
    
    def test_end_session_removes_all_data(self, session_manager):
        """Test that ending session removes all associated data"""
        session_id = session_manager.create_session(777, "hi")
        
        # Add various data
        session_manager.update_context(session_id, "key1", "value1")
        session_manager.update_context(session_id, "key2", "value2")
        session_manager.update_context(session_id, "aadhaar_number", "123456789012")
        
        # End session
        session_manager.end_session(session_id)
        
        # Verify all data is inaccessible
        assert session_manager.get_context(session_id, "key1") is None
        assert session_manager.get_context(session_id, "key2") is None
        assert session_manager.get_context(session_id, "aadhaar_number") is None
    
    def test_end_session_invalid_session(self, session_manager):
        """Test ending a non-existent session"""
        result = session_manager.end_session("invalid_session_id")
        
        assert result is False
    
    def test_end_session_idempotent(self, session_manager):
        """Test that ending a session multiple times is safe"""
        session_id = session_manager.create_session(888, "en")
        
        # End session first time
        result1 = session_manager.end_session(session_id)
        assert result1 is True
        
        # End session second time
        result2 = session_manager.end_session(session_id)
        assert result2 is False  # Session already ended
    
    def test_end_session_isolation(self, session_manager):
        """Test that ending one session doesn't affect others"""
        session_id_1 = session_manager.create_session(100, "en")
        session_id_2 = session_manager.create_session(200, "hi")
        
        session_manager.update_context(session_id_1, "data", "session1")
        session_manager.update_context(session_id_2, "data", "session2")
        
        # End first session
        session_manager.end_session(session_id_1)
        
        # Verify first session is gone
        assert session_manager.get_session(session_id_1) is None
        
        # Verify second session is unaffected
        assert session_manager.get_session(session_id_2) is not None
        assert session_manager.get_context(session_id_2, "data") == "session2"


class TestSessionTimeout:
    """Test session timeout scenarios"""
    
    def test_session_has_expiration(self, session_manager, mock_redis):
        """Test that sessions are created with expiration time"""
        session_id = session_manager.create_session(999, "en")
        
        # Check TTL in Redis
        ttl = mock_redis.ttl(f"session:{session_id}")
        
        # TTL should be set (positive value)
        assert ttl > 0
        # Should be approximately 30 minutes (1800 seconds)
        assert ttl <= 1800
        assert ttl > 1700  # Allow some margin for test execution time
    
    def test_extend_session_basic(self, session_manager):
        """Test extending session timeout"""
        session_id = session_manager.create_session(1000, "en")
        
        result = session_manager.extend_session(session_id)
        
        assert result is True
    
    def test_extend_session_invalid(self, session_manager):
        """Test extending non-existent session"""
        result = session_manager.extend_session("invalid_session_id")
        
        assert result is False
    
    def test_extend_session_after_end(self, session_manager):
        """Test that extending ended session fails"""
        session_id = session_manager.create_session(1001, "en")
        
        session_manager.end_session(session_id)
        
        result = session_manager.extend_session(session_id)
        
        assert result is False
    
    def test_session_expiration_simulation(self, session_manager, mock_redis):
        """Test session expiration behavior (simulated)"""
        # Create session with very short timeout for testing
        session_manager.session_timeout = timedelta(seconds=1)
        session_id = session_manager.create_session(1002, "en")
        
        # Verify session exists
        assert session_manager.get_session(session_id) is not None
        
        # Manually expire the key in fake Redis
        mock_redis.delete(f"session:{session_id}")
        
        # Verify session is no longer accessible
        assert session_manager.get_session(session_id) is None
    
    def test_update_context_extends_timeout(self, session_manager, mock_redis):
        """Test that updating context resets the expiration timer"""
        session_id = session_manager.create_session(1003, "en")
        
        # Get initial TTL
        initial_ttl = mock_redis.ttl(f"session:{session_id}")
        
        # Wait a moment
        time.sleep(0.1)
        
        # Update context (this should reset TTL)
        session_manager.update_context(session_id, "test_key", "test_value")
        
        # Get new TTL
        new_ttl = mock_redis.ttl(f"session:{session_id}")
        
        # New TTL should be close to the full timeout duration
        # (allowing for small time differences in test execution)
        assert new_ttl >= initial_ttl - 1


class TestSessionRetrieval:
    """Test session retrieval functionality"""
    
    def test_get_session_basic(self, session_manager):
        """Test basic session retrieval"""
        session_id = session_manager.create_session(1004, "en")
        
        session_data = session_manager.get_session(session_id)
        
        assert session_data is not None
        assert isinstance(session_data, dict)
    
    def test_get_session_nonexistent(self, session_manager):
        """Test retrieving non-existent session"""
        session_data = session_manager.get_session("nonexistent_session_id")
        
        assert session_data is None
    
    def test_get_session_structure(self, session_manager):
        """Test that retrieved session has correct structure"""
        user_id = 1005
        language = "ta"
        session_id = session_manager.create_session(user_id, language)
        
        session_data = session_manager.get_session(session_id)
        
        # Verify all required fields are present
        required_fields = [
            "session_id",
            "user_id",
            "start_time",
            "language",
            "conversation_history",
            "temporary_context"
        ]
        
        for field in required_fields:
            assert field in session_data, f"Missing required field: {field}"
        
        # Verify field values
        assert session_data["session_id"] == session_id
        assert session_data["user_id"] == user_id
        assert session_data["language"] == language


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_context_key(self, session_manager):
        """Test handling empty context key"""
        session_id = session_manager.create_session(1006, "en")
        
        session_manager.update_context(session_id, "", "value")
        value = session_manager.get_context(session_id, "")
        
        assert value == "value"
    
    def test_none_context_value(self, session_manager):
        """Test storing None as context value"""
        session_id = session_manager.create_session(1007, "en")
        
        session_manager.update_context(session_id, "test_key", None)
        value = session_manager.get_context(session_id, "test_key")
        
        assert value is None
    
    def test_large_context_data(self, session_manager):
        """Test storing large data in context"""
        session_id = session_manager.create_session(1008, "en")
        
        # Create large data structure
        large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        
        result = session_manager.update_context(session_id, "large_data", large_data)
        
        assert result is True
        retrieved = session_manager.get_context(session_id, "large_data")
        assert retrieved == large_data
    
    def test_special_characters_in_keys(self, session_manager):
        """Test context keys with special characters"""
        session_id = session_manager.create_session(1009, "en")
        
        special_keys = [
            "key-with-dash",
            "key_with_underscore",
            "key.with.dot",
            "key:with:colon"
        ]
        
        for key in special_keys:
            session_manager.update_context(session_id, key, f"value_for_{key}")
            value = session_manager.get_context(session_id, key)
            assert value == f"value_for_{key}"
    
    def test_unicode_in_context(self, session_manager):
        """Test storing Unicode characters in context"""
        session_id = session_manager.create_session(1010, "hi")
        
        unicode_data = {
            "hindi": "नमस्ते",
            "tamil": "வணக்கம்",
            "emoji": "😀🎉",
            "mixed": "Hello नमस्ते 世界"
        }
        
        for key, value in unicode_data.items():
            session_manager.update_context(session_id, key, value)
            retrieved = session_manager.get_context(session_id, key)
            assert retrieved == value
