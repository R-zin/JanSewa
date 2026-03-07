"""
Authentication API Endpoints

Provides REST API endpoints for:
- User registration
- User login
- Token validation
- Password reset
- MFA setup and verification

Validates Requirements 10.1 and 10.2
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.services.authentication import (
    auth_service,
    UserRegistration,
    UserLogin,
    Token,
    PasswordReset,
    PasswordResetConfirm,
    MFASetup
)
from app.db.models import User
from app.db.base import get_db


router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer token
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    registration: UserRegistration,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    Args:
        registration: User registration data
        db: Database session
        
    Returns:
        Success message with user ID
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    try:
        user = await auth_service.register_user(registration, db)
        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "email": user.email
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT token
    
    Args:
        login_data: User login credentials
        db: Database session
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = await auth_service.login(login_data, db)
        return token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information (excluding password)
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "language_preference": current_user.language_preference,
        "created_at": current_user.created_at
    }


@router.post("/password-reset/request", response_model=dict)
async def request_password_reset(
    reset_request: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Request a password reset token
    
    Args:
        reset_request: Password reset request with email
        db: Database session
        
    Returns:
        Success message (in production, token would be sent via email)
        
    Raises:
        HTTPException: If user not found
    """
    try:
        reset_token = await auth_service.request_password_reset(reset_request, db)
        # In production, send this via email
        # For now, return it in response (NOT SECURE - for demo only)
        return {
            "message": "Password reset token generated",
            "reset_token": reset_token  # Remove this in production
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )


@router.post("/password-reset/confirm", response_model=dict)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token
    
    Args:
        reset_confirm: Password reset confirmation with token and new password
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If token invalid or reset fails
    """
    try:
        await auth_service.reset_password(reset_confirm, db)
        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/mfa/setup", response_model=MFASetup)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Setup multi-factor authentication for current user
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        MFA setup data including secret and QR code URL
        
    Raises:
        HTTPException: If setup fails
    """
    try:
        mfa_setup = await auth_service.setup_mfa(current_user.id, db)
        return mfa_setup
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup failed"
        )


@router.post("/mfa/verify", response_model=dict)
async def verify_mfa(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """
    Verify MFA code
    
    Args:
        code: 6-digit TOTP code
        current_user: Current authenticated user
        
    Returns:
        Verification result
        
    Raises:
        HTTPException: If verification fails
    """
    # In production, retrieve user's MFA secret from database
    # For now, this is a placeholder
    secret = "placeholder_secret"
    
    is_valid = auth_service.verify_totp_code(secret, code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code"
        )
    
    return {"message": "MFA code verified successfully"}


@router.post("/token/validate", response_model=dict)
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    """
    Validate current JWT token
    
    Args:
        current_user: Current authenticated user (validates token)
        
    Returns:
        Validation result with user info
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email
    }
