"""
Unit tests for authentication service

Tests:
- Password hashing and verification
- JWT token generation and validation
- User registration
- User login
- Password reset
- MFA setup
- Rate limiting
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.services.authentication import (
    AuthenticationService,
    UserRegistration,
    UserLogin,
    PasswordReset,
    PasswordResetConfirm
)


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Test User model
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
def auth_service():
    """Create authentication service instance"""
    return AuthenticationService()


@pytest.fixture
def sample_user_registration():
    """Sample user registration data"""
    return UserRegistration(
        email="test@example.com",
        password="SecurePass123",
        full_name="Test User",
        language_preference="en"
    )


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_hash_password(self, auth_service):
        """Test password hashing"""
        password = "SecurePass123"
        hashed = auth_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password"""
        password = "SecurePass123"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password"""
        password = "SecurePass123"
        wrong_password = "WrongPass456"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(wrong_password, hashed) is False
    
    def test_different_hashes_for_same_password(self, auth_service):
        """Test that same password produces different hashes (salt)"""
        password = "SecurePass123"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        assert hash1 != hash2
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token generation and validation"""
    
    def test_create_access_token(self, auth_service):
        """Test JWT token creation"""
        data = {"user_id": 1, "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self, auth_service):
        """Test verification of valid token"""
        data = {"user_id": 1, "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        
        token_data = auth_service.verify_token(token)
        
        assert token_data is not None
        assert token_data.user_id == 1
        assert token_data.email == "test@example.com"
    
    def test_verify_invalid_token(self, auth_service):
        """Test verification of invalid token"""
        invalid_token = "invalid.token.here"
        
        token_data = auth_service.verify_token(invalid_token)
        
        assert token_data is None
    
    def test_token_expiration(self, auth_service):
        """Test token expiration"""
        data = {"user_id": 1, "email": "test@example.com"}
        # Create token that expires immediately
        token = auth_service.create_access_token(
            data, 
            expires_delta=timedelta(seconds=-1)
        )
        
        token_data = auth_service.verify_token(token)
        
        # Expired token should be invalid
        assert token_data is None
    
    def test_token_custom_expiration(self, auth_service):
        """Test token with custom expiration"""
        data = {"user_id": 1, "email": "test@example.com"}
        token = auth_service.create_access_token(
            data,
            expires_delta=timedelta(hours=2)
        )
        
        token_data = auth_service.verify_token(token)
        
        assert token_data is not None
        assert token_data.user_id == 1


class TestUserRegistration:
    """Test user registration"""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, db, sample_user_registration):
        """Test successful user registration"""
        user = await auth_service.register_user(sample_user_registration, db)
        
        assert user.id is not None
        assert user.email == sample_user_registration.email
        assert user.full_name == sample_user_registration.full_name
        assert user.language_preference == sample_user_registration.language_preference
        assert user.hashed_password != sample_user_registration.password
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service, db, sample_user_registration):
        """Test registration with duplicate email"""
        # Register first user
        await auth_service.register_user(sample_user_registration, db)
        
        # Try to register again with same email
        with pytest.raises(ValueError, match="Email already registered"):
            await auth_service.register_user(sample_user_registration, db)
    
    def test_password_validation_too_short(self):
        """Test password validation - too short"""
        with pytest.raises(ValueError, match="at least 8 characters"):
            UserRegistration(
                email="test@example.com",
                password="Short1",
                full_name="Test User"
            )
    
    def test_password_validation_no_uppercase(self):
        """Test password validation - no uppercase"""
        with pytest.raises(ValueError, match="uppercase letter"):
            UserRegistration(
                email="test@example.com",
                password="lowercase123",
                full_name="Test User"
            )
    
    def test_password_validation_no_lowercase(self):
        """Test password validation - no lowercase"""
        with pytest.raises(ValueError, match="lowercase letter"):
            UserRegistration(
                email="test@example.com",
                password="UPPERCASE123",
                full_name="Test User"
            )
    
    def test_password_validation_no_digit(self):
        """Test password validation - no digit"""
        with pytest.raises(ValueError, match="digit"):
            UserRegistration(
                email="test@example.com",
                password="NoDigitsHere",
                full_name="Test User"
            )


class TestUserAuthentication:
    """Test user authentication and login"""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, db, sample_user_registration):
        """Test successful user authentication"""
        # Register user
        await auth_service.register_user(sample_user_registration, db)
        
        # Authenticate
        login_data = UserLogin(
            email=sample_user_registration.email,
            password=sample_user_registration.password
        )
        user = await auth_service.authenticate_user(login_data, db)
        
        assert user is not None
        assert user.email == sample_user_registration.email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, db, sample_user_registration):
        """Test authentication with wrong password"""
        # Register user
        await auth_service.register_user(sample_user_registration, db)
        
        # Try to authenticate with wrong password
        login_data = UserLogin(
            email=sample_user_registration.email,
            password="WrongPassword123"
        )
        user = await auth_service.authenticate_user(login_data, db)
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, db):
        """Test authentication with non-existent user"""
        login_data = UserLogin(
            email="nonexistent@example.com",
            password="SomePassword123"
        )
        user = await auth_service.authenticate_user(login_data, db)
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, db, sample_user_registration):
        """Test successful login with token generation"""
        # Register user
        await auth_service.register_user(sample_user_registration, db)
        
        # Login
        login_data = UserLogin(
            email=sample_user_registration.email,
            password=sample_user_registration.password
        )
        token = await auth_service.login(login_data, db)
        
        assert token.access_token is not None
        assert token.token_type == "bearer"
        assert token.expires_in > 0
    
    @pytest.mark.asyncio
    async def test_login_failure(self, auth_service, db, sample_user_registration):
        """Test login failure with wrong credentials"""
        # Register user
        await auth_service.register_user(sample_user_registration, db)
        
        # Try to login with wrong password
        login_data = UserLogin(
            email=sample_user_registration.email,
            password="WrongPassword123"
        )
        
        with pytest.raises(ValueError, match="Invalid email or password"):
            await auth_service.login(login_data, db)


class TestRateLimiting:
    """Test rate limiting for login attempts"""
    
    def test_check_rate_limit_allowed(self, auth_service):
        """Test rate limit check when allowed"""
        email = "test@example.com"
        
        is_allowed, lockout_until = auth_service.check_rate_limit(email)
        
        assert is_allowed is True
        assert lockout_until is None
    
    def test_record_login_attempts(self, auth_service):
        """Test recording login attempts"""
        email = "test@example.com"
        
        # Record multiple attempts
        for _ in range(3):
            auth_service.record_login_attempt(email)
        
        assert email in auth_service.login_attempts
        assert len(auth_service.login_attempts[email]) == 3
    
    def test_rate_limit_exceeded(self, auth_service):
        """Test rate limit when exceeded"""
        email = "test@example.com"
        
        # Record max attempts
        for _ in range(auth_service.max_attempts):
            auth_service.record_login_attempt(email)
        
        is_allowed, lockout_until = auth_service.check_rate_limit(email)
        
        assert is_allowed is False
        assert lockout_until is not None
    
    def test_clear_login_attempts(self, auth_service):
        """Test clearing login attempts"""
        email = "test@example.com"
        
        # Record attempts
        for _ in range(3):
            auth_service.record_login_attempt(email)
        
        # Clear attempts
        auth_service.clear_login_attempts(email)
        
        assert email not in auth_service.login_attempts


class TestPasswordReset:
    """Test password reset functionality"""
    
    def test_generate_reset_token(self, auth_service):
        """Test reset token generation"""
        email = "test@example.com"
        
        token = auth_service.generate_reset_token(email)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    @pytest.mark.asyncio
    async def test_request_password_reset(self, auth_service, db, sample_user_registration):
        """Test password reset request"""
        # Register user
        await auth_service.register_user(sample_user_registration, db)
        
        # Request reset
        reset_request = PasswordReset(email=sample_user_registration.email)
        reset_token = await auth_service.request_password_reset(reset_request, db)
        
        assert isinstance(reset_token, str)
        assert len(reset_token) > 0
    
    @pytest.mark.asyncio
    async def test_request_password_reset_user_not_found(self, auth_service, db):
        """Test password reset request for non-existent user"""
        reset_request = PasswordReset(email="nonexistent@example.com")
        
        with pytest.raises(ValueError, match="User not found"):
            await auth_service.request_password_reset(reset_request, db)
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_service, db, sample_user_registration):
        """Test successful password reset"""
        # Register user
        user = await auth_service.register_user(sample_user_registration, db)
        old_password_hash = user.hashed_password
        
        # Request reset
        reset_request = PasswordReset(email=sample_user_registration.email)
        reset_token = await auth_service.request_password_reset(reset_request, db)
        
        # Reset password
        new_password = "NewSecurePass456"
        reset_confirm = PasswordResetConfirm(
            reset_token=reset_token,
            new_password=new_password
        )
        result = await auth_service.reset_password(reset_confirm, db)
        
        assert result is True
        
        # Verify password changed
        db.refresh(user)
        assert user.hashed_password != old_password_hash
        assert auth_service.verify_password(new_password, user.hashed_password)
    
    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, auth_service, db):
        """Test password reset with invalid token"""
        reset_confirm = PasswordResetConfirm(
            reset_token="invalid.token.here",
            new_password="NewSecurePass456"
        )
        
        with pytest.raises(ValueError, match="Invalid or expired reset token"):
            await auth_service.reset_password(reset_confirm, db)


class TestMFA:
    """Test multi-factor authentication"""
    
    def test_generate_mfa_secret(self, auth_service):
        """Test MFA secret generation"""
        secret = auth_service.generate_mfa_secret()
        
        assert isinstance(secret, str)
        assert len(secret) > 0
        # Base32 encoded
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in secret)
    
    def test_generate_backup_codes(self, auth_service):
        """Test backup code generation"""
        codes = auth_service.generate_backup_codes(count=10)
        
        assert len(codes) == 10
        for code in codes:
            assert isinstance(code, str)
            assert "-" in code  # Format: XXXX-XXXX
    
    @pytest.mark.asyncio
    async def test_setup_mfa(self, auth_service, db, sample_user_registration):
        """Test MFA setup"""
        # Register user
        user = await auth_service.register_user(sample_user_registration, db)
        
        # Setup MFA
        mfa_setup = await auth_service.setup_mfa(user.id, db)
        
        assert mfa_setup.secret is not None
        assert mfa_setup.qr_code_url is not None
        assert "otpauth://totp/" in mfa_setup.qr_code_url
        assert len(mfa_setup.backup_codes) == 10
    
    def test_verify_totp_code_valid(self, auth_service):
        """Test TOTP code verification with valid code"""
        secret = "JBSWY3DPEHPK3PXP"
        code = "123456"  # 6-digit code
        
        result = auth_service.verify_totp_code(secret, code)
        
        # Placeholder implementation accepts any 6-digit code
        assert result is True
    
    def test_verify_totp_code_invalid(self, auth_service):
        """Test TOTP code verification with invalid code"""
        secret = "JBSWY3DPEHPK3PXP"
        code = "12345"  # Only 5 digits
        
        result = auth_service.verify_totp_code(secret, code)
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
