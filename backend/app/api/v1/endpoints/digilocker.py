"""
DigiLocker Integration API Endpoints
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.services.digilocker_auth import DigiLockerAuthenticator
from app.services.digilocker_client_enhanced import EnhancedDigiLockerClient
from app.services.digilocker_errors import (
    DigiLockerError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError
)
from app.services.digilocker_retry import RetryConfig
from app.services.encryption_service import EncryptionService
from app.services.document_storage import document_storage
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
encryption_service = EncryptionService()
authenticator = DigiLockerAuthenticator(
    client_id=settings.DIGILOCKER_CLIENT_ID,
    client_secret=settings.DIGILOCKER_CLIENT_SECRET,
    redirect_uri=settings.DIGILOCKER_REDIRECT_URI,
    encryption_service=encryption_service
)

# Initialize enhanced client with retry configuration
retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)
digilocker_client = EnhancedDigiLockerClient(
    authenticator=authenticator,
    retry_config=retry_config,
    rate_limit_config=(10, 60.0)  # 10 requests per minute
)


@router.get("/auth/url")
async def get_auth_url(user_id: str, scope: str = "public"):
    """
    Get DigiLocker OAuth authorization URL
    """
    try:
        result = authenticator.generate_auth_url(user_id, scope)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AuthCallbackRequest(BaseModel):
    code: str
    state: str


@router.post("/auth/callback")
async def auth_callback(request: AuthCallbackRequest):
    """
    Handle OAuth callback with error handling
    """
    try:
        result = await authenticator.exchange_code_for_token(
            code=request.code,
            state=request.state
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "authentication_failed",
                    "message": (
                        "Failed to authenticate with DigiLocker. "
                        "Please try again or check your credentials."
                    )
                }
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "authentication_error",
                "message": "An error occurred during authentication. Please try again."
            }
        )


@router.get("/auth/status")
async def get_auth_status(user_id: str):
    """
    Check DigiLocker authentication status
    """
    try:
        is_authenticated = authenticator.is_authenticated(user_id)
        
        token_info = None
        if is_authenticated:
            token_info = authenticator.get_token_info(user_id)
        
        return {
            "authenticated": is_authenticated,
            "token_info": token_info
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/disconnect")
async def disconnect(user_id: str):
    """
    Disconnect from DigiLocker
    """
    try:
        success = authenticator.disconnect(user_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to disconnect")
        
        return {"message": "Disconnected from DigiLocker successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(user_id: str, category: Optional[str] = None):
    """
    List documents from DigiLocker with error handling
    """
    try:
        documents = await digilocker_client.list_documents_with_retry(user_id, category)
        return {"documents": documents}
    
    except AuthenticationError as e:
        logger.error(f"Authentication error for user {user_id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": e.error_type,
                "message": digilocker_client.get_user_friendly_error_message(e),
                "details": e.details
            }
        )
    
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": e.error_type,
                "message": digilocker_client.get_user_friendly_error_message(e),
                "retry_after": e.retry_after
            }
        )
    
    except ServiceUnavailableError as e:
        logger.error(f"DigiLocker service unavailable: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": e.error_type,
                "message": digilocker_client.get_user_friendly_error_message(e)
            }
        )
    
    except DigiLockerError as e:
        logger.error(f"DigiLocker error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": e.error_type,
                "message": digilocker_client.get_user_friendly_error_message(e),
                "details": e.details
            }
        )
    
    except Exception as e:
        logger.error(f"Unexpected error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unknown_error", "message": str(e)}
        )


@router.post("/documents/{doc_id}/import")
async def import_document(user_id: str, doc_id: str):
    """
    Import a document from DigiLocker with error handling and storage integration
    """
    try:
        result = await digilocker_client.import_document_with_retry(user_id, doc_id)
        
        if result.success:
            import_data = result.data
            
            # Store the document using document_storage with DigiLocker metadata
            if "content" in import_data and "digilocker_metadata" in import_data:
                # Convert content to bytes if it's a string
                content = import_data["content"]
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                # Import to document storage with automatic categorization
                storage_result = await document_storage.import_from_digilocker(
                    user_id=int(user_id),
                    file_data=content,
                    digilocker_metadata=import_data["digilocker_metadata"]
                )
                
                # Add storage information to response
                import_data["stored"] = True
                import_data["storage_metadata"] = {
                    "category": storage_result.get("category"),
                    "s3_key": storage_result.get("s3_key"),
                    "file_size": storage_result.get("file_size")
                }
            
            return import_data
        else:
            # Import failed after retries
            error = result.error
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            if isinstance(error, AuthenticationError):
                status_code = status.HTTP_401_UNAUTHORIZED
            elif isinstance(error, RateLimitError):
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
            elif isinstance(error, ServiceUnavailableError):
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": error.error_type,
                    "message": digilocker_client.get_user_friendly_error_message(error),
                    "doc_id": doc_id
                }
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error importing document {doc_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unknown_error", "message": str(e)}
        )


class BulkImportRequest(BaseModel):
    doc_ids: List[str]


@router.post("/documents/bulk-import")
async def bulk_import(user_id: str, request: BulkImportRequest):
    """
    Import multiple documents from DigiLocker with partial import support and storage integration
    """
    try:
        result = await digilocker_client.bulk_import_with_partial_handling(
            user_id,
            request.doc_ids,
            continue_on_error=True
        )
        
        # Store each successfully imported document
        stored_count = 0
        for doc in result.get("successful", []):
            try:
                if "content" in doc and "digilocker_metadata" in doc:
                    content = doc["content"]
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    
                    await document_storage.import_from_digilocker(
                        user_id=int(user_id),
                        file_data=content,
                        digilocker_metadata=doc["digilocker_metadata"]
                    )
                    stored_count += 1
                    doc["stored"] = True
            except Exception as e:
                logger.error(f"Failed to store document {doc.get('doc_id')}: {str(e)}")
                doc["stored"] = False
                doc["storage_error"] = str(e)
        
        # Determine response status based on results
        if len(result["failed"]) == 0:
            # All succeeded
            response_status = status.HTTP_200_OK
        elif len(result["successful"]) == 0:
            # All failed
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            # Partial success
            response_status = status.HTTP_207_MULTI_STATUS
        
        return {
            "status": "completed" if len(result["failed"]) == 0 else "partial",
            "total": result["total"],
            "successful_count": len(result["successful"]),
            "failed_count": len(result["failed"]),
            "stored_count": stored_count,
            "successful": result["successful"],
            "failed": result["failed"],
            "message": (
                f"Successfully imported {len(result['successful'])} of {result['total']} documents. "
                f"{stored_count} stored. {len(result['failed'])} failed."
            ) if result["partial_success"] else None
        }
    
    except AuthenticationError as e:
        logger.error(f"Authentication error during bulk import: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": e.error_type,
                "message": digilocker_client.get_user_friendly_error_message(e)
            }
        )
    
    except Exception as e:
        logger.error(f"Unexpected error during bulk import: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unknown_error", "message": str(e)}
        )


@router.post("/sync")
async def sync_documents(user_id: str, auto_import: bool = False):
    """
    Sync documents from DigiLocker with comprehensive error handling
    """
    try:
        sync_id = await digilocker_client.sync_documents_with_error_handling(
            user_id,
            auto_import
        )
        
        # Get sync status
        sync_status = digilocker_client.get_sync_status(sync_id)
        
        return {
            "sync_id": sync_id,
            "status": sync_status
        }
    
    except Exception as e:
        logger.error(f"Unexpected error during sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unknown_error", "message": str(e)}
        )


@router.get("/sync/{sync_id}/status")
async def get_sync_status(sync_id: str):
    """
    Get sync operation status
    """
    try:
        status = digilocker_client.get_sync_status(sync_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Sync operation not found")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/history")
async def get_sync_history(user_id: str, limit: int = 10):
    """
    Get sync history for user
    """
    try:
        history = digilocker_client.get_sync_history(user_id, limit)
        return {"history": history}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/schedule")
async def schedule_auto_sync(user_id: str, interval_hours: int = 24):
    """
    Schedule automatic sync
    """
    try:
        schedule = digilocker_client.schedule_auto_sync(user_id, interval_hours)
        return schedule
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/error-stats")
async def get_error_statistics():
    """
    Get DigiLocker error statistics
    """
    try:
        stats = digilocker_client.get_error_statistics()
        return {
            "statistics": stats,
            "message": "Error statistics for DigiLocker operations"
        }
    
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unknown_error", "message": str(e)}
        )
