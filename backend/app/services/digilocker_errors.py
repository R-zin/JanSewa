"""
DigiLocker Error Handling

Custom exceptions and error handling utilities for DigiLocker integration.
"""

from typing import Optional
from enum import Enum


class DigiLockerErrorType(str, Enum):
    """Types of DigiLocker errors"""
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DOCUMENT_NOT_FOUND = "document_not_found"
    INVALID_TOKEN = "invalid_token"
    NETWORK_ERROR = "network_error"
    VALIDATION_FAILED = "validation_failed"
    UNKNOWN_ERROR = "unknown_error"


class DigiLockerError(Exception):
    """Base exception for DigiLocker errors"""
    
    def __init__(
        self,
        message: str,
        error_type: DigiLockerErrorType,
        retry_after: Optional[int] = None,
        details: Optional[dict] = None
    ):
        """
        Initialize DigiLocker error
        
        Args:
            message: Human-readable error message
            error_type: Type of error
            retry_after: Seconds to wait before retry (for rate limits)
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.retry_after = retry_after
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """Convert error to dictionary"""
        result = {
            "error": self.error_type,
            "message": self.message,
            "details": self.details
        }
        
        if self.retry_after:
            result["retry_after"] = self.retry_after
        
        return result


class AuthenticationError(DigiLockerError):
    """Authentication failure error"""
    
    def __init__(self, message: str = "DigiLocker authentication failed", details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_type=DigiLockerErrorType.AUTHENTICATION_FAILED,
            details=details
        )


class RateLimitError(DigiLockerError):
    """Rate limit exceeded error"""
    
    def __init__(self, retry_after: int, details: Optional[dict] = None):
        message = f"DigiLocker API rate limit exceeded. Please retry after {retry_after} seconds."
        super().__init__(
            message=message,
            error_type=DigiLockerErrorType.RATE_LIMIT_EXCEEDED,
            retry_after=retry_after,
            details=details
        )


class ServiceUnavailableError(DigiLockerError):
    """Service unavailable error"""
    
    def __init__(self, message: str = "DigiLocker service is temporarily unavailable", details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_type=DigiLockerErrorType.SERVICE_UNAVAILABLE,
            details=details
        )


class DocumentNotFoundError(DigiLockerError):
    """Document not found error"""
    
    def __init__(self, doc_id: str):
        message = f"Document '{doc_id}' not found in DigiLocker"
        super().__init__(
            message=message,
            error_type=DigiLockerErrorType.DOCUMENT_NOT_FOUND,
            details={"doc_id": doc_id}
        )


class InvalidTokenError(DigiLockerError):
    """Invalid or expired token error"""
    
    def __init__(self, message: str = "DigiLocker access token is invalid or expired"):
        super().__init__(
            message=message,
            error_type=DigiLockerErrorType.INVALID_TOKEN
        )
