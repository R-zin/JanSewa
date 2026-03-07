"""
Audit Logger Service for Document Operations

This service tracks all document operations for security and compliance purposes.
Audit logs are immutable and stored in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
import logging

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Session
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Document operation types"""
    UPLOAD = "upload"
    RETRIEVE = "retrieve"
    DELETE = "delete"
    UPDATE = "update"
    PREVIEW = "preview"
    SHARE = "share"
    CATEGORIZE = "categorize"
    VERSION_UPLOAD = "version_upload"


# Note: AuditLogEntry model is defined in app/db/models.py to avoid circular imports
# This allows the model to be imported by both the service and the database layer


class AuditLogEntryResponse(BaseModel):
    """Response model for audit log entries"""
    id: int
    timestamp: datetime
    user_id: int
    document_id: Optional[int]
    action: str
    result: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[str]
    
    class Config:
        from_attributes = True


class AuditLogFilters(BaseModel):
    """Filters for querying audit logs"""
    user_id: Optional[int] = None
    document_id: Optional[int] = None
    action: Optional[AuditAction] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    result: Optional[str] = None
    limit: int = 100
    offset: int = 0


class AuditLogger:
    """
    Audit logging service for document operations
    
    Features:
    - Immutable audit logs (append-only)
    - Tracks all document operations
    - Includes user context (IP, user agent)
    - Supports filtering and retrieval
    - Secure storage in PostgreSQL
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def log_operation(
        self,
        user_id: int,
        action: AuditAction,
        result: str,
        document_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create an audit log entry for a document operation
        
        Args:
            user_id: ID of the user performing the operation
            action: Type of operation (upload, retrieve, delete, etc.)
            result: Operation result (success, failure, partial)
            document_id: ID of the document (if applicable)
            ip_address: IP address of the request
            user_agent: User agent string from the request
            details: Additional context as a dictionary
        
        Returns:
            ID of the created audit log entry
        """
        import json
        from app.db.models import AuditLogEntry
        
        try:
            # Create audit log entry
            audit_entry = AuditLogEntry(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                document_id=document_id,
                action=action.value,
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                details=json.dumps(details) if details else None
            )
            
            self.db.add(audit_entry)
            self.db.commit()
            self.db.refresh(audit_entry)
            
            logger.info(
                f"Audit log created: user={user_id}, action={action.value}, "
                f"document={document_id}, result={result}"
            )
            
            return audit_entry.id
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            self.db.rollback()
            raise
    
    async def get_logs(
        self,
        filters: AuditLogFilters
    ) -> List[AuditLogEntryResponse]:
        """
        Retrieve audit logs with filtering
        
        Args:
            filters: Filter criteria for querying logs
        
        Returns:
            List of audit log entries matching the filters
        """
        from app.db.models import AuditLogEntry
        
        try:
            query = self.db.query(AuditLogEntry)
            
            # Apply filters
            if filters.user_id:
                query = query.filter(AuditLogEntry.user_id == filters.user_id)
            
            if filters.document_id:
                query = query.filter(AuditLogEntry.document_id == filters.document_id)
            
            if filters.action:
                query = query.filter(AuditLogEntry.action == filters.action.value)
            
            if filters.start_date:
                query = query.filter(AuditLogEntry.timestamp >= filters.start_date)
            
            if filters.end_date:
                query = query.filter(AuditLogEntry.timestamp <= filters.end_date)
            
            if filters.result:
                query = query.filter(AuditLogEntry.result == filters.result)
            
            # Order by timestamp descending (most recent first)
            query = query.order_by(AuditLogEntry.timestamp.desc())
            
            # Apply pagination
            query = query.limit(filters.limit).offset(filters.offset)
            
            # Execute query
            entries = query.all()
            
            logger.info(f"Retrieved {len(entries)} audit log entries")
            
            return [AuditLogEntryResponse.from_orm(entry) for entry in entries]
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {str(e)}")
            raise
    
    async def get_user_logs(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogEntryResponse]:
        """
        Get all audit logs for a specific user
        
        Args:
            user_id: ID of the user
            limit: Maximum number of entries to return
            offset: Number of entries to skip
        
        Returns:
            List of audit log entries for the user
        """
        filters = AuditLogFilters(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return await self.get_logs(filters)
    
    async def get_document_logs(
        self,
        document_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogEntryResponse]:
        """
        Get all audit logs for a specific document
        
        Args:
            document_id: ID of the document
            limit: Maximum number of entries to return
            offset: Number of entries to skip
        
        Returns:
            List of audit log entries for the document
        """
        filters = AuditLogFilters(
            document_id=document_id,
            limit=limit,
            offset=offset
        )
        return await self.get_logs(filters)
    
    async def get_logs_by_action(
        self,
        user_id: int,
        action: AuditAction,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogEntryResponse]:
        """
        Get audit logs filtered by action type
        
        Args:
            user_id: ID of the user
            action: Type of operation to filter by
            limit: Maximum number of entries to return
            offset: Number of entries to skip
        
        Returns:
            List of audit log entries for the specified action
        """
        filters = AuditLogFilters(
            user_id=user_id,
            action=action,
            limit=limit,
            offset=offset
        )
        return await self.get_logs(filters)
    
    async def get_logs_by_date_range(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogEntryResponse]:
        """
        Get audit logs within a date range
        
        Args:
            user_id: ID of the user
            start_date: Start of the date range
            end_date: End of the date range
            limit: Maximum number of entries to return
            offset: Number of entries to skip
        
        Returns:
            List of audit log entries within the date range
        """
        filters = AuditLogFilters(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return await self.get_logs(filters)
    
    async def count_logs(self, filters: AuditLogFilters) -> int:
        """
        Count audit logs matching the filters
        
        Args:
            filters: Filter criteria for counting logs
        
        Returns:
            Number of audit log entries matching the filters
        """
        from app.db.models import AuditLogEntry
        
        try:
            query = self.db.query(AuditLogEntry)
            
            # Apply filters (same as get_logs)
            if filters.user_id:
                query = query.filter(AuditLogEntry.user_id == filters.user_id)
            
            if filters.document_id:
                query = query.filter(AuditLogEntry.document_id == filters.document_id)
            
            if filters.action:
                query = query.filter(AuditLogEntry.action == filters.action.value)
            
            if filters.start_date:
                query = query.filter(AuditLogEntry.timestamp >= filters.start_date)
            
            if filters.end_date:
                query = query.filter(AuditLogEntry.timestamp <= filters.end_date)
            
            if filters.result:
                query = query.filter(AuditLogEntry.result == filters.result)
            
            count = query.count()
            
            logger.info(f"Counted {count} audit log entries")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to count audit logs: {str(e)}")
            raise


def create_audit_logger(db_session: Session) -> AuditLogger:
    """
    Factory function to create an AuditLogger instance
    
    Args:
        db_session: SQLAlchemy database session
    
    Returns:
        Configured AuditLogger instance
    """
    return AuditLogger(db_session)
