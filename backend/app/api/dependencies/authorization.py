"""
Authorization Dependencies

FastAPI dependencies for authorization checks and resource validation.
Used to protect API endpoints and ensure users can only access their own resources.

Validates Requirements 10.1 and 15.1
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Callable

from app.db.models import User, Document, ServiceRequest, AutomationSession, Credential
from app.db.base import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.services.authorization import authorization_service, Permission


def require_permission(permission: Permission):
    """
    Dependency factory to require a specific permission
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function that checks permission
        
    Example:
        @router.get("/admin/users")
        async def list_users(
            current_user: User = Depends(require_permission(Permission.MANAGE_USERS))
        ):
            ...
    """
    def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if user has required permission"""
        authorization_service.require_permission(current_user, permission)
        return current_user
    
    return permission_checker


def get_user_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Document:
    """
    Dependency to get and validate document ownership
    
    Args:
        document_id: Document ID from path parameter
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Document object if user has access
        
    Raises:
        HTTPException: If document not found or access denied
        
    Example:
        @router.get("/documents/{document_id}")
        async def get_document(
            document: Document = Depends(get_user_document)
        ):
            return document
    """
    return authorization_service.validate_document_ownership(
        current_user,
        document_id,
        db
    )


def get_user_service_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ServiceRequest:
    """
    Dependency to get and validate service request ownership
    
    Args:
        request_id: Service request ID from path parameter
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ServiceRequest object if user has access
        
    Raises:
        HTTPException: If request not found or access denied
        
    Example:
        @router.get("/service-requests/{request_id}")
        async def get_request(
            service_request: ServiceRequest = Depends(get_user_service_request)
        ):
            return service_request
    """
    return authorization_service.validate_service_request_ownership(
        current_user,
        request_id,
        db
    )


def get_user_automation_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AutomationSession:
    """
    Dependency to get and validate automation session ownership
    
    Args:
        session_id: Automation session ID from path parameter
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        AutomationSession object if user has access
        
    Raises:
        HTTPException: If session not found or access denied
        
    Example:
        @router.get("/automation/{session_id}")
        async def get_session(
            automation_session: AutomationSession = Depends(get_user_automation_session)
        ):
            return automation_session
    """
    return authorization_service.validate_automation_session_ownership(
        current_user,
        session_id,
        db
    )


def get_user_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Credential:
    """
    Dependency to get and validate credential ownership
    
    Args:
        credential_id: Credential ID from path parameter
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Credential object if user has access
        
    Raises:
        HTTPException: If credential not found or access denied
        
    Example:
        @router.get("/credentials/{credential_id}")
        async def get_credential(
            credential: Credential = Depends(get_user_credential)
        ):
            return credential
    """
    return authorization_service.validate_credential_ownership(
        current_user,
        credential_id,
        db
    )


# Permission-based dependencies for common use cases
require_read_own_documents = require_permission(Permission.READ_OWN_DOCUMENTS)
require_write_own_documents = require_permission(Permission.WRITE_OWN_DOCUMENTS)
require_delete_own_documents = require_permission(Permission.DELETE_OWN_DOCUMENTS)

require_read_own_requests = require_permission(Permission.READ_OWN_REQUESTS)
require_write_own_requests = require_permission(Permission.WRITE_OWN_REQUESTS)

require_start_own_automation = require_permission(Permission.START_OWN_AUTOMATION)
require_control_own_automation = require_permission(Permission.CONTROL_OWN_AUTOMATION)

require_manage_users = require_permission(Permission.MANAGE_USERS)
require_view_audit_logs = require_permission(Permission.VIEW_AUDIT_LOGS)
