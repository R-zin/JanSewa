"""
Document Storage Service with Audit Logging Integration

This module provides a wrapper around the document storage service
that automatically logs all operations to the audit log.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from app.services.document_storage import DocumentStorage
from app.services.audit_logger import AuditLogger, AuditAction
from app.models.document import DocumentCategory

logger = logging.getLogger(__name__)


class DocumentStorageWithAudit:
    """
    Document storage service with integrated audit logging
    
    This wrapper ensures all document operations are logged for compliance
    and security purposes.
    """
    
    def __init__(self, storage: DocumentStorage, audit_logger: AuditLogger):
        self.storage = storage
        self.audit_logger = audit_logger
    
    async def upload_document(
        self,
        user_id: int,
        file_data: bytes,
        file_name: str,
        document_type: str,
        category: DocumentCategory,
        expiration_date: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload and encrypt document with audit logging
        
        Args:
            user_id: ID of the user uploading the document
            file_data: Raw file bytes
            file_name: Name of the file
            document_type: Type of document
            category: Document category
            expiration_date: Optional expiration date
            ip_address: IP address of the request
            user_agent: User agent string
        
        Returns:
            Document metadata dictionary
        """
        result = "failure"
        document_id = None
        error_details = None
        
        try:
            # Perform upload
            metadata = await self.storage.upload_document(
                user_id=user_id,
                file_data=file_data,
                file_name=file_name,
                document_type=document_type,
                category=category,
                expiration_date=expiration_date
            )
            
            result = "success"
            document_id = metadata.get("document_id")
            
            # Log successful upload
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.UPLOAD,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "file_name": file_name,
                    "document_type": document_type,
                    "category": category.value if hasattr(category, 'value') else str(category),
                    "file_size": len(file_data),
                    "has_expiration": expiration_date is not None
                }
            )
            
            return metadata
            
        except Exception as e:
            error_details = str(e)
            logger.error(f"Document upload failed: {error_details}")
            
            # Log failed upload
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.UPLOAD,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "file_name": file_name,
                    "error": error_details
                }
            )
            
            raise
    
    async def retrieve_document(
        self,
        user_id: int,
        document_id: int,
        s3_key: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bytes:
        """
        Retrieve and decrypt document with audit logging
        
        Args:
            user_id: ID of the user retrieving the document
            document_id: ID of the document
            s3_key: S3 storage key
            ip_address: IP address of the request
            user_agent: User agent string
        
        Returns:
            Decrypted document bytes
        """
        result = "failure"
        error_details = None
        
        try:
            # Perform retrieval
            document_data = await self.storage.retrieve_document(
                user_id=user_id,
                s3_key=s3_key
            )
            
            result = "success"
            
            # Log successful retrieval
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.RETRIEVE,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "s3_key": s3_key,
                    "size": len(document_data)
                }
            )
            
            return document_data
            
        except Exception as e:
            error_details = str(e)
            logger.error(f"Document retrieval failed: {error_details}")
            
            # Log failed retrieval
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.RETRIEVE,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "s3_key": s3_key,
                    "error": error_details
                }
            )
            
            raise
    
    async def delete_document(
        self,
        user_id: int,
        document_id: int,
        s3_key: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Delete document with audit logging
        
        Args:
            user_id: ID of the user deleting the document
            document_id: ID of the document
            s3_key: S3 storage key
            ip_address: IP address of the request
            user_agent: User agent string
        
        Returns:
            True if deletion was successful
        """
        result = "failure"
        error_details = None
        
        try:
            # Perform deletion
            success = await self.storage.delete_document(
                user_id=user_id,
                s3_key=s3_key
            )
            
            result = "success" if success else "failure"
            
            # Log deletion
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.DELETE,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "s3_key": s3_key
                }
            )
            
            return success
            
        except Exception as e:
            error_details = str(e)
            logger.error(f"Document deletion failed: {error_details}")
            
            # Log failed deletion
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.DELETE,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "s3_key": s3_key,
                    "error": error_details
                }
            )
            
            raise
    
    async def preview_document(
        self,
        user_id: int,
        document_id: int,
        s3_key: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bytes:
        """
        Preview document with audit logging
        
        Args:
            user_id: ID of the user previewing the document
            document_id: ID of the document
            s3_key: S3 storage key
            ip_address: IP address of the request
            user_agent: User agent string
        
        Returns:
            Preview data (could be thumbnail or first page)
        """
        result = "failure"
        
        try:
            # For now, preview is same as retrieve
            # In production, this would generate a thumbnail or preview
            document_data = await self.storage.retrieve_document(
                user_id=user_id,
                s3_key=s3_key
            )
            
            result = "success"
            
            # Log preview
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.PREVIEW,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "s3_key": s3_key
                }
            )
            
            return document_data
            
        except Exception as e:
            logger.error(f"Document preview failed: {str(e)}")
            
            # Log failed preview
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.PREVIEW,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "s3_key": s3_key,
                    "error": str(e)
                }
            )
            
            raise
    
    async def update_document(
        self,
        user_id: int,
        document_id: int,
        update_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Update document metadata with audit logging
        
        Args:
            user_id: ID of the user updating the document
            document_id: ID of the document
            update_data: Dictionary of fields to update
            ip_address: IP address of the request
            user_agent: User agent string
        
        Returns:
            True if update was successful
        """
        result = "success"
        
        try:
            # Log update (actual update would be in database layer)
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.UPDATE,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "updated_fields": list(update_data.keys())
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Document update failed: {str(e)}")
            
            # Log failed update
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.UPDATE,
                result="failure",
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "error": str(e)
                }
            )
            
            raise
    
    async def share_document(
        self,
        user_id: int,
        document_id: int,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Share document with automation agent with audit logging
        
        Args:
            user_id: ID of the user sharing the document
            document_id: ID of the document
            session_id: Automation session ID
            ip_address: IP address of the request
            user_agent: User agent string
        
        Returns:
            True if sharing was successful
        """
        result = "success"
        
        try:
            # Log share operation
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.SHARE,
                result=result,
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "session_id": session_id,
                    "shared_with": "automation_agent"
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Document sharing failed: {str(e)}")
            
            # Log failed share
            await self.audit_logger.log_operation(
                user_id=user_id,
                action=AuditAction.SHARE,
                result="failure",
                document_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "session_id": session_id,
                    "error": str(e)
                }
            )
            
            raise


def create_document_storage_with_audit(
    storage: DocumentStorage,
    db_session: Session
) -> DocumentStorageWithAudit:
    """
    Factory function to create a DocumentStorageWithAudit instance
    
    Args:
        storage: DocumentStorage instance
        db_session: SQLAlchemy database session
    
    Returns:
        Configured DocumentStorageWithAudit instance
    """
    from app.services.audit_logger import create_audit_logger
    
    audit_logger = create_audit_logger(db_session)
    return DocumentStorageWithAudit(storage, audit_logger)
