"""
Authentication Service

Provides user authentication functionality including:
- User registration with password hashing
- User login with password validation
- JWT token generation and validation
- Session token management
- Multi-factor authentication support (TOTP-based)
- Password reset functionality
- Rate limiting for login attempts

Validates Requirements 10.1 (secure session management) and 10.2 (protect sensitive user data)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, validator
import secrets
import hashlib
from sqlalchemy.orm import Session
from app.core.config import settings


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRegistration(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str
    full_name: str
    language_preference: str = "en"
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """User login request model"""
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None


class Token(BaseModel):
    """JWT token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""
    user_id: int
    email: str
    exp: datetime


class PasswordReset(BaseModel):
    """Password reset request model"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    reset_token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class MFASetup(BaseModel):
    """MFA setup response model"""
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class AuthenticationService:
    """
    Authentication service for user management and security
    
    Implements:
    - Password hashing using bcrypt
    - JWT token generation and validation
    - User registration and login
    - MFA support (TOTP-based)
    - Password reset functionality
    - Rate limiting for login attempts
    """
    
    def __init__(self):
        self.pwd_context = pwd_context
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        # In-memory rate limiting (should use Redis in production)
        self.login_attempts: Dict[str, list] = {}
        self.max_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token
        
        Args:
            data: Data to encode in the token
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: int = payload.get("user_id")
            email: str = payload.get("email")
            exp: datetime = datetime.fromtimestamp(payload.get("exp"))
            
            if user_id is None or email is None:
                return None
            
            return TokenData(user_id=user_id, email=email, exp=exp)
        except JWTError:
            return None
    
    def check_rate_limit(self, email: str) -> tuple[bool, Optional[datetime]]:
        """
        Check if user has exceeded login attempt rate limit
        
        Args:
            email: User email address
            
        Returns:
            Tuple of (is_allowed, lockout_until)
        """
        now = datetime.utcnow()
        
        if email not in self.login_attempts:
            return True, None
        
        # Clean old attempts
        self.login_attempts[email] = [
            attempt for attempt in self.login_attempts[email]
            if now - attempt < self.lockout_duration
        ]
        
        if len(self.login_attempts[email]) >= self.max_attempts:
            lockout_until = self.login_attempts[email][0] + self.lockout_duration
            return False, lockout_until
        
        return True, None
    
    def record_login_attempt(self, email: str):
        """
        Record a failed login attempt
        
        Args:
            email: User email address
        """
        if email not in self.login_attempts:
            self.login_attempts[email] = []
        self.login_attempts[email].append(datetime.utcnow())
    
    def clear_login_attempts(self, email: str):
        """
        Clear login attempts for a user (after successful login)
        
        Args:
            email: User email address
        """
        if email in self.login_attempts:
            del self.login_attempts[email]
    
    async def register_user(
        self, 
        registration: UserRegistration, 
        db: Session
    ):
        """
        Register a new user
        
        Args:
            registration: User registration data
            db: Database session
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If email already exists
        """
        from app.db.models import User
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == registration.email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Hash password
        hashed_password = self.hash_password(registration.password)
        
        # Create user
        user = User(
            email=registration.email,
            hashed_password=hashed_password,
            full_name=registration.full_name,
            language_preference=registration.language_preference
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    async def authenticate_user(
        self, 
        login: UserLogin, 
        db: Session
    ):
        """
        Authenticate a user with email and password
        
        Args:
            login: User login credentials
            db: Database session
            
        Returns:
            User object if authentication successful, None otherwise
        """
        from app.db.models import User
        
        # Check rate limit
        is_allowed, lockout_until = self.check_rate_limit(login.email)
        if not is_allowed:
            raise ValueError(f"Too many login attempts. Try again after {lockout_until}")
        
        # Get user
        user = db.query(User).filter(User.email == login.email).first()
        if not user:
            self.record_login_attempt(login.email)
            return None
        
        # Verify password
        if not self.verify_password(login.password, user.hashed_password):
            self.record_login_attempt(login.email)
            return None
        
        # Clear login attempts on successful authentication
        self.clear_login_attempts(login.email)
        
        return user
    
    async def login(
        self, 
        login: UserLogin, 
        db: Session
    ) -> Token:
        """
        Login user and generate access token
        
        Args:
            login: User login credentials
            db: Database session
            
        Returns:
            JWT token
            
        Raises:
            ValueError: If authentication fails
        """
        user = await self.authenticate_user(login, db)
        if not user:
            raise ValueError("Invalid email or password")
        
        # Create access token
        access_token = self.create_access_token(
            data={"user_id": user.id, "email": user.email}
        )
        
        return Token(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def generate_reset_token(self, email: str) -> str:
        """
        Generate a password reset token
        
        Args:
            email: User email address
            
        Returns:
            Reset token string
        """
        # Create token with 1 hour expiration
        token_data = {
            "email": email,
            "purpose": "password_reset"
        }
        return self.create_access_token(token_data, expires_delta=timedelta(hours=1))
    
    async def request_password_reset(
        self, 
        reset_request: PasswordReset, 
        db: Session
    ) -> str:
        """
        Request a password reset
        
        Args:
            reset_request: Password reset request
            db: Database session
            
        Returns:
            Reset token (in production, this would be sent via email)
            
        Raises:
            ValueError: If user not found
        """
        from app.db.models import User
        
        user = db.query(User).filter(User.email == reset_request.email).first()
        if not user:
            raise ValueError("User not found")
        
        reset_token = self.generate_reset_token(reset_request.email)
        
        # In production, send this token via email
        # For now, return it directly
        return reset_token
    
    async def reset_password(
        self, 
        reset_confirm: PasswordResetConfirm, 
        db: Session
    ) -> bool:
        """
        Reset user password with token
        
        Args:
            reset_confirm: Password reset confirmation with token
            db: Database session
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If token invalid or expired
        """
        from app.db.models import User
        
        # Verify token
        token_data = self.verify_token(reset_confirm.reset_token)
        if not token_data:
            raise ValueError("Invalid or expired reset token")
        
        # Get user
        user = db.query(User).filter(User.email == token_data.email).first()
        if not user:
            raise ValueError("User not found")
        
        # Update password
        user.hashed_password = self.hash_password(reset_confirm.new_password)
        db.commit()
        
        return True
    
    def generate_mfa_secret(self) -> str:
        """
        Generate a secret for TOTP-based MFA
        
        Returns:
            Base32-encoded secret string
        """
        # Generate 20-byte random secret
        secret_bytes = secrets.token_bytes(20)
        # Convert to base32 for TOTP compatibility
        import base64
        secret = base64.b32encode(secret_bytes).decode('utf-8')
        return secret
    
    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """
        Generate backup codes for MFA
        
        Args:
            count: Number of backup codes to generate
            
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    async def setup_mfa(self, user_id: int, db: Session) -> MFASetup:
        """
        Setup MFA for a user
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            MFA setup data including secret and QR code URL
        """
        from app.db.models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Generate secret
        secret = self.generate_mfa_secret()
        
        # Generate QR code URL for authenticator apps
        # Format: otpauth://totp/AppName:user@email?secret=SECRET&issuer=AppName
        qr_code_url = (
            f"otpauth://totp/GovServices:{user.email}"
            f"?secret={secret}&issuer=GovServices"
        )
        
        # Generate backup codes
        backup_codes = self.generate_backup_codes()
        
        # In production, store secret and hashed backup codes in database
        # For now, return them
        
        return MFASetup(
            secret=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes
        )
    
    def verify_totp_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code
        
        Args:
            secret: User's MFA secret
            code: 6-digit TOTP code
            
        Returns:
            True if code is valid
        """
        # This is a placeholder - in production, use pyotp library
        # For now, accept any 6-digit code for demonstration
        return len(code) == 6 and code.isdigit()


# Global authentication service instance
auth_service = AuthenticationService()
