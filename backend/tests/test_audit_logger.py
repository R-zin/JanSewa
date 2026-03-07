"""
Unit tests for AuditLogger service
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, MetaData, Table
from sqlalchemy.orm import sessionmaker, declarative_base
from unittest.mock import Mock, patch

from app.services.audit_logger import (
    AuditLogger,
    AuditAction,
    AuditLogFilters,
    create_audit_logger
)

# Create a separate Base for testing to avoid import issues
TestBase = declarative_base()


class AuditLogEntry(TestBase):
    """Test version of AuditLogEntry"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(Text, nullable=True)


# Test database setup
@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    
    # Create users table first
    metadata = MetaData()
    users = Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('email', String)
    )
    metadata.create_all(engine)
    
    # Create audit_logs table
    TestBase.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Insert a test user
    session.execute(users.insert().values(id=1, email="test@example.com"))
    session.commit()
    
    yield session
    session.close()


@pytest.fixture
def audit_logger(db_session):
    """Create an AuditLogger instance for testing"""
    return AuditLogger(db_session)


class TestAuditLogger:
    """Test suite for AuditLogger"""
    
    @pytest.mark.asyncio
    async def test_log_upload_operation(self, audit_logger):
        """Test logging a document upload operation"""
        # Arrange
        user_id = 1
        document_id = 123
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        details = {"file_name": "test.pdf", "file_size": 1024}
        
        # Act
        log_id = await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=document_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        # Assert
        assert log_id is not None
        assert log_id > 0
    
    @pytest.mark.asyncio
    async def test_log_retrieve_operation(self, audit_logger):
        """Test logging a document retrieve operation"""
        # Arrange
        user_id = 1
        document_id = 456
        
        # Act
        log_id = await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.RETRIEVE,
            result="success",
            document_id=document_id
        )
        
        # Assert
        assert log_id is not None
    
    @pytest.mark.asyncio
    async def test_log_delete_operation(self, audit_logger):
        """Test logging a document delete operation"""
        # Arrange
        user_id = 1
        document_id = 789
        
        # Act
        log_id = await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.DELETE,
            result="success",
            document_id=document_id
        )
        
        # Assert
        assert log_id is not None
    
    @pytest.mark.asyncio
    async def test_log_failed_operation(self, audit_logger):
        """Test logging a failed operation"""
        # Arrange
        user_id = 1
        details = {"error": "File too large"}
        
        # Act
        log_id = await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="failure",
            details=details
        )
        
        # Assert
        assert log_id is not None
    
    @pytest.mark.asyncio
    async def test_get_user_logs(self, audit_logger):
        """Test retrieving logs for a specific user"""
        # Arrange
        user_id = 1
        
        # Create multiple log entries
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=1
        )
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.RETRIEVE,
            result="success",
            document_id=1
        )
        
        # Act
        logs = await audit_logger.get_user_logs(user_id=user_id)
        
        # Assert
        assert len(logs) >= 2
        assert all(log.user_id == user_id for log in logs)
    
    @pytest.mark.asyncio
    async def test_get_document_logs(self, audit_logger):
        """Test retrieving logs for a specific document"""
        # Arrange
        user_id = 1
        document_id = 100
        
        # Create log entries for the document
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=document_id
        )
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.RETRIEVE,
            result="success",
            document_id=document_id
        )
        
        # Act
        logs = await audit_logger.get_document_logs(document_id=document_id)
        
        # Assert
        assert len(logs) >= 2
        assert all(log.document_id == document_id for log in logs)
    
    @pytest.mark.asyncio
    async def test_get_logs_by_action(self, audit_logger):
        """Test filtering logs by action type"""
        # Arrange
        user_id = 1
        
        # Create different action types
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=1
        )
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=2
        )
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.DELETE,
            result="success",
            document_id=3
        )
        
        # Act
        upload_logs = await audit_logger.get_logs_by_action(
            user_id=user_id,
            action=AuditAction.UPLOAD
        )
        
        # Assert
        assert len(upload_logs) >= 2
        assert all(log.action == AuditAction.UPLOAD.value for log in upload_logs)
    
    @pytest.mark.asyncio
    async def test_get_logs_by_date_range(self, audit_logger):
        """Test filtering logs by date range"""
        # Arrange
        user_id = 1
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow() + timedelta(hours=1)
        
        # Create log entry
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=1
        )
        
        # Act
        logs = await audit_logger.get_logs_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Assert
        assert len(logs) >= 1
        assert all(start_date <= log.timestamp <= end_date for log in logs)
    
    @pytest.mark.asyncio
    async def test_get_logs_with_filters(self, audit_logger):
        """Test retrieving logs with multiple filters"""
        # Arrange
        user_id = 1
        document_id = 200
        
        # Create log entries
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=document_id
        )
        
        # Act
        filters = AuditLogFilters(
            user_id=user_id,
            document_id=document_id,
            action=AuditAction.UPLOAD,
            result="success"
        )
        logs = await audit_logger.get_logs(filters)
        
        # Assert
        assert len(logs) >= 1
        assert all(
            log.user_id == user_id and
            log.document_id == document_id and
            log.action == AuditAction.UPLOAD.value and
            log.result == "success"
            for log in logs
        )
    
    @pytest.mark.asyncio
    async def test_count_logs(self, audit_logger):
        """Test counting logs with filters"""
        # Arrange
        user_id = 1
        
        # Create multiple log entries
        for i in range(5):
            await audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.UPLOAD,
                result="success",
                document_id=i
            )
        
        # Act
        filters = AuditLogFilters(user_id=user_id, action=AuditAction.UPLOAD)
        count = await audit_logger.count_logs(filters)
        
        # Assert
        assert count >= 5
    
    @pytest.mark.asyncio
    async def test_pagination(self, audit_logger):
        """Test pagination of audit logs"""
        # Arrange
        user_id = 1
        
        # Create multiple log entries
        for i in range(10):
            await audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.UPLOAD,
                result="success",
                document_id=i
            )
        
        # Act - Get first page
        filters_page1 = AuditLogFilters(user_id=user_id, limit=5, offset=0)
        logs_page1 = await audit_logger.get_logs(filters_page1)
        
        # Act - Get second page
        filters_page2 = AuditLogFilters(user_id=user_id, limit=5, offset=5)
        logs_page2 = await audit_logger.get_logs(filters_page2)
        
        # Assert
        assert len(logs_page1) == 5
        assert len(logs_page2) == 5
        assert logs_page1[0].id != logs_page2[0].id
    
    @pytest.mark.asyncio
    async def test_logs_ordered_by_timestamp(self, audit_logger):
        """Test that logs are returned in descending timestamp order"""
        # Arrange
        user_id = 1
        
        # Create log entries
        for i in range(3):
            await audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.UPLOAD,
                result="success",
                document_id=i
            )
        
        # Act
        logs = await audit_logger.get_user_logs(user_id=user_id)
        
        # Assert
        assert len(logs) >= 3
        # Check descending order (most recent first)
        for i in range(len(logs) - 1):
            assert logs[i].timestamp >= logs[i + 1].timestamp
    
    @pytest.mark.asyncio
    async def test_ip_address_and_user_agent_stored(self, audit_logger):
        """Test that IP address and user agent are stored correctly"""
        # Arrange
        user_id = 1
        ip_address = "10.0.0.1"
        user_agent = "TestAgent/1.0"
        
        # Act
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=1,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logs = await audit_logger.get_user_logs(user_id=user_id, limit=1)
        
        # Assert
        assert len(logs) == 1
        assert logs[0].ip_address == ip_address
        assert logs[0].user_agent == user_agent
    
    @pytest.mark.asyncio
    async def test_details_stored_as_json(self, audit_logger):
        """Test that details are stored as JSON string"""
        # Arrange
        user_id = 1
        details = {
            "file_name": "test.pdf",
            "file_size": 2048,
            "category": "identity"
        }
        
        # Act
        await audit_logger.log_operation(
            user_id=user_id,
            action=AuditAction.UPLOAD,
            result="success",
            document_id=1,
            details=details
        )
        
        logs = await audit_logger.get_user_logs(user_id=user_id, limit=1)
        
        # Assert
        assert len(logs) == 1
        assert logs[0].details is not None
        
        # Parse JSON and verify
        import json
        stored_details = json.loads(logs[0].details)
        assert stored_details["file_name"] == "test.pdf"
        assert stored_details["file_size"] == 2048
    
    def test_create_audit_logger_factory(self, db_session):
        """Test the factory function"""
        # Act
        logger = create_audit_logger(db_session)
        
        # Assert
        assert isinstance(logger, AuditLogger)
        assert logger.db == db_session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
