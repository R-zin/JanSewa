"""
Integration tests for AuditLogger service

These tests verify the audit logger functionality without requiring
a full database setup.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import json

from app.services.audit_logger import (
    AuditAction,
    AuditLogFilters,
    AuditLogEntryResponse
)


class TestAuditLoggerIntegration:
    """Integration tests for AuditLogger"""
    
    def test_audit_action_enum(self):
        """Test that all audit actions are defined"""
        assert AuditAction.UPLOAD.value == "upload"
        assert AuditAction.RETRIEVE.value == "retrieve"
        assert AuditAction.DELETE.value == "delete"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.PREVIEW.value == "preview"
        assert AuditAction.SHARE.value == "share"
        assert AuditAction.CATEGORIZE.value == "categorize"
        assert AuditAction.VERSION_UPLOAD.value == "version_upload"
    
    def test_audit_log_filters_creation(self):
        """Test creating audit log filters"""
        filters = AuditLogFilters(
            user_id=123,
            document_id=456,
            action=AuditAction.UPLOAD,
            result="success",
            limit=50,
            offset=10
        )
        
        assert filters.user_id == 123
        assert filters.document_id == 456
        assert filters.action == AuditAction.UPLOAD
        assert filters.result == "success"
        assert filters.limit == 50
        assert filters.offset == 10
    
    def test_audit_log_filters_defaults(self):
        """Test default values for audit log filters"""
        filters = AuditLogFilters()
        
        assert filters.user_id is None
        assert filters.document_id is None
        assert filters.action is None
        assert filters.start_date is None
        assert filters.end_date is None
        assert filters.result is None
        assert filters.limit == 100
        assert filters.offset == 0
    
    def test_audit_log_entry_response_model(self):
        """Test the audit log entry response model"""
        entry = AuditLogEntryResponse(
            id=1,
            timestamp=datetime.utcnow(),
            user_id=123,
            document_id=456,
            action="upload",
            result="success",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details='{"file_name": "test.pdf"}'
        )
        
        assert entry.id == 1
        assert entry.user_id == 123
        assert entry.document_id == 456
        assert entry.action == "upload"
        assert entry.result == "success"
        assert entry.ip_address == "192.168.1.1"
        assert entry.user_agent == "Mozilla/5.0"
    
    def test_audit_log_with_date_range(self):
        """Test creating filters with date range"""
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()
        
        filters = AuditLogFilters(
            user_id=123,
            start_date=start,
            end_date=end
        )
        
        assert filters.start_date == start
        assert filters.end_date == end
    
    def test_audit_log_pagination(self):
        """Test pagination parameters"""
        # First page
        filters_page1 = AuditLogFilters(limit=10, offset=0)
        assert filters_page1.limit == 10
        assert filters_page1.offset == 0
        
        # Second page
        filters_page2 = AuditLogFilters(limit=10, offset=10)
        assert filters_page2.limit == 10
        assert filters_page2.offset == 10
    
    def test_multiple_action_types(self):
        """Test different action types"""
        actions = [
            AuditAction.UPLOAD,
            AuditAction.RETRIEVE,
            AuditAction.DELETE,
            AuditAction.UPDATE,
            AuditAction.PREVIEW,
            AuditAction.SHARE,
            AuditAction.CATEGORIZE,
            AuditAction.VERSION_UPLOAD
        ]
        
        for action in actions:
            filters = AuditLogFilters(action=action)
            assert filters.action == action
    
    def test_result_types(self):
        """Test different result types"""
        results = ["success", "failure", "partial"]
        
        for result in results:
            filters = AuditLogFilters(result=result)
            assert filters.result == result
    
    @patch('app.services.audit_logger.AuditLogger')
    def test_audit_logger_mock(self, mock_logger_class):
        """Test audit logger with mocking"""
        # Create mock instance
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        # Mock log_operation to return an ID
        mock_logger.log_operation.return_value = 1
        
        # Create logger instance
        logger = mock_logger_class(Mock())
        
        # Verify it was created
        assert logger is not None
    
    def test_details_json_serialization(self):
        """Test that details can be serialized to JSON"""
        details = {
            "file_name": "test.pdf",
            "file_size": 2048,
            "category": "identity",
            "has_expiration": True
        }
        
        # Serialize to JSON
        json_details = json.dumps(details)
        
        # Deserialize back
        parsed_details = json.loads(json_details)
        
        assert parsed_details["file_name"] == "test.pdf"
        assert parsed_details["file_size"] == 2048
        assert parsed_details["category"] == "identity"
        assert parsed_details["has_expiration"] is True
    
    def test_ip_address_formats(self):
        """Test various IP address formats"""
        ip_addresses = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",  # IPv6
            None  # No IP address
        ]
        
        for ip in ip_addresses:
            entry = AuditLogEntryResponse(
                id=1,
                timestamp=datetime.utcnow(),
                user_id=123,
                document_id=456,
                action="upload",
                result="success",
                ip_address=ip,
                user_agent="Test",
                details=None
            )
            assert entry.ip_address == ip
    
    def test_user_agent_strings(self):
        """Test various user agent strings"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Chrome/91.0.4472.124",
            "Safari/14.1.1",
            "Mobile App/1.0",
            None  # No user agent
        ]
        
        for ua in user_agents:
            entry = AuditLogEntryResponse(
                id=1,
                timestamp=datetime.utcnow(),
                user_id=123,
                document_id=456,
                action="upload",
                result="success",
                ip_address="192.168.1.1",
                user_agent=ua,
                details=None
            )
            assert entry.user_agent == ua


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
