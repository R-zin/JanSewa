"""
API endpoints for audit log access
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.audit_logger import (
    AuditLogger,
    AuditLogEntryResponse,
    AuditLogFilters,
    AuditAction,
    create_audit_logger
)

router = APIRouter()


def get_audit_logger(db: Session = Depends(get_db)) -> AuditLogger:
    """Dependency to get AuditLogger instance"""
    return create_audit_logger(db)


@router.get("/logs", response_model=List[AuditLogEntryResponse])
async def get_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    result: Optional[str] = Query(None, description="Filter by result (success/failure)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Retrieve audit logs with optional filtering
    
    This endpoint allows querying audit logs by various criteria:
    - User ID
    - Document ID
    - Action type (upload, retrieve, delete, etc.)
    - Date range
    - Operation result
    
    Results are paginated and ordered by timestamp (most recent first).
    """
    try:
        filters = AuditLogFilters(
            user_id=user_id,
            document_id=document_id,
            action=action,
            start_date=start_date,
            end_date=end_date,
            result=result,
            limit=limit,
            offset=offset
        )
        
        logs = await audit_logger.get_logs(filters)
        return logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")


@router.get("/logs/user/{user_id}", response_model=List[AuditLogEntryResponse])
async def get_user_audit_logs(
    user_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get all audit logs for a specific user
    
    Returns all document operations performed by the specified user,
    ordered by timestamp (most recent first).
    """
    try:
        logs = await audit_logger.get_user_logs(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user logs: {str(e)}")


@router.get("/logs/document/{document_id}", response_model=List[AuditLogEntryResponse])
async def get_document_audit_logs(
    document_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get all audit logs for a specific document
    
    Returns all operations performed on the specified document,
    ordered by timestamp (most recent first).
    """
    try:
        logs = await audit_logger.get_document_logs(
            document_id=document_id,
            limit=limit,
            offset=offset
        )
        return logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document logs: {str(e)}")


@router.get("/logs/action/{action}", response_model=List[AuditLogEntryResponse])
async def get_logs_by_action(
    action: AuditAction,
    user_id: int = Query(..., description="User ID is required"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get audit logs filtered by action type
    
    Returns all operations of the specified type (upload, retrieve, delete, etc.)
    for a given user, ordered by timestamp (most recent first).
    """
    try:
        logs = await audit_logger.get_logs_by_action(
            user_id=user_id,
            action=action,
            limit=limit,
            offset=offset
        )
        return logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs by action: {str(e)}")


@router.get("/logs/count")
async def count_audit_logs(
    user_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    action: Optional[AuditAction] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    result: Optional[str] = Query(None),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Count audit logs matching the specified filters
    
    Returns the total number of audit log entries that match the given criteria.
    Useful for pagination and statistics.
    """
    try:
        filters = AuditLogFilters(
            user_id=user_id,
            document_id=document_id,
            action=action,
            start_date=start_date,
            end_date=end_date,
            result=result
        )
        
        count = await audit_logger.count_logs(filters)
        return {"count": count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to count audit logs: {str(e)}")


@router.get("/logs/date-range", response_model=List[AuditLogEntryResponse])
async def get_logs_by_date_range(
    user_id: int = Query(..., description="User ID is required"),
    start_date: datetime = Query(..., description="Start date (inclusive)"),
    end_date: datetime = Query(..., description="End date (inclusive)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get audit logs within a specific date range
    
    Returns all operations performed by the user within the specified date range,
    ordered by timestamp (most recent first).
    """
    try:
        logs = await audit_logger.get_logs_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs by date range: {str(e)}")
