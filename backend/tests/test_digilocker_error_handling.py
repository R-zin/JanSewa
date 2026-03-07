"""
Tests for DigiLocker Error Handling

Tests error handling, retry logic, and partial import functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.digilocker_errors import (
    DigiLockerError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    DocumentNotFoundError,
    InvalidTokenError,
    DigiLockerErrorType
)
from app.services.digilocker_retry import (
    RetryStrategy,
    RetryConfig,
    RateLimiter
)
from app.services.digilocker_client_enhanced import (
    EnhancedDigiLockerClient,
    ImportResult
)


class TestDigiLockerErrors:
    """Test DigiLocker error classes"""
    
    def test_authentication_error(self):
        """Test authentication error creation"""
        error = AuthenticationError(
            message="Auth failed",
            details={"user_id": "test123"}
        )
        
        assert error.error_type == DigiLockerErrorType.AUTHENTICATION_FAILED
        assert error.message == "Auth failed"
        assert error.details["user_id"] == "test123"
        assert error.retry_after is None
    
    def test_rate_limit_error(self):
        """Test rate limit error with retry_after"""
        error = RateLimitError(retry_after=60)
        
        assert error.error_type == DigiLockerErrorType.RATE_LIMIT_EXCEEDED
        assert error.retry_after == 60
        assert "60 seconds" in error.message
    
    def test_service_unavailable_error(self):
        """Test service unavailable error"""
        error = ServiceUnavailableError()
        
        assert error.error_type == DigiLockerErrorType.SERVICE_UNAVAILABLE
        assert "temporarily unavailable" in error.message.lower()
    
    def test_document_not_found_error(self):
        """Test document not found error"""
        error = DocumentNotFoundError(doc_id="doc123")
        
        assert error.error_type == DigiLockerErrorType.DOCUMENT_NOT_FOUND
        assert "doc123" in error.message
        assert error.details["doc_id"] == "doc123"
    
    def test_error_to_dict(self):
        """Test error serialization"""
        error = RateLimitError(retry_after=30, details={"endpoint": "/documents"})
        error_dict = error.to_dict()
        
        assert error_dict["error"] == DigiLockerErrorType.RATE_LIMIT_EXCEEDED
        assert error_dict["retry_after"] == 30
        assert error_dict["details"]["endpoint"] == "/documents"


class TestRetryStrategy:
    """Test retry strategy and exponential backoff"""
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=False
        )
        strategy = RetryStrategy(config)
        
        # First retry: 1 * 2^0 = 1
        assert strategy.calculate_delay(0) == 1.0
        
        # Second retry: 1 * 2^1 = 2
        assert strategy.calculate_delay(1) == 2.0
        
        # Third retry: 1 * 2^2 = 4
        assert strategy.calculate_delay(2) == 4.0
    
    def test_calculate_delay_max_cap(self):
        """Test delay is capped at max_delay"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False
        )
        strategy = RetryStrategy(config)
        
        # Large attempt number should be capped
        delay = strategy.calculate_delay(10)
        assert delay == 10.0
    
    def test_calculate_delay_with_retry_after(self):
        """Test explicit retry_after overrides calculation"""
        config = RetryConfig()
        strategy = RetryStrategy(config)
        
        # Explicit retry_after should be used
        delay = strategy.calculate_delay(0, retry_after=45)
        assert delay == 45.0
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt"""
        strategy = RetryStrategy(RetryConfig(max_attempts=3))
        
        mock_func = AsyncMock(return_value="success")
        
        result = await strategy.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful execution after retries"""
        strategy = RetryStrategy(RetryConfig(
            max_attempts=3,
            initial_delay=0.01  # Fast for testing
        ))
        
        # Fail twice, then succeed
        mock_func = AsyncMock(
            side_effect=[
                ServiceUnavailableError(),
                ServiceUnavailableError(),
                "success"
            ]
        )
        
        result = await strategy.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test all retries exhausted"""
        strategy = RetryStrategy(RetryConfig(
            max_attempts=2,
            initial_delay=0.01
        ))
        
        # Always fail
        mock_func = AsyncMock(
            side_effect=ServiceUnavailableError("Service down")
        )
        
        with pytest.raises(ServiceUnavailableError):
            await strategy.execute_with_retry(mock_func)
        
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_authentication_error(self):
        """Test authentication errors are not retried"""
        strategy = RetryStrategy(RetryConfig(max_attempts=3))
        
        mock_func = AsyncMock(
            side_effect=AuthenticationError("Invalid credentials")
        )
        
        with pytest.raises(AuthenticationError):
            await strategy.execute_with_retry(mock_func)
        
        # Should fail immediately without retry
        assert mock_func.call_count == 1


class TestRateLimiter:
    """Test rate limiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test rate limiter allows requests within limit"""
        limiter = RateLimiter(max_requests=5, time_window=1.0)
        
        # Should allow 5 requests
        for _ in range(5):
            await limiter.acquire()
        
        assert len(limiter.requests) == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess(self):
        """Test rate limiter blocks requests exceeding limit"""
        limiter = RateLimiter(max_requests=2, time_window=0.5)
        
        # First 2 requests should be immediate
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        await limiter.acquire()
        first_two = asyncio.get_event_loop().time() - start
        
        # Third request should be delayed
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        third = asyncio.get_event_loop().time() - start
        
        assert first_two < 0.1  # First two are fast
        assert third >= 0.4  # Third is delayed


class TestImportResult:
    """Test ImportResult class"""
    
    def test_successful_import_result(self):
        """Test successful import result"""
        result = ImportResult(
            doc_id="doc123",
            success=True,
            data={"name": "Aadhaar Card"}
        )
        
        assert result.success
        assert result.data["name"] == "Aadhaar Card"
        assert result.error is None
        
        result_dict = result.to_dict()
        assert result_dict["success"]
        assert result_dict["data"]["name"] == "Aadhaar Card"
    
    def test_failed_import_result(self):
        """Test failed import result"""
        error = DocumentNotFoundError("doc123")
        result = ImportResult(
            doc_id="doc123",
            success=False,
            error=error
        )
        
        assert not result.success
        assert result.error == error
        assert result.data is None
        
        result_dict = result.to_dict()
        assert not result_dict["success"]
        assert "error" in result_dict


class TestEnhancedDigiLockerClient:
    """Test enhanced DigiLocker client"""
    
    @pytest.fixture
    def mock_authenticator(self):
        """Create mock authenticator"""
        auth = Mock()
        auth.is_authenticated.return_value = True
        auth.get_access_token.return_value = "mock_token"
        return auth
    
    @pytest.fixture
    def client(self, mock_authenticator):
        """Create enhanced client"""
        return EnhancedDigiLockerClient(
            authenticator=mock_authenticator,
            retry_config=RetryConfig(
                max_attempts=2,
                initial_delay=0.01
            ),
            rate_limit_config=(10, 1.0)
        )
    
    def test_handle_api_error_authentication(self, client):
        """Test authentication error handling"""
        error = Exception("401 Unauthorized")
        result = client._handle_api_error(error, "test_op")
        
        assert isinstance(result, AuthenticationError)
        assert "authentication" in result.message.lower()
    
    def test_handle_api_error_rate_limit(self, client):
        """Test rate limit error handling"""
        error = Exception("429 Too Many Requests")
        result = client._handle_api_error(error, "test_op")
        
        assert isinstance(result, RateLimitError)
        assert result.retry_after is not None
    
    def test_handle_api_error_service_unavailable(self, client):
        """Test service unavailable error handling"""
        error = Exception("503 Service Unavailable")
        result = client._handle_api_error(error, "test_op")
        
        assert isinstance(result, ServiceUnavailableError)
    
    def test_handle_api_error_not_found(self, client):
        """Test not found error handling"""
        error = Exception("404 Not Found")
        result = client._handle_api_error(error, "test_op", {"doc_id": "doc123"})
        
        assert isinstance(result, DocumentNotFoundError)
        assert result.details["doc_id"] == "doc123"
    
    def test_record_error(self, client):
        """Test error statistics recording"""
        client._record_error("rate_limit_exceeded")
        client._record_error("rate_limit_exceeded")
        client._record_error("service_unavailable")
        
        stats = client.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert stats["by_type"]["rate_limit_exceeded"] == 2
        assert stats["by_type"]["service_unavailable"] == 1
    
    def test_get_user_friendly_error_message(self, client):
        """Test user-friendly error messages"""
        # Authentication error
        auth_error = AuthenticationError()
        message = client.get_user_friendly_error_message(auth_error)
        assert "connect" in message.lower()
        assert "account" in message.lower()
        
        # Rate limit error
        rate_error = RateLimitError(retry_after=60)
        message = client.get_user_friendly_error_message(rate_error)
        assert "60" in message
        assert "wait" in message.lower()
        
        # Service unavailable
        service_error = ServiceUnavailableError()
        message = client.get_user_friendly_error_message(service_error)
        assert "unavailable" in message.lower()
        assert "try again" in message.lower()
    
    @pytest.mark.asyncio
    async def test_bulk_import_partial_success(self, client, mock_authenticator):
        """Test bulk import with partial success"""
        # Mock import_document to succeed for some, fail for others
        async def mock_import(user_id, doc_id):
            if doc_id == "fail_doc":
                raise DocumentNotFoundError(doc_id)
            return {"doc_id": doc_id, "name": f"Document {doc_id}"}
        
        with patch.object(client, 'import_document', side_effect=mock_import):
            results = await client.bulk_import_with_partial_handling(
                user_id="user123",
                doc_ids=["doc1", "doc2", "fail_doc", "doc3"],
                continue_on_error=True
            )
        
        assert results["total"] == 4
        assert len(results["successful"]) == 3
        assert len(results["failed"]) == 1
        assert results["partial_success"]
        
        # Check failed document
        failed = results["failed"][0]
        assert failed["doc_id"] == "fail_doc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
