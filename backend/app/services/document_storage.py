from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import uuid
import logging

from app.services.aws_service import aws_service
from app.services.encryption_service import encryption_service
from app.services.malware_scanner import malware_scanner, ThreatLevel
from app.models.document import DocumentMetadata, DocumentSummary, StorageQuota, DocumentCategory

logger = logging.getLogger(__name__)


class ExpirationWarning:
    """Document expiration warning"""
    def __init__(self, document_id: int, document_name: str, expiration_date: datetime, days_until_expiration: int):
        self.document_id = document_id
        self.document_name = document_name
        self.expiration_date = expiration_date
        self.days_until_expiration = days_until_expiration
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "days_until_expiration": self.days_until_expiration
        }


class DocumentStorage:
    """Document storage service with encryption and AWS S3"""
    
    def __init__(self):
        self.max_size_mb = 10
        self.max_storage_per_user_mb = 100
        self.expiration_warning_days = 30  # Warn when document expires within 30 days
        self.archive_after_expiration_days = 90  # Archive 90 days after expiration
    
    async def upload_document(
        self,
        user_id: int,
        file_data: bytes,
        file_name: str,
        document_type: str,
        category: DocumentCategory,
        expiration_date: Optional[datetime] = None,
        is_digilocker: bool = False,
        digilocker_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload and encrypt document"""
        
        # Validate file size
        file_size_mb = len(file_data) / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            raise ValueError(f"File size exceeds {self.max_size_mb}MB limit")
        
        # Check user storage quota
        # (Simplified - would check actual usage from database)
        
        # Scan for malware before processing
        logger.info(f"Scanning document for malware: {file_name}")
        scan_result = await malware_scanner.scan_file(file_data, file_name)
        
        if not scan_result.is_safe:
            logger.warning(f"Malware scan failed for {file_name}: {scan_result.threat_level}")
            raise ValueError(
                f"Document failed malware scan. "
                f"Threat level: {scan_result.threat_level}. "
                f"Details: {scan_result.details}"
            )
        
        logger.info(f"Malware scan passed for {file_name} (scan time: {scan_result.scan_duration_ms:.2f}ms)")
        
        # Encrypt document
        encrypted_data = encryption_service.encrypt_document(file_data, user_id)
        
        # Generate S3 key
        s3_key = f"users/{user_id}/documents/{uuid.uuid4()}_{file_name}"
        
        # Upload to S3
        success = await aws_service.upload_document(encrypted_data, s3_key)
        
        if not success:
            raise Exception("Failed to upload document to S3")
        
        metadata = {
            "document_type": document_type,
            "category": category,
            "file_name": file_name,
            "s3_key": s3_key,
            "file_size": len(file_data),
            "upload_date": datetime.utcnow(),
            "expiration_date": expiration_date,
            "expiration_status": self.get_document_expiration_status(expiration_date),
            "scan_result": scan_result.to_dict(),
            "is_digilocker": is_digilocker,
            "digilocker_metadata": digilocker_metadata
        }
        
        logger.info(f"Document uploaded for user {user_id}: {file_name} (DigiLocker: {is_digilocker})")
        return metadata
    
    async def retrieve_document(
        self,
        user_id: int,
        s3_key: str
    ) -> bytes:
        """Retrieve and decrypt document"""
        # Download from S3
        encrypted_data = await aws_service.download_document(s3_key)
        
        # Decrypt
        decrypted_data = encryption_service.decrypt_document(encrypted_data, user_id)
        
        logger.info(f"Document retrieved for user {user_id}")
        return decrypted_data
    
    async def delete_document(
        self,
        user_id: int,
        s3_key: str
    ) -> bool:
        """Delete document from storage"""
        success = await aws_service.delete_document(s3_key)
        logger.info(f"Document deleted for user {user_id}: {s3_key}")
        return success
    
    def get_storage_quota(self, user_id: int, used_mb: float) -> StorageQuota:
        """Get storage quota information"""
        return StorageQuota(
            used_mb=used_mb,
            total_mb=self.max_storage_per_user_mb,
            available_mb=self.max_storage_per_user_mb - used_mb,
            document_count=0  # Would be fetched from database
        )
    
    def is_document_expired(self, expiration_date: Optional[datetime]) -> bool:
        """Check if a document is expired"""
        if not expiration_date:
            return False
        
        now = datetime.utcnow()
        return now > expiration_date
    
    def get_days_until_expiration(self, expiration_date: Optional[datetime]) -> Optional[int]:
        """Calculate days until document expiration"""
        if not expiration_date:
            return None
        
        now = datetime.utcnow()
        delta = expiration_date - now
        return delta.days
    
    def should_show_expiration_warning(self, expiration_date: Optional[datetime]) -> bool:
        """Check if expiration warning should be shown"""
        if not expiration_date:
            return False
        
        days_until = self.get_days_until_expiration(expiration_date)
        if days_until is None:
            return False
        
        # Show warning if expires within warning period and not yet expired
        return 0 <= days_until <= self.expiration_warning_days
    
    def should_archive_document(self, expiration_date: Optional[datetime]) -> bool:
        """Check if document should be archived (expired for 90+ days)"""
        if not expiration_date:
            return False
        
        now = datetime.utcnow()
        days_since_expiration = (now - expiration_date).days
        
        # Archive if expired for more than archive_after_expiration_days
        return days_since_expiration >= self.archive_after_expiration_days
    
    def generate_expiration_warning(
        self,
        document_id: int,
        document_name: str,
        expiration_date: datetime
    ) -> ExpirationWarning:
        """Generate expiration warning for a document"""
        days_until = self.get_days_until_expiration(expiration_date)
        
        return ExpirationWarning(
            document_id=document_id,
            document_name=document_name,
            expiration_date=expiration_date,
            days_until_expiration=days_until if days_until is not None else 0
        )
    
    def get_expiration_warnings(self, documents: List[Dict[str, Any]]) -> List[ExpirationWarning]:
        """Get expiration warnings for a list of documents"""
        warnings = []
        
        for doc in documents:
            expiration_date = doc.get("expiration_date")
            if expiration_date and self.should_show_expiration_warning(expiration_date):
                warning = self.generate_expiration_warning(
                    document_id=doc.get("id", 0),
                    document_name=doc.get("file_name", "Unknown"),
                    expiration_date=expiration_date
                )
                warnings.append(warning)
        
        return warnings
    
    async def archive_expired_document(
        self,
        user_id: int,
        document_id: int,
        s3_key: str
    ) -> bool:
        """Archive an expired document by moving it to archive location"""
        try:
            # Generate archive key
            archive_key = s3_key.replace("/documents/", "/archived/")
            
            # Download document from current location
            encrypted_data = await aws_service.download_document(s3_key)
            
            # Upload to archive location
            success = await aws_service.upload_document(encrypted_data, archive_key)
            
            if success:
                # Delete from original location
                await aws_service.delete_document(s3_key)
                logger.info(f"Document archived for user {user_id}: {document_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to archive document {document_id}: {str(e)}")
            return False
    
    async def process_expired_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process expired documents for archival"""
        archived_count = 0
        failed_count = 0
        
        for doc in documents:
            expiration_date = doc.get("expiration_date")
            
            if self.should_archive_document(expiration_date):
                success = await self.archive_expired_document(
                    user_id=doc.get("user_id"),
                    document_id=doc.get("id"),
                    s3_key=doc.get("s3_key")
                )
                
                if success:
                    archived_count += 1
                else:
                    failed_count += 1
        
        logger.info(f"Archived {archived_count} documents, {failed_count} failures")
        
        return {
            "archived_count": archived_count,
            "failed_count": failed_count,
            "total_processed": archived_count + failed_count
        }
    
    def get_document_expiration_status(self, expiration_date: Optional[datetime]) -> str:
        """Get expiration status for a document"""
        if not expiration_date:
            return "no_expiration"
        
        if self.is_document_expired(expiration_date):
            days_since = (datetime.utcnow() - expiration_date).days
            if days_since >= self.archive_after_expiration_days:
                return "archived"
            return "expired"
        
        if self.should_show_expiration_warning(expiration_date):
            return "expiring_soon"
        
        return "valid"
    
    def update_document_metadata_with_expiration_status(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update document metadata with current expiration status"""
        expiration_date = metadata.get("expiration_date")
        metadata["expiration_status"] = self.get_document_expiration_status(expiration_date)
        return metadata
    
    def assign_category_from_digilocker_metadata(self, digilocker_metadata: Dict[str, Any]) -> DocumentCategory:
        """
        Automatically assign document category based on DigiLocker metadata
        
        Args:
            digilocker_metadata: DigiLocker document metadata containing doc_type, issuer, etc.
            
        Returns:
            Appropriate DocumentCategory
        """
        if not digilocker_metadata:
            return DocumentCategory.OTHER
        
        doc_type = digilocker_metadata.get("doc_type", "").upper()
        issuer = digilocker_metadata.get("issuer", "").lower()
        doc_name = digilocker_metadata.get("doc_name", "").lower()
        
        # Aadhaar documents
        if "ADHAR" in doc_type or "aadhaar" in doc_name or "uidai" in issuer:
            return DocumentCategory.IDENTITY
        
        # PAN card
        if "PAN" in doc_type or "pan" in doc_name or "income tax" in issuer:
            return DocumentCategory.IDENTITY
        
        # Vehicle documents (check before driving license to avoid false matches)
        if "VAHAN" in doc_type or "vehicle" in doc_name or ("registration" in doc_name and ("vehicle" in doc_name or "rc" in doc_name)):
            return DocumentCategory.VEHICLE
        
        # Driving License
        if "DRVLC" in doc_type or "DL" in doc_type or "driving" in doc_name or ("license" in doc_name and "driving" in doc_name):
            return DocumentCategory.IDENTITY
        
        # Voter ID
        if "VOTER" in doc_type or "voter" in doc_name or "election" in issuer:
            return DocumentCategory.IDENTITY
        
        # Income/Caste/Domicile certificates (check before educational)
        if "income" in doc_name or "caste" in doc_name or "domicile" in doc_name:
            return DocumentCategory.CERTIFICATE
        
        # Educational certificates
        if "EDU" in doc_type or "university" in issuer or "board" in issuer or "degree" in doc_name or "marksheet" in doc_name or "diploma" in doc_name:
            return DocumentCategory.EDUCATION
        
        # Address proof documents
        if "address" in doc_name or "utility" in doc_name or "bill" in doc_name:
            return DocumentCategory.ADDRESS_PROOF
        
        return DocumentCategory.OTHER
    
    async def import_from_digilocker(
        self,
        user_id: int,
        file_data: bytes,
        digilocker_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Import a document from DigiLocker with automatic tagging and categorization
        
        Args:
            user_id: User ID
            file_data: Document file content
            digilocker_metadata: Metadata from DigiLocker including doc_type, issuer, issue_date, etc.
            
        Returns:
            Document metadata
        """
        # Extract information from DigiLocker metadata
        file_name = digilocker_metadata.get("doc_name", "digilocker_document.pdf")
        document_type = digilocker_metadata.get("doc_type", "unknown")
        
        # Automatically assign category based on DigiLocker metadata
        category = self.assign_category_from_digilocker_metadata(digilocker_metadata)
        
        # Extract expiration date if available
        expiration_date = None
        if "expiry_date" in digilocker_metadata:
            expiration_date = digilocker_metadata.get("expiry_date")
        
        # Upload document with DigiLocker tagging
        metadata = await self.upload_document(
            user_id=user_id,
            file_data=file_data,
            file_name=file_name,
            document_type=document_type,
            category=category,
            expiration_date=expiration_date,
            is_digilocker=True,
            digilocker_metadata=digilocker_metadata
        )
        
        logger.info(
            f"Imported DigiLocker document for user {user_id}: {file_name} "
            f"(category: {category}, issuer: {digilocker_metadata.get('issuer')})"
        )
        
        return metadata


document_storage = DocumentStorage()
