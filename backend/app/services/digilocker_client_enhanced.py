"""
Enhanced DigiLocker Client with Error Handling

Extends DigiLocker client with comprehensive error handling, retry logic,
and partial import support.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import asyncio

from .digilocker_client import (
    DigiLockerClient,
    DigiLockerDocument,
    SyncStatus,
    SyncHistory,
    DocumentCategory
)
from .digilocker_auth import DigiLockerAuthenticator
from .digilocker_errors import (
    DigiLockerError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    DocumentNotFoundError,
    InvalidTokenError
)
from .digilocker_retry import RetryStrategy, RetryConfig, RateLimiter

logger = logging.getLogger(__name__)


class ImportResult:
    """Result of a document import operation"""
    
    def __init__(
        self,
        doc_id: str,
        success: bool,
        data: Optional[Dict] = None,
        error: Optional[DigiLockerError] = None
    ):
        self.doc_id = doc_id
        self.success = success
        self.data = data
        self.error = error
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            "doc_id": self.doc_id,
            "success": self.success
        }
        
        if self.success and self.data:
            result["data"] = self.data
        elif not self.success and self.error:
            result["error"] = self.error.to_dict()
        
        return result


class EnhancedDigiLockerClient(DigiLockerClient):
    """
    Enhanced DigiLocker client with error handling and retry logic
    """
    
    def __init__(
        self,
        authenticator: DigiLockerAuthenticator,
        retry_config: Optional[RetryConfig] = None,
        rate_limit_config: Optional[Tuple[int, float]] = None
    ):
        """
        Initialize enhanced DigiLocker client
        
        Args:
            authenticator: DigiLocker authentication service
            retry_config: Configuration for retry behavior
            rate_limit_config: Tuple of (max_requests, time_window_seconds)
        """
        super().__init__(authenticator)
        
        # Initialize retry strategy
        self.retry_strategy = RetryStrategy(retry_config or RetryConfig())
        
        # Initialize rate limiter (default: 10 requests per minute)
        rate_limit = rate_limit_config or (10, 60.0)
        self.rate_limiter = RateLimiter(rate_limit[0], rate_limit[1])
        
        # Track error statistics
        self.error_stats: Dict[str, int] = {}
    
    async def list_documents_with_retry(
        self,
        user_id: str,
        category: Optional[DocumentCategory] = None
    ) -> List[DigiLockerDocument]:
        """
        List documents with retry logic
        
        Args:
            user_id: User ID
            category: Optional filter by category
            
        Returns:
            List of documents
            
        Raises:
            DigiLockerError: If operation fails after retries
        """
        async def _list_documents():
            # Acquire rate limit permission
            await self.rate_limiter.acquire()
            
            # Check authentication
            if not self.authenticator.is_authenticated(user_id):
                raise AuthenticationError(
                    message="User not authenticated with DigiLocker. Please reconnect your account.",
                    details={"user_id": user_id}
                )
            
            try:
                # Call parent method
                return await self.list_documents(user_id, category)
                
            except Exception as e:
                # Convert to DigiLocker error
                raise self._handle_api_error(e, "list_documents")
        
        return await self.retry_strategy.execute_with_retry(_list_documents)
    
    async def import_document_with_retry(
        self,
        user_id: str,
        doc_id: str
    ) -> ImportResult:
        """
        Import document with retry logic and error handling
        
        Args:
            user_id: User ID
            doc_id: Document ID
            
        Returns:
            ImportResult with success status and data or error
        """
        async def _import_document():
            # Acquire rate limit permission
            await self.rate_limiter.acquire()
            
            # Check authentication
            if not self.authenticator.is_authenticated(user_id):
                raise AuthenticationError(
                    message="User not authenticated with DigiLocker. Please reconnect your account.",
                    details={"user_id": user_id}
                )
            
            try:
                # Call parent method
                data = await self.import_document(user_id, doc_id)
                return data
                
            except Exception as e:
                # Convert to DigiLocker error
                raise self._handle_api_error(e, "import_document", {"doc_id": doc_id})
        
        try:
            data = await self.retry_strategy.execute_with_retry(_import_document)
            return ImportResult(doc_id=doc_id, success=True, data=data)
            
        except DigiLockerError as e:
            logger.error(f"Failed to import document {doc_id}: {e.message}")
            self._record_error(e.error_type)
            return ImportResult(doc_id=doc_id, success=False, error=e)
    
    async def bulk_import_with_partial_handling(
        self,
        user_id: str,
        doc_ids: List[str],
        continue_on_error: bool = True
    ) -> Dict:
        """
        Import multiple documents with partial import support
        
        Args:
            user_id: User ID
            doc_ids: List of document IDs
            continue_on_error: Whether to continue if some imports fail
            
        Returns:
            Detailed results including successful and failed imports
        """
        results = {
            "total": len(doc_ids),
            "successful": [],
            "failed": [],
            "partial_success": False
        }
        
        logger.info(f"Starting bulk import of {len(doc_ids)} documents for user {user_id}")
        
        # Import documents one by one with error handling
        for doc_id in doc_ids:
            try:
                import_result = await self.import_document_with_retry(user_id, doc_id)
                
                if import_result.success:
                    results["successful"].append(import_result.to_dict())
                    logger.info(f"Successfully imported document {doc_id}")
                else:
                    results["failed"].append(import_result.to_dict())
                    logger.warning(f"Failed to import document {doc_id}")
                    
                    # Stop if continue_on_error is False
                    if not continue_on_error:
                        logger.info("Stopping bulk import due to error")
                        break
                        
            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error importing {doc_id}: {str(e)}")
                results["failed"].append({
                    "doc_id": doc_id,
                    "success": False,
                    "error": {
                        "error": "unknown_error",
                        "message": str(e)
                    }
                })
                
                if not continue_on_error:
                    break
        
        # Determine if this was a partial success
        has_successes = len(results["successful"]) > 0
        has_failures = len(results["failed"]) > 0
        results["partial_success"] = has_successes and has_failures
        
        # Log summary
        logger.info(
            f"Bulk import completed: {len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )
        
        return results
    
    async def sync_documents_with_error_handling(
        self,
        user_id: str,
        auto_import: bool = False
    ) -> str:
        """
        Sync documents with comprehensive error handling
        
        Args:
            user_id: User ID
            auto_import: Whether to automatically import documents
            
        Returns:
            Sync ID for tracking
        """
        sync_id = f"sync_{user_id}_{datetime.now().timestamp()}"
        
        # Create sync history entry
        sync_record = SyncHistory(
            sync_id=sync_id,
            user_id=user_id,
            started_at=datetime.now(),
            completed_at=None,
            status=SyncStatus.IN_PROGRESS,
            documents_synced=0,
            documents_failed=0
        )
        
        self.sync_history[sync_id] = sync_record
        
        try:
            # List documents with retry
            documents = await self.list_documents_with_retry(user_id)
            
            # If auto_import, import all documents
            if auto_import:
                doc_ids = [d.doc_id for d in documents]
                import_results = await self.bulk_import_with_partial_handling(
                    user_id,
                    doc_ids,
                    continue_on_error=True
                )
                
                sync_record.documents_synced = len(import_results["successful"])
                sync_record.documents_failed = len(import_results["failed"])
                
                # If partial success, include details
                if import_results["partial_success"]:
                    sync_record.error_message = (
                        f"Partial import: {sync_record.documents_synced} succeeded, "
                        f"{sync_record.documents_failed} failed"
                    )
            else:
                sync_record.documents_synced = len(documents)
            
            sync_record.status = SyncStatus.COMPLETED
            sync_record.completed_at = datetime.now()
            
            logger.info(f"Sync {sync_id} completed successfully")
            
        except AuthenticationError as e:
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = e.message
            sync_record.completed_at = datetime.now()
            logger.error(f"Sync {sync_id} failed: {e.message}")
            
        except ServiceUnavailableError as e:
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = (
                "DigiLocker service is temporarily unavailable. "
                "Please try again in a few minutes."
            )
            sync_record.completed_at = datetime.now()
            logger.error(f"Sync {sync_id} failed: Service unavailable")
            
        except RateLimitError as e:
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = e.message
            sync_record.completed_at = datetime.now()
            logger.error(f"Sync {sync_id} failed: Rate limit exceeded")
            
        except DigiLockerError as e:
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = e.message
            sync_record.completed_at = datetime.now()
            logger.error(f"Sync {sync_id} failed: {e.message}")
            
        except Exception as e:
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = f"Unexpected error: {str(e)}"
            sync_record.completed_at = datetime.now()
            logger.error(f"Sync {sync_id} failed with unexpected error: {str(e)}")
        
        return sync_id
    
    def _handle_api_error(
        self,
        error: Exception,
        operation: str,
        context: Optional[Dict] = None
    ) -> DigiLockerError:
        """
        Convert API errors to DigiLocker errors
        
        Args:
            error: Original exception
            operation: Operation that failed
            context: Additional context
            
        Returns:
            DigiLockerError
        """
        error_str = str(error).lower()
        context = context or {}
        
        # Check for authentication errors
        if "authentication" in error_str or "unauthorized" in error_str or "401" in error_str:
            return AuthenticationError(
                message="DigiLocker authentication failed. Please check your credentials and try again.",
                details={**context, "operation": operation}
            )
        
        # Check for rate limit errors
        if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
            # Try to extract retry-after from error
            retry_after = 60  # Default to 60 seconds
            return RateLimitError(
                retry_after=retry_after,
                details={**context, "operation": operation}
            )
        
        # Check for service unavailable
        if "unavailable" in error_str or "503" in error_str or "502" in error_str:
            return ServiceUnavailableError(
                message="DigiLocker service is temporarily unavailable. Please try again later.",
                details={**context, "operation": operation}
            )
        
        # Check for not found errors
        if "not found" in error_str or "404" in error_str:
            doc_id = context.get("doc_id", "unknown")
            return DocumentNotFoundError(doc_id)
        
        # Check for invalid token
        if "token" in error_str and ("invalid" in error_str or "expired" in error_str):
            return InvalidTokenError()
        
        # Generic DigiLocker error
        from .digilocker_errors import DigiLockerErrorType
        return DigiLockerError(
            message=f"DigiLocker API error during {operation}: {str(error)}",
            error_type=DigiLockerErrorType.UNKNOWN_ERROR,
            details={**context, "operation": operation, "original_error": str(error)}
        )
    
    def _record_error(self, error_type: str):
        """Record error for statistics"""
        if error_type not in self.error_stats:
            self.error_stats[error_type] = 0
        self.error_stats[error_type] += 1
    
    def get_error_statistics(self) -> Dict:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_stats.values()),
            "by_type": dict(self.error_stats)
        }
    
    def get_user_friendly_error_message(self, error: DigiLockerError) -> str:
        """
        Generate user-friendly error message
        
        Args:
            error: DigiLocker error
            
        Returns:
            User-friendly message
        """
        from .digilocker_errors import DigiLockerErrorType
        
        messages = {
            DigiLockerErrorType.AUTHENTICATION_FAILED: (
                "We couldn't connect to your DigiLocker account. "
                "Please check your credentials and try reconnecting."
            ),
            DigiLockerErrorType.RATE_LIMIT_EXCEEDED: (
                f"You've made too many requests to DigiLocker. "
                f"Please wait {error.retry_after} seconds before trying again."
            ),
            DigiLockerErrorType.SERVICE_UNAVAILABLE: (
                "DigiLocker service is temporarily unavailable. "
                "This is usually temporary - please try again in a few minutes."
            ),
            DigiLockerErrorType.DOCUMENT_NOT_FOUND: (
                "The requested document could not be found in your DigiLocker account. "
                "It may have been removed or you may not have access to it."
            ),
            DigiLockerErrorType.INVALID_TOKEN: (
                "Your DigiLocker session has expired. "
                "Please reconnect your account to continue."
            ),
            DigiLockerErrorType.NETWORK_ERROR: (
                "We're having trouble connecting to DigiLocker. "
                "Please check your internet connection and try again."
            ),
            DigiLockerErrorType.UNKNOWN_ERROR: (
                "An unexpected error occurred while accessing DigiLocker. "
                "Please try again or contact support if the problem persists."
            )
        }
        
        return messages.get(error.error_type, error.message)
