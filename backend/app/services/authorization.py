"""
Authorization Service

Provides role-based access control (RBAC) and resource ownership validation.
Implements authorization checks for API endpoints and resources.

Validates Requirements 10.1 and 15.1:
- Requirement 10.1: Secure session management with proper access control
- Requirement 15.1: Users can only access their own documents
"""

from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

# Use TYPE_CHECKING to avoid circular imports and database connection on import
if TYPE_CHECKING:
    from app.db.models import User, Document, ServiceRequest, AutomationSession, Credential


class Role(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    USER = "user"


class Permission(str, Enum):
    """System permissions"""
    # Document permissions
    READ_OWN_DOCUMENTS = "read_own_documents"
    WRITE_OWN_DOCUMENTS = "write_own_documents"
    DELETE_OWN_DOCUMENTS = "delete_own_documents"
    READ_ALL_DOCUMENTS = "read_all_documents"
    
    # Service request permissions
    READ_OWN_REQUESTS = "read_own_requests"
    WRITE_OWN_REQUESTS = "write_own_requests"
    READ_ALL_REQUESTS = "read_all_requests"
    
    # Session permissions
    READ_OWN_SESSIONS = "read_own_sessions"
    WRITE_OWN_SESSIONS = "write_own_sessions"
    READ_ALL_SESSIONS = "read_all_sessions"
    
    # Credential permissions
    READ_OWN_CREDENTIALS = "read_own_credentials"
    WRITE_OWN_CREDENTIALS = "write_own_credentials"
    DELETE_OWN_CREDENTIALS = "delete_own_credentials"
    
    # Automation permissions
    START_OWN_AUTOMATION = "start_own_automation"
    READ_OWN_AUTOMATION = "read_own_automation"
    CONTROL_OWN_AUTOMATION = "control_own_automation"
    READ_ALL_AUTOMATION = "read_all_automation"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SYSTEM = "manage_system"


# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.USER: [
        # Document permissions
        Permission.READ_OWN_DOCUMENTS,
        Permission.WRITE_OWN_DOCUMENTS,
        Permission.DELETE_OWN_DOCUMENTS,
        
        # Service request permissions
        Permission.READ_OWN_REQUESTS,
        Permission.WRITE_OWN_REQUESTS,
        
        # Session permissions
        Permission.READ_OWN_SESSIONS,
        Permission.WRITE_OWN_SESSIONS,
        
        # Credential permissions
        Permission.READ_OWN_CREDENTIALS,
        Permission.WRITE_OWN_CREDENTIALS,
        Permission.DELETE_OWN_CREDENTIALS,
        
        # Automation permissions
        Permission.START_OWN_AUTOMATION,
        Permission.READ_OWN_AUTOMATION,
        Permission.CONTROL_OWN_AUTOMATION,
    ],
    Role.ADMIN: [
        # All user permissions
        Permission.READ_OWN_DOCUMENTS,
        Permission.WRITE_OWN_DOCUMENTS,
        Permission.DELETE_OWN_DOCUMENTS,
        Permission.READ_OWN_REQUESTS,
        Permission.WRITE_OWN_REQUESTS,
        Permission.READ_OWN_SESSIONS,
        Permission.WRITE_OWN_SESSIONS,
        Permission.READ_OWN_CREDENTIALS,
        Permission.WRITE_OWN_CREDENTIALS,
        Permission.DELETE_OWN_CREDENTIALS,
        Permission.START_OWN_AUTOMATION,
        Permission.READ_OWN_AUTOMATION,
        Permission.CONTROL_OWN_AUTOMATION,
        
        # Admin-only permissions
        Permission.READ_ALL_DOCUMENTS,
        Permission.READ_ALL_REQUESTS,
        Permission.READ_ALL_SESSIONS,
        Permission.READ_ALL_AUTOMATION,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_SYSTEM,
    ]
}


class AuthorizationService:
    """
    Service for handling authorization and access control
    
    Provides:
    - Role-based access control (RBAC)
    - Resource ownership validation
    - Permission checking
    """
    
    def __init__(self):
        """Initialize authorization service"""
        pass
    
    def get_user_role(self, user: "User") -> Role:
        """
        Get user's role
        
        Args:
            user: User object
            
        Returns:
            User's role (defaults to USER if not set)
        """
        # For now, all users are regular users
        # In production, this would check a role field on the user model
        # Example: return Role(user.role) if hasattr(user, 'role') else Role.USER
        return Role.USER
    
    def get_role_permissions(self, role: Role) -> List[Permission]:
        """
        Get permissions for a role
        
        Args:
            role: User role
            
        Returns:
            List of permissions for the role
        """
        return ROLE_PERMISSIONS.get(role, [])
    
    def has_permission(self, user: "User", permission: Permission) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user: User object
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        user_role = self.get_user_role(user)
        role_permissions = self.get_role_permissions(user_role)
        return permission in role_permissions
    
    def require_permission(self, user: "User", permission: Permission) -> None:
        """
        Require user to have a specific permission
        
        Args:
            user: User object
            permission: Required permission
            
        Raises:
            HTTPException: If user doesn't have permission (403 Forbidden)
        """
        if not self.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
    
    def validate_document_ownership(
        self,
        user: "User",
        document_id: int,
        db: Session
    ) -> "Document":
        """
        Validate that user owns the document
        
        Args:
            user: User object
            document_id: Document ID to check
            db: Database session
            
        Returns:
            Document object if user owns it
            
        Raises:
            HTTPException: If document not found (404) or access denied (403)
        """
        from app.db.models import Document
        
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if user owns the document or has admin permission
        if document.user_id != user.id:
            if not self.has_permission(user, Permission.READ_ALL_DOCUMENTS):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only access your own documents"
                )
        
        return document
    
    def validate_service_request_ownership(
        self,
        user: "User",
        request_id: int,
        db: Session
    ) -> "ServiceRequest":
        """
        Validate that user owns the service request
        
        Args:
            user: User object
            request_id: Service request ID to check
            db: Database session
            
        Returns:
            ServiceRequest object if user owns it
            
        Raises:
            HTTPException: If request not found (404) or access denied (403)
        """
        from app.db.models import ServiceRequest
        
        service_request = db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id
        ).first()
        
        if not service_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service request not found"
            )
        
        # Check if user owns the request or has admin permission
        if service_request.user_id != user.id:
            if not self.has_permission(user, Permission.READ_ALL_REQUESTS):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only access your own service requests"
                )
        
        return service_request
    
    def validate_automation_session_ownership(
        self,
        user: "User",
        session_id: int,
        db: Session
    ) -> "AutomationSession":
        """
        Validate that user owns the automation session
        
        Args:
            user: User object
            session_id: Automation session ID to check
            db: Database session
            
        Returns:
            AutomationSession object if user owns it
            
        Raises:
            HTTPException: If session not found (404) or access denied (403)
        """
        from app.db.models import AutomationSession
        
        automation_session = db.query(AutomationSession).filter(
            AutomationSession.id == session_id
        ).first()
        
        if not automation_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation session not found"
            )
        
        # Check if user owns the session or has admin permission
        if automation_session.user_id != user.id:
            if not self.has_permission(user, Permission.READ_ALL_AUTOMATION):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only access your own automation sessions"
                )
        
        return automation_session
    
    def validate_credential_ownership(
        self,
        user: "User",
        credential_id: int,
        db: Session
    ) -> "Credential":
        """
        Validate that user owns the credential
        
        Args:
            user: User object
            credential_id: Credential ID to check
            db: Database session
            
        Returns:
            Credential object if user owns it
            
        Raises:
            HTTPException: If credential not found (404) or access denied (403)
        """
        from app.db.models import Credential
        
        credential = db.query(Credential).filter(
            Credential.id == credential_id
        ).first()
        
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found"
            )
        
        # Check if user owns the credential
        if credential.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own credentials"
            )
        
        return credential
    
    def filter_user_documents(
        self,
        user: "User",
        db: Session
    ) -> List:
        """
        Get documents accessible to user
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            List of documents user can access
        """
        from app.db.models import Document
        
        # Admin can see all documents
        if self.has_permission(user, Permission.READ_ALL_DOCUMENTS):
            return db.query(Document).all()
        
        # Regular users see only their own documents
        return db.query(Document).filter(Document.user_id == user.id).all()
    
    def filter_user_service_requests(
        self,
        user: "User",
        db: Session
    ) -> List:
        """
        Get service requests accessible to user
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            List of service requests user can access
        """
        from app.db.models import ServiceRequest
        
        # Admin can see all requests
        if self.has_permission(user, Permission.READ_ALL_REQUESTS):
            return db.query(ServiceRequest).all()
        
        # Regular users see only their own requests
        return db.query(ServiceRequest).filter(
            ServiceRequest.user_id == user.id
        ).all()
    
    def filter_user_automation_sessions(
        self,
        user: "User",
        db: Session
    ) -> List:
        """
        Get automation sessions accessible to user
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            List of automation sessions user can access
        """
        from app.db.models import AutomationSession
        
        # Admin can see all sessions
        if self.has_permission(user, Permission.READ_ALL_AUTOMATION):
            return db.query(AutomationSession).all()
        
        # Regular users see only their own sessions
        return db.query(AutomationSession).filter(
            AutomationSession.user_id == user.id
        ).all()


# Global authorization service instance
authorization_service = AuthorizationService()
