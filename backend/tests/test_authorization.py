"""
Authorization Service Tests

Tests for role-based access control and resource ownership validation.

Validates Requirements 10.1 and 15.1:
- Requirement 10.1: Secure session management with proper access control
- Requirement 15.1: Users can only access their own documents
"""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

from app.services.authorization import (
    AuthorizationService,
    Role,
    Permission,
    ROLE_PERMISSIONS,
    authorization_service
)


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Test models (simplified versions)
class User(Base):
    """User model for testing"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    
    documents = relationship("Document", back_populates="user")
    service_requests = relationship("ServiceRequest", back_populates="user")
    automation_sessions = relationship("AutomationSession", back_populates="user")
    credentials = relationship("Credential", back_populates="user")


class Document(Base):
    """Document model for testing"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    document_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    
    user = relationship("User", back_populates="documents")


class ServiceRequest(Base):
    """Service request model for testing"""
    __tablename__ = "service_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(String, nullable=False)
    status = Column(String, default="submitted")
    
    user = relationship("User", back_populates="service_requests")


class AutomationSession(Base):
    """Automation session model for testing"""
    __tablename__ = "automation_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(String, nullable=False)
    status = Column(String, default="in_progress")
    
    user = relationship("User", back_populates="automation_sessions")


class Credential(Base):
    """Credential model for testing"""
    __tablename__ = "credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    portal_name = Column(String, nullable=False)
    encrypted_username = Column(Text, nullable=False)
    encrypted_password = Column(Text, nullable=False)
    
    user = relationship("User", back_populates="credentials")


@pytest.fixture
def db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db: Session):
    """Create test user"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db: Session):
    """Create another test user"""
    user = User(
        email="other@example.com",
        hashed_password="hashed_password",
        full_name="Other User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_document(db: Session, test_user: User):
    """Create test document"""
    document = Document(
        user_id=test_user.id,
        document_type="aadhaar",
        file_name="aadhaar.pdf"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@pytest.fixture
def test_service_request(db: Session, test_user: User):
    """Create test service request"""
    request = ServiceRequest(
        user_id=test_user.id,
        service_id="aadhaar_name_change",
        status="submitted"
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@pytest.fixture
def test_automation_session(db: Session, test_user: User):
    """Create test automation session"""
    session = AutomationSession(
        user_id=test_user.id,
        service_id="aadhaar_name_change",
        status="in_progress"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_credential(db: Session, test_user: User):
    """Create test credential"""
    credential = Credential(
        user_id=test_user.id,
        portal_name="aadhaar_portal",
        encrypted_username="encrypted_user",
        encrypted_password="encrypted_pass"
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


class TestRolePermissions:
    """Test role and permission system"""
    
    def test_user_role_has_correct_permissions(self):
        """Test that USER role has expected permissions"""
        user_permissions = ROLE_PERMISSIONS[Role.USER]
        
        # User should have own resource permissions
        assert Permission.READ_OWN_DOCUMENTS in user_permissions
        assert Permission.WRITE_OWN_DOCUMENTS in user_permissions
        assert Permission.DELETE_OWN_DOCUMENTS in user_permissions
        assert Permission.READ_OWN_REQUESTS in user_permissions
        assert Permission.START_OWN_AUTOMATION in user_permissions
        
        # User should NOT have admin permissions
        assert Permission.READ_ALL_DOCUMENTS not in user_permissions
        assert Permission.MANAGE_USERS not in user_permissions
        assert Permission.VIEW_AUDIT_LOGS not in user_permissions
    
    def test_admin_role_has_all_permissions(self):
        """Test that ADMIN role has all permissions"""
        admin_permissions = ROLE_PERMISSIONS[Role.ADMIN]
        
        # Admin should have all user permissions
        assert Permission.READ_OWN_DOCUMENTS in admin_permissions
        assert Permission.WRITE_OWN_DOCUMENTS in admin_permissions
        
        # Admin should have admin-only permissions
        assert Permission.READ_ALL_DOCUMENTS in admin_permissions
        assert Permission.READ_ALL_REQUESTS in admin_permissions
        assert Permission.MANAGE_USERS in admin_permissions
        assert Permission.VIEW_AUDIT_LOGS in admin_permissions
    
    def test_get_user_role(self, test_user: User):
        """Test getting user role"""
        auth_service = AuthorizationService()
        role = auth_service.get_user_role(test_user)
        
        # Currently all users are USER role
        assert role == Role.USER
    
    def test_get_role_permissions(self):
        """Test getting permissions for a role"""
        auth_service = AuthorizationService()
        
        user_perms = auth_service.get_role_permissions(Role.USER)
        assert len(user_perms) > 0
        assert Permission.READ_OWN_DOCUMENTS in user_perms
        
        admin_perms = auth_service.get_role_permissions(Role.ADMIN)
        assert len(admin_perms) > len(user_perms)
        assert Permission.MANAGE_USERS in admin_perms


class TestPermissionChecking:
    """Test permission checking"""
    
    def test_user_has_own_resource_permissions(self, test_user: User):
        """Test that user has permissions for own resources"""
        auth_service = AuthorizationService()
        
        assert auth_service.has_permission(test_user, Permission.READ_OWN_DOCUMENTS)
        assert auth_service.has_permission(test_user, Permission.WRITE_OWN_DOCUMENTS)
        assert auth_service.has_permission(test_user, Permission.DELETE_OWN_DOCUMENTS)
        assert auth_service.has_permission(test_user, Permission.START_OWN_AUTOMATION)
    
    def test_user_does_not_have_admin_permissions(self, test_user: User):
        """Test that regular user doesn't have admin permissions"""
        auth_service = AuthorizationService()
        
        assert not auth_service.has_permission(test_user, Permission.READ_ALL_DOCUMENTS)
        assert not auth_service.has_permission(test_user, Permission.MANAGE_USERS)
        assert not auth_service.has_permission(test_user, Permission.VIEW_AUDIT_LOGS)
    
    def test_require_permission_success(self, test_user: User):
        """Test require_permission with valid permission"""
        auth_service = AuthorizationService()
        
        # Should not raise exception
        auth_service.require_permission(test_user, Permission.READ_OWN_DOCUMENTS)
    
    def test_require_permission_failure(self, test_user: User):
        """Test require_permission with invalid permission"""
        auth_service = AuthorizationService()
        
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            auth_service.require_permission(test_user, Permission.MANAGE_USERS)
        
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail


class TestDocumentOwnership:
    """Test document ownership validation (Requirement 15.1)"""
    
    def test_validate_own_document_success(
        self,
        db: Session,
        test_user: User,
        test_document: Document
    ):
        """Test validating access to own document"""
        auth_service = AuthorizationService()
        
        document = auth_service.validate_document_ownership(
            test_user,
            test_document.id,
            db
        )
        
        assert document.id == test_document.id
        assert document.user_id == test_user.id
    
    def test_validate_other_user_document_failure(
        self,
        db: Session,
        other_user: User,
        test_document: Document
    ):
        """Test that user cannot access another user's document"""
        auth_service = AuthorizationService()
        
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_document_ownership(
                other_user,
                test_document.id,
                db
            )
        
        assert exc_info.value.status_code == 403
        assert "You can only access your own documents" in exc_info.value.detail
    
    def test_validate_nonexistent_document(
        self,
        db: Session,
        test_user: User
    ):
        """Test validating nonexistent document"""
        auth_service = AuthorizationService()
        
        # Should raise 404 Not Found
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_document_ownership(
                test_user,
                99999,  # Non-existent ID
                db
            )
        
        assert exc_info.value.status_code == 404
        assert "Document not found" in exc_info.value.detail
    
    def test_filter_user_documents(
        self,
        db: Session,
        test_user: User,
        other_user: User,
        test_document: Document
    ):
        """Test filtering documents by user"""
        # Create document for other user
        other_doc = Document(
            user_id=other_user.id,
            document_type="pan",
            file_name="pan.pdf"
        )
        db.add(other_doc)
        db.commit()
        
        auth_service = AuthorizationService()
        
        # Test user should only see their own document
        user_docs = auth_service.filter_user_documents(test_user, db)
        assert len(user_docs) == 1
        assert user_docs[0].id == test_document.id
        assert user_docs[0].user_id == test_user.id


class TestServiceRequestOwnership:
    """Test service request ownership validation"""
    
    def test_validate_own_request_success(
        self,
        db: Session,
        test_user: User,
        test_service_request: ServiceRequest
    ):
        """Test validating access to own service request"""
        auth_service = AuthorizationService()
        
        request = auth_service.validate_service_request_ownership(
            test_user,
            test_service_request.id,
            db
        )
        
        assert request.id == test_service_request.id
        assert request.user_id == test_user.id
    
    def test_validate_other_user_request_failure(
        self,
        db: Session,
        other_user: User,
        test_service_request: ServiceRequest
    ):
        """Test that user cannot access another user's service request"""
        auth_service = AuthorizationService()
        
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_service_request_ownership(
                other_user,
                test_service_request.id,
                db
            )
        
        assert exc_info.value.status_code == 403
        assert "You can only access your own service requests" in exc_info.value.detail
    
    def test_filter_user_service_requests(
        self,
        db: Session,
        test_user: User,
        other_user: User,
        test_service_request: ServiceRequest
    ):
        """Test filtering service requests by user"""
        # Create request for other user
        other_request = ServiceRequest(
            user_id=other_user.id,
            service_id="pan_correction",
            status="submitted"
        )
        db.add(other_request)
        db.commit()
        
        auth_service = AuthorizationService()
        
        # Test user should only see their own request
        user_requests = auth_service.filter_user_service_requests(test_user, db)
        assert len(user_requests) == 1
        assert user_requests[0].id == test_service_request.id
        assert user_requests[0].user_id == test_user.id


class TestAutomationSessionOwnership:
    """Test automation session ownership validation"""
    
    def test_validate_own_session_success(
        self,
        db: Session,
        test_user: User,
        test_automation_session: AutomationSession
    ):
        """Test validating access to own automation session"""
        auth_service = AuthorizationService()
        
        session = auth_service.validate_automation_session_ownership(
            test_user,
            test_automation_session.id,
            db
        )
        
        assert session.id == test_automation_session.id
        assert session.user_id == test_user.id
    
    def test_validate_other_user_session_failure(
        self,
        db: Session,
        other_user: User,
        test_automation_session: AutomationSession
    ):
        """Test that user cannot access another user's automation session"""
        auth_service = AuthorizationService()
        
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_automation_session_ownership(
                other_user,
                test_automation_session.id,
                db
            )
        
        assert exc_info.value.status_code == 403
        assert "You can only access your own automation sessions" in exc_info.value.detail
    
    def test_filter_user_automation_sessions(
        self,
        db: Session,
        test_user: User,
        other_user: User,
        test_automation_session: AutomationSession
    ):
        """Test filtering automation sessions by user"""
        # Create session for other user
        other_session = AutomationSession(
            user_id=other_user.id,
            service_id="pan_correction",
            status="in_progress"
        )
        db.add(other_session)
        db.commit()
        
        auth_service = AuthorizationService()
        
        # Test user should only see their own session
        user_sessions = auth_service.filter_user_automation_sessions(test_user, db)
        assert len(user_sessions) == 1
        assert user_sessions[0].id == test_automation_session.id
        assert user_sessions[0].user_id == test_user.id


class TestCredentialOwnership:
    """Test credential ownership validation"""
    
    def test_validate_own_credential_success(
        self,
        db: Session,
        test_user: User,
        test_credential: Credential
    ):
        """Test validating access to own credential"""
        auth_service = AuthorizationService()
        
        credential = auth_service.validate_credential_ownership(
            test_user,
            test_credential.id,
            db
        )
        
        assert credential.id == test_credential.id
        assert credential.user_id == test_user.id
    
    def test_validate_other_user_credential_failure(
        self,
        db: Session,
        other_user: User,
        test_credential: Credential
    ):
        """Test that user cannot access another user's credential"""
        auth_service = AuthorizationService()
        
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_credential_ownership(
                other_user,
                test_credential.id,
                db
            )
        
        assert exc_info.value.status_code == 403
        assert "You can only access your own credentials" in exc_info.value.detail
    
    def test_validate_nonexistent_credential(
        self,
        db: Session,
        test_user: User
    ):
        """Test validating nonexistent credential"""
        auth_service = AuthorizationService()
        
        # Should raise 404 Not Found
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_credential_ownership(
                test_user,
                99999,  # Non-existent ID
                db
            )
        
        assert exc_info.value.status_code == 404
        assert "Credential not found" in exc_info.value.detail


class TestAccessControlIntegration:
    """Integration tests for access control (Requirement 10.1)"""
    
    def test_user_isolation(
        self,
        db: Session,
        test_user: User,
        other_user: User
    ):
        """Test that users are properly isolated from each other's resources"""
        # Create resources for both users
        user1_doc = Document(
            user_id=test_user.id,
            document_type="aadhaar",
            file_name="aadhaar.pdf"
        )
        user2_doc = Document(
            user_id=other_user.id,
            document_type="pan",
            file_name="pan.pdf"
        )
        db.add_all([user1_doc, user2_doc])
        db.commit()
        
        auth_service = AuthorizationService()
        
        # User 1 can access their own document
        doc = auth_service.validate_document_ownership(test_user, user1_doc.id, db)
        assert doc.id == user1_doc.id
        
        # User 1 cannot access User 2's document
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_document_ownership(test_user, user2_doc.id, db)
        assert exc_info.value.status_code == 403
        
        # User 2 can access their own document
        doc = auth_service.validate_document_ownership(other_user, user2_doc.id, db)
        assert doc.id == user2_doc.id
        
        # User 2 cannot access User 1's document
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_document_ownership(other_user, user1_doc.id, db)
        assert exc_info.value.status_code == 403
    
    def test_comprehensive_resource_isolation(
        self,
        db: Session,
        test_user: User,
        other_user: User
    ):
        """Test isolation across all resource types"""
        # Create resources for test_user
        doc = Document(user_id=test_user.id, document_type="aadhaar", file_name="test.pdf")
        request = ServiceRequest(user_id=test_user.id, service_id="test_service")
        session = AutomationSession(user_id=test_user.id, service_id="test_service")
        cred = Credential(
            user_id=test_user.id,
            portal_name="test_portal",
            encrypted_username="user",
            encrypted_password="pass"
        )
        db.add_all([doc, request, session, cred])
        db.commit()
        
        auth_service = AuthorizationService()
        
        # Other user cannot access any of test_user's resources
        with pytest.raises(HTTPException):
            auth_service.validate_document_ownership(other_user, doc.id, db)
        
        with pytest.raises(HTTPException):
            auth_service.validate_service_request_ownership(other_user, request.id, db)
        
        with pytest.raises(HTTPException):
            auth_service.validate_automation_session_ownership(other_user, session.id, db)
        
        with pytest.raises(HTTPException):
            auth_service.validate_credential_ownership(other_user, cred.id, db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
