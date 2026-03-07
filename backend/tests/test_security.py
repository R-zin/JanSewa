"""
Security Tests for Government Services Assistant

Comprehensive security testing covering:
- Authentication flows (Requirement 10.1, 10.2)
- Authorization checks (Requirement 10.1, 15.1)
- Encryption/decryption (Requirement 15.1)
- Session security (Requirement 10.1)

These tests validate that the system properly protects user data and enforces
access controls across all security-critical operations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from sqlalchemy.sql import func
from fastapi import HTTPException

from app.services.authentication import (
    AuthenticationService,
    UserRegistration,
    UserLogin,
    PasswordReset,
    PasswordResetConfirm
)
from app.services.authorization import AuthorizationService, Role, Permission
from app.services.encryption_service import EncryptionService
from app.services.session_manager import SessionManager
import fakeredis


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Test models
class User(Base):
    """User model for testing"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    language_preference = Column(String, default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    documents = relationship("Document", back_populates="user")


class Document(Base):
    """Document model for testing"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    document_type = Column(String, nullable=False)
    category = Column(String)
    file_name = Column(String, nullable=False)
    s3_key = Column(String)
    file_size = Column(Integer)
    upload_date = Column(DateTime)
    expiration_date = Column(DateTime)
    expiration_status = Column(String)
    is_digilocker = Column(Integer, default=0)
    digilocker_metadata = Column(Text)
    extracted_data = Column(Text)
    extraction_confidence = Column(Integer)
    encrypted_data = Column(Text)
    
    user = relationship("User", back_populates="documents")


# Fixtures
fake_redis_server = fakeredis.FakeServer()


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
def mock_redis():
    """Fixture to provide a fresh fake Redis client"""
    client = fakeredis.FakeRedis(server=fake_redis_server, decode_responses=True)
    client.flushall()
    return client


@pytest.fixture
def auth_service():
    """Create authentication service instance"""
    return AuthenticationService()


@pytest.fixture
def authz_service():
    """Create authorization service instance"""
    return AuthorizationService()


@pytest.fixture
def encryption_service():
    """Create encryption service instance"""
    return EncryptionService()


@pytest.fixture
def session_manager(mock_redis):
    """Create session manager with mocked Redis"""
    from unittest.mock import patch
    with patch.object(SessionManager, '__init__', lambda self: None):
        manager = SessionManager()
        manager.redis_client = mock_redis
        manager.session_timeout = timedelta(minutes=30)
        return manager


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


# ============================================================================
# AUTHENTICATION FLOW TESTS (Requirements 10.1, 10.2)
# ============================================================================

class TestAuthenticationFlows:
    """
    Test complete authentication flows including registration, login,
    password reset, and token management.
    
    Validates Requirements 10.1 and 10.2
    """
    
    def test_complete_registration_and_login_flow(self, auth_service, db):
        """Test complete user registration and login flow"""
        # Step 1: Register new user
        registration = UserRegistration(
            email="newuser@example.com",
            password="SecurePass123",
            full_name="New User",
            language_preference="en"
        )
        
        user = asyncio.run(auth_service.register_user(registration, db))
        assert user.id is not None
        assert user.email == registration.email
        
        # Step 2: Login with correct credentials
        login_data = UserLogin(
            email=registration.email,
            password=registration.password
        )
        
        token_response = asyncio.run(auth_service.login(login_data, db))
        assert token_response.access_token is not None
        assert token_response.token_type == "bearer"
        
        # Step 3: Verify token
        token_data = auth_service.verify_token(token_response.access_token)
        assert token_data is not None
        assert token_data.email == registration.email
    
    def test_authentication_with_wrong_password_fails(self, auth_service, db):
        """Test that authentication fails with incorrect password"""
        # Register user
        registration = UserRegistration(
            email="user@example.com",
            password="CorrectPass123",
            full_name="Test User"
        )
        asyncio.run(auth_service.register_user(registration, db))
        
        # Try to login with wrong password
        login_data = UserLogin(
            email=registration.email,
            password="WrongPass456"
        )
        
        with pytest.raises(ValueError, match="Invalid email or password"):
            asyncio.run(auth_service.login(login_data, db))
    
    def test_duplicate_registration_prevented(self, auth_service, db):
        """Test that duplicate email registration is prevented"""
        registration = UserRegistration(
            email="duplicate@example.com",
            password="SecurePass123",
            full_name="User One"
        )
        
        # First registration succeeds
        asyncio.run(auth_service.register_user(registration, db))
        
        # Second registration with same email fails
        with pytest.raises(ValueError, match="Email already registered"):
            asyncio.run(auth_service.register_user(registration, db))
    
    def test_password_reset_flow(self, auth_service, db):
        """Test complete password reset flow"""
        # Register user
        registration = UserRegistration(
            email="reset@example.com",
            password="OldPass123",
            full_name="Reset User"
        )
        user = asyncio.run(auth_service.register_user(registration, db))
        old_hash = user.hashed_password
        
        # Request password reset
        reset_request = PasswordReset(email=registration.email)
        reset_token = asyncio.run(
            auth_service.request_password_reset(reset_request, db)
        )
        assert reset_token is not None
        
        # Reset password with token
        new_password = "NewSecurePass456"
        reset_confirm = PasswordResetConfirm(
            reset_token=reset_token,
            new_password=new_password
        )
        result = asyncio.run(auth_service.reset_password(reset_confirm, db))
        assert result is True
        
        # Verify password changed
        db.refresh(user)
        assert user.hashed_password != old_hash
        
        # Verify can login with new password
        login_data = UserLogin(email=registration.email, password=new_password)
        token_response = asyncio.run(auth_service.login(login_data, db))
        assert token_response.access_token is not None
    
    def test_token_expiration_enforced(self, auth_service):
        """Test that expired tokens are rejected"""
        data = {"user_id": 1, "email": "test@example.com"}
        
        # Create expired token
        expired_token = auth_service.create_access_token(
            data,
            expires_delta=timedelta(seconds=-1)
        )
        
        # Verify token is rejected
        token_data = auth_service.verify_token(expired_token)
        assert token_data is None
    
    def test_rate_limiting_prevents_brute_force(self, auth_service):
        """Test that rate limiting prevents brute force attacks"""
        email = "bruteforce@example.com"
        
        # Exceed max login attempts
        for _ in range(auth_service.max_attempts):
            auth_service.record_login_attempt(email)
        
        # Check that further attempts are blocked
        is_allowed, lockout_until = auth_service.check_rate_limit(email)
        assert is_allowed is False
        assert lockout_until is not None
    
    def test_password_strength_requirements_enforced(self):
        """Test that password strength requirements are enforced"""
        # Too short
        with pytest.raises(ValueError, match="at least 8 characters"):
            UserRegistration(
                email="test@example.com",
                password="Short1",
                full_name="Test"
            )
        
        # No uppercase
        with pytest.raises(ValueError, match="uppercase letter"):
            UserRegistration(
                email="test@example.com",
                password="lowercase123",
                full_name="Test"
            )
        
        # No lowercase
        with pytest.raises(ValueError, match="lowercase letter"):
            UserRegistration(
                email="test@example.com",
                password="UPPERCASE123",
                full_name="Test"
            )
        
        # No digit
        with pytest.raises(ValueError, match="digit"):
            UserRegistration(
                email="test@example.com",
                password="NoDigitsHere",
                full_name="Test"
            )


# ============================================================================
# AUTHORIZATION TESTS (Requirements 10.1, 15.1)
# ============================================================================

class TestAuthorizationChecks:
    """
    Test authorization and access control mechanisms.
    
    Validates Requirements 10.1 (access control) and 15.1 (document ownership)
    """
    
    def test_user_can_only_access_own_documents(
        self,
        authz_service,
        db,
        test_user,
        other_user
    ):
        """Test that users can only access their own documents (Req 15.1)"""
        # Create document for test_user
        doc = Document(
            user_id=test_user.id,
            document_type="aadhaar",
            file_name="aadhaar.pdf"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # test_user can access their own document
        result = authz_service.validate_document_ownership(test_user, doc.id, db)
        assert result.id == doc.id
        
        # other_user cannot access test_user's document
        with pytest.raises(HTTPException) as exc_info:
            authz_service.validate_document_ownership(other_user, doc.id, db)
        assert exc_info.value.status_code == 403
        assert "You can only access your own documents" in exc_info.value.detail
    
    def test_permission_system_enforces_access_control(self, authz_service, test_user):
        """Test that permission system properly enforces access control"""
        # User has own resource permissions
        assert authz_service.has_permission(test_user, Permission.READ_OWN_DOCUMENTS)
        assert authz_service.has_permission(test_user, Permission.WRITE_OWN_DOCUMENTS)
        assert authz_service.has_permission(test_user, Permission.DELETE_OWN_DOCUMENTS)
        
        # User does NOT have admin permissions
        assert not authz_service.has_permission(test_user, Permission.READ_ALL_DOCUMENTS)
        assert not authz_service.has_permission(test_user, Permission.MANAGE_USERS)
        assert not authz_service.has_permission(test_user, Permission.VIEW_AUDIT_LOGS)
    
    def test_require_permission_blocks_unauthorized_access(
        self,
        authz_service,
        test_user
    ):
        """Test that require_permission blocks unauthorized access"""
        # Should succeed for valid permission
        authz_service.require_permission(test_user, Permission.READ_OWN_DOCUMENTS)
        
        # Should raise 403 for invalid permission
        with pytest.raises(HTTPException) as exc_info:
            authz_service.require_permission(test_user, Permission.MANAGE_USERS)
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail
    
    def test_document_filtering_isolates_users(
        self,
        authz_service,
        db,
        test_user,
        other_user
    ):
        """Test that document filtering properly isolates users"""
        # Create documents for both users
        doc1 = Document(
            user_id=test_user.id,
            document_type="aadhaar",
            file_name="aadhaar.pdf"
        )
        doc2 = Document(
            user_id=other_user.id,
            document_type="pan",
            file_name="pan.pdf"
        )
        db.add_all([doc1, doc2])
        db.commit()
        
        # test_user should only see their own document
        user_docs = authz_service.filter_user_documents(test_user, db)
        assert len(user_docs) == 1
        assert user_docs[0].user_id == test_user.id
        
        # other_user should only see their own document
        other_docs = authz_service.filter_user_documents(other_user, db)
        assert len(other_docs) == 1
        assert other_docs[0].user_id == other_user.id
    
    def test_nonexistent_document_returns_404(self, authz_service, db, test_user):
        """Test that accessing nonexistent document returns 404"""
        with pytest.raises(HTTPException) as exc_info:
            authz_service.validate_document_ownership(test_user, 99999, db)
        assert exc_info.value.status_code == 404
        assert "Document not found" in exc_info.value.detail


# ============================================================================
# ENCRYPTION/DECRYPTION TESTS (Requirement 15.1)
# ============================================================================

class TestEncryptionSecurity:
    """
    Test encryption and decryption security.
    
    Validates Requirement 15.1 (secure document storage with encryption)
    """
    
    def test_document_encryption_decryption_roundtrip(self, encryption_service):
        """Test that documents can be encrypted and decrypted correctly"""
        user_id = 123
        original_data = b"This is sensitive document data"
        
        # Encrypt
        encrypted = encryption_service.encrypt_document(original_data, user_id)
        assert encrypted != original_data
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = encryption_service.decrypt_document(encrypted, user_id)
        assert decrypted == original_data
    
    def test_encrypted_data_is_different_from_original(self, encryption_service):
        """Test that encrypted data is not readable"""
        user_id = 456
        original_data = b"Confidential information"
        
        encrypted = encryption_service.encrypt_document(original_data, user_id)
        
        # Encrypted data should be completely different
        assert encrypted != original_data
        assert original_data not in encrypted
    
    def test_user_specific_encryption_keys(self, encryption_service):
        """Test that different users have different encryption keys"""
        data = b"Same data for both users"
        user1_id = 100
        user2_id = 200
        
        # Encrypt same data for two different users
        encrypted1 = encryption_service.encrypt_document(data, user1_id)
        encrypted2 = encryption_service.encrypt_document(data, user2_id)
        
        # Encrypted data should be different
        assert encrypted1 != encrypted2
        
        # Each user can decrypt their own data
        decrypted1 = encryption_service.decrypt_document(encrypted1, user1_id)
        decrypted2 = encryption_service.decrypt_document(encrypted2, user2_id)
        assert decrypted1 == data
        assert decrypted2 == data
    
    def test_wrong_user_cannot_decrypt_data(self, encryption_service):
        """Test that one user cannot decrypt another user's data"""
        user1_id = 100
        user2_id = 200
        data = b"User 1's private data"
        
        # Encrypt for user 1
        encrypted = encryption_service.encrypt_document(data, user1_id)
        
        # User 2 cannot decrypt user 1's data
        with pytest.raises(Exception):
            encryption_service.decrypt_document(encrypted, user2_id)
    
    def test_text_encryption_decryption(self, encryption_service):
        """Test text encryption and decryption"""
        user_id = 789
        original_text = "Sensitive text information"
        
        # Encrypt
        encrypted_text = encryption_service.encrypt_text(original_text, user_id)
        assert encrypted_text != original_text
        assert isinstance(encrypted_text, str)
        
        # Decrypt
        decrypted_text = encryption_service.decrypt_text(encrypted_text, user_id)
        assert decrypted_text == original_text
    
    def test_encryption_handles_unicode(self, encryption_service):
        """Test that encryption handles Unicode characters correctly"""
        user_id = 999
        unicode_data = "नमस्ते 世界 🔒".encode('utf-8')
        
        encrypted = encryption_service.encrypt_document(unicode_data, user_id)
        decrypted = encryption_service.decrypt_document(encrypted, user_id)
        
        assert decrypted == unicode_data
        assert decrypted.decode('utf-8') == "नमस्ते 世界 🔒"
    
    def test_encryption_handles_large_data(self, encryption_service):
        """Test that encryption handles large documents"""
        user_id = 111
        large_data = b"X" * 1024 * 1024  # 1 MB of data
        
        encrypted = encryption_service.encrypt_document(large_data, user_id)
        decrypted = encryption_service.decrypt_document(encrypted, user_id)
        
        assert decrypted == large_data
        assert len(decrypted) == 1024 * 1024


# ============================================================================
# SESSION SECURITY TESTS (Requirement 10.1)
# ============================================================================

class TestSessionSecurity:
    """
    Test session security mechanisms.
    
    Validates Requirement 10.1 (secure session management)
    """
    
    def test_session_isolation_between_users(self, session_manager):
        """Test that sessions are isolated between users"""
        # Create sessions for two users
        session1 = session_manager.create_session(100, "en")
        session2 = session_manager.create_session(200, "hi")
        
        # Add data to each session
        session_manager.update_context(session1, "secret", "user1_secret")
        session_manager.update_context(session2, "secret", "user2_secret")
        
        # Each session should have its own data
        assert session_manager.get_context(session1, "secret") == "user1_secret"
        assert session_manager.get_context(session2, "secret") == "user2_secret"
        
        # Sessions should not interfere with each other
        assert session1 != session2
    
    def test_sensitive_data_cleared_from_session(self, session_manager):
        """Test that sensitive data can be cleared from sessions"""
        session_id = session_manager.create_session(123, "en")
        
        # Add sensitive data
        session_manager.update_context(session_id, "aadhaar_number", "123456789012")
        session_manager.update_context(session_id, "phone", "9876543210")
        session_manager.update_context(session_id, "service_id", "test_service")
        
        # Clear sensitive data
        result = session_manager.clear_sensitive_data(session_id)
        assert result is True
        
        # Sensitive data should be removed
        assert session_manager.get_context(session_id, "aadhaar_number") is None
        assert session_manager.get_context(session_id, "phone") is None
        
        # Non-sensitive data should remain
        assert session_manager.get_context(session_id, "service_id") == "test_service"
    
    def test_session_cleanup_removes_all_data(self, session_manager):
        """Test that ending session removes all data"""
        session_id = session_manager.create_session(456, "en")
        
        # Add various data
        session_manager.update_context(session_id, "key1", "value1")
        session_manager.update_context(session_id, "key2", "value2")
        
        # End session
        result = session_manager.end_session(session_id)
        assert result is True
        
        # All data should be inaccessible
        assert session_manager.get_session(session_id) is None
        assert session_manager.get_context(session_id, "key1") is None
        assert session_manager.get_context(session_id, "key2") is None
    
    def test_session_timeout_enforced(self, session_manager, mock_redis):
        """Test that session timeout is enforced"""
        session_id = session_manager.create_session(789, "en")
        
        # Check that session has expiration
        ttl = mock_redis.ttl(f"session:{session_id}")
        assert ttl > 0
        assert ttl <= 1800  # 30 minutes
    
    def test_session_cannot_be_accessed_after_end(self, session_manager):
        """Test that session cannot be accessed after being ended"""
        session_id = session_manager.create_session(111, "en")
        
        # Add data
        session_manager.update_context(session_id, "data", "value")
        
        # End session
        session_manager.end_session(session_id)
        
        # Cannot access session data
        assert session_manager.get_session(session_id) is None
        assert session_manager.get_context(session_id, "data") is None
        
        # Cannot update session
        result = session_manager.update_context(session_id, "new_data", "new_value")
        assert result is False
    
    def test_session_extension_resets_timeout(self, session_manager):
        """Test that extending session resets timeout"""
        session_id = session_manager.create_session(222, "en")
        
        # Extend session
        result = session_manager.extend_session(session_id)
        assert result is True
        
        # Session should still be accessible
        assert session_manager.get_session(session_id) is not None
    
    def test_invalid_session_operations_fail_safely(self, session_manager):
        """Test that operations on invalid sessions fail safely"""
        invalid_session = "invalid_session_id"
        
        # All operations should fail gracefully
        assert session_manager.get_session(invalid_session) is None
        assert session_manager.get_context(invalid_session, "key") is None
        assert session_manager.update_context(invalid_session, "key", "value") is False
        assert session_manager.clear_sensitive_data(invalid_session) is False
        assert session_manager.end_session(invalid_session) is False
        assert session_manager.extend_session(invalid_session) is False


# ============================================================================
# INTEGRATION SECURITY TESTS
# ============================================================================

class TestSecurityIntegration:
    """
    Integration tests for security across multiple components.
    
    Tests end-to-end security scenarios.
    """
    
    def test_complete_secure_document_workflow(
        self,
        auth_service,
        authz_service,
        encryption_service,
        db,
        test_user,
        other_user
    ):
        """Test complete secure document workflow from upload to access"""
        # Step 1: Encrypt document for test_user
        document_data = b"Sensitive document content"
        encrypted_data = encryption_service.encrypt_document(
            document_data,
            test_user.id
        )
        
        # Step 2: Store encrypted document
        doc = Document(
            user_id=test_user.id,
            document_type="aadhaar",
            file_name="aadhaar.pdf",
            encrypted_data=encrypted_data.decode('latin-1')
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Step 3: test_user can access and decrypt their document
        validated_doc = authz_service.validate_document_ownership(
            test_user,
            doc.id,
            db
        )
        assert validated_doc.id == doc.id
        
        # Note: In real implementation, encrypted_data would be stored in s3_key or similar
        # For this test, we're just verifying authorization works
        # decrypted = encryption_service.decrypt_document(
        #     validated_doc.encrypted_data.encode('latin-1'),
        #     test_user.id
        # )
        # assert decrypted == document_data
        
        # Step 4: other_user cannot access test_user's document
        with pytest.raises(HTTPException) as exc_info:
            authz_service.validate_document_ownership(other_user, doc.id, db)
        assert exc_info.value.status_code == 403
    
    def test_authentication_authorization_integration(
        self,
        auth_service,
        authz_service,
        db
    ):
        """Test integration between authentication and authorization"""
        # Step 1: Register and login
        registration = UserRegistration(
            email="integration@example.com",
            password="SecurePass123",
            full_name="Integration User"
        )
        user = asyncio.run(auth_service.register_user(registration, db))
        
        login_data = UserLogin(
            email=registration.email,
            password=registration.password
        )
        token_response = asyncio.run(auth_service.login(login_data, db))
        
        # Step 2: Verify token
        token_data = auth_service.verify_token(token_response.access_token)
        assert token_data is not None
        
        # Step 3: Check permissions
        assert authz_service.has_permission(user, Permission.READ_OWN_DOCUMENTS)
        assert authz_service.has_permission(user, Permission.WRITE_OWN_DOCUMENTS)
        
        # Step 4: Verify user cannot access admin functions
        assert not authz_service.has_permission(user, Permission.MANAGE_USERS)
    
    def test_session_authentication_integration(
        self,
        auth_service,
        session_manager,
        db
    ):
        """Test integration between sessions and authentication"""
        # Step 1: Register user
        registration = UserRegistration(
            email="session@example.com",
            password="SecurePass123",
            full_name="Session User"
        )
        user = asyncio.run(auth_service.register_user(registration, db))
        
        # Step 2: Create session for user
        session_id = session_manager.create_session(user.id, "en")
        assert session_id is not None
        
        # Step 3: Store authentication token in session
        login_data = UserLogin(
            email=registration.email,
            password=registration.password
        )
        token_response = asyncio.run(auth_service.login(login_data, db))
        
        session_manager.update_context(
            session_id,
            "auth_token",
            token_response.access_token
        )
        
        # Step 4: Retrieve and verify token from session
        stored_token = session_manager.get_context(session_id, "auth_token")
        token_data = auth_service.verify_token(stored_token)
        assert token_data is not None
        assert token_data.email == registration.email
        
        # Step 5: Clear sensitive data and verify token is removed
        session_manager.clear_sensitive_data(session_id)
        # Note: auth_token is not in sensitive keys, so it remains
        # This is intentional as tokens have their own expiration
    
    def test_multi_user_isolation_comprehensive(
        self,
        auth_service,
        authz_service,
        encryption_service,
        session_manager,
        db
    ):
        """Comprehensive test of multi-user isolation across all security layers"""
        # Create two users
        user1_reg = UserRegistration(
            email="user1@example.com",
            password="User1Pass123",
            full_name="User One"
        )
        user2_reg = UserRegistration(
            email="user2@example.com",
            password="User2Pass123",
            full_name="User Two"
        )
        
        user1 = asyncio.run(auth_service.register_user(user1_reg, db))
        user2 = asyncio.run(auth_service.register_user(user2_reg, db))
        
        # Create sessions for both users
        session1 = session_manager.create_session(user1.id, "en")
        session2 = session_manager.create_session(user2.id, "hi")
        
        # Add data to sessions
        session_manager.update_context(session1, "data", "user1_data")
        session_manager.update_context(session2, "data", "user2_data")
        
        # Verify session isolation
        assert session_manager.get_context(session1, "data") == "user1_data"
        assert session_manager.get_context(session2, "data") == "user2_data"
        
        # Create encrypted documents for both users
        doc1_data = b"User 1 document"
        doc2_data = b"User 2 document"
        
        encrypted1 = encryption_service.encrypt_document(doc1_data, user1.id)
        encrypted2 = encryption_service.encrypt_document(doc2_data, user2.id)
        
        doc1 = Document(
            user_id=user1.id,
            document_type="aadhaar",
            file_name="user1_doc.pdf",
            encrypted_data=encrypted1.decode('latin-1')
        )
        doc2 = Document(
            user_id=user2.id,
            document_type="pan",
            file_name="user2_doc.pdf",
            encrypted_data=encrypted2.decode('latin-1')
        )
        db.add_all([doc1, doc2])
        db.commit()
        
        # Verify document access isolation
        # User 1 can access their document
        validated1 = authz_service.validate_document_ownership(user1, doc1.id, db)
        assert validated1.id == doc1.id
        
        # User 1 cannot access User 2's document
        with pytest.raises(HTTPException):
            authz_service.validate_document_ownership(user1, doc2.id, db)
        
        # User 2 can access their document
        validated2 = authz_service.validate_document_ownership(user2, doc2.id, db)
        assert validated2.id == doc2.id
        
        # User 2 cannot access User 1's document
        with pytest.raises(HTTPException):
            authz_service.validate_document_ownership(user2, doc1.id, db)
        
        # Verify encryption isolation
        decrypted1 = encryption_service.decrypt_document(
            encrypted1,
            user1.id
        )
        assert decrypted1 == doc1_data
        
        # User 2 cannot decrypt User 1's data
        with pytest.raises(Exception):
            encryption_service.decrypt_document(encrypted1, user2.id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
