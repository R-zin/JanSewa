"""
DigiLocker Client Service

Handles document retrieval, import, and sync operations with DigiLocker API.
"""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
import hashlib
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
from .digilocker_auth import DigiLockerAuthenticator


class DocumentCategory(str, Enum):
    """DigiLocker document categories"""
    AADHAAR = "aadhaar"
    PAN = "pan"
    DRIVING_LICENSE = "driving_license"
    VOTER_ID = "voter_id"
    EDUCATIONAL = "educational"
    VEHICLE = "vehicle"
    INSURANCE = "insurance"
    OTHER = "other"


class ValidationStatus(str, Enum):
    """Document validation status"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    FAILED = "failed"


class ValidationError(BaseModel):
    """Validation error details"""
    error_code: str
    error_message: str
    timestamp: datetime


class DigiLockerDocument(BaseModel):
    """Represents a document in DigiLocker"""
    doc_id: str
    doc_name: str
    doc_type: str
    issuer: str
    issue_date: Optional[datetime]
    category: DocumentCategory
    size_bytes: int
    mime_type: str
    uri: str
    signature: Optional[str] = None  # Digital signature
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_error: Optional[ValidationError] = None


class SyncStatus(str, Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncHistory(BaseModel):
    """Represents a sync operation"""
    sync_id: str
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: SyncStatus
    documents_synced: int
    documents_failed: int
    error_message: Optional[str] = None


class DigiLockerClient:
    """
    Client for interacting with DigiLocker API.
    Handles document listing, import, and synchronization.
    """
    
    def __init__(self, authenticator: DigiLockerAuthenticator):
        """
        Initialize DigiLocker client
        
        Args:
            authenticator: DigiLocker authentication service
        """
        self.authenticator = authenticator
        self.api_base_url = "https://digilocker.meity.gov.in/public/oauth2/1"
        self.sync_history: Dict[str, SyncHistory] = {}
        self.user_documents: Dict[str, List[DigiLockerDocument]] = {}
        
        # In production, this would be the actual DigiLocker public key
        # For now, generate a test key pair
        self._init_test_keys()
    
    async def list_documents(
        self,
        user_id: str,
        category: Optional[DocumentCategory] = None
    ) -> List[DigiLockerDocument]:
        """
        List documents from user's DigiLocker
        
        Args:
            user_id: User ID
            category: Optional filter by category
            
        Returns:
            List of documents with metadata
        """
        # Get access token
        access_token = self.authenticator.get_access_token(user_id)
        if not access_token:
            raise Exception("User not authenticated with DigiLocker")
        
        # In production, make actual API call to DigiLocker
        # For now, simulate document list
        documents = self._simulate_document_list(user_id)
        
        # Filter by category if specified
        if category:
            documents = [d for d in documents if d.category == category]
        
        # Cache documents
        self.user_documents[user_id] = documents
        
        return documents
    
    def _simulate_document_list(self, user_id: str) -> List[DigiLockerDocument]:
        """Simulate DigiLocker document list (for development)"""
        # Generate test signatures for simulated documents
        aadhaar_content = b"<simulated_aadhaar_content>"
        pan_content = b"<simulated_pan_content>"
        dl_content = b"<simulated_dl_content>"
        
        return [
            DigiLockerDocument(
                doc_id="dl_aadhaar_001",
                doc_name="Aadhaar Card",
                doc_type="ADHAR",
                issuer="UIDAI",
                issue_date=datetime(2020, 1, 15),
                category=DocumentCategory.AADHAAR,
                size_bytes=245000,
                mime_type="application/pdf",
                uri="digilocker://ADHAR-UIDAI/12345",
                signature=self._generate_test_signature(aadhaar_content),
                validation_status=ValidationStatus.PENDING
            ),
            DigiLockerDocument(
                doc_id="dl_pan_001",
                doc_name="PAN Card",
                doc_type="PANCR",
                issuer="Income Tax Department",
                issue_date=datetime(2019, 6, 10),
                category=DocumentCategory.PAN,
                size_bytes=180000,
                mime_type="application/pdf",
                uri="digilocker://PANCR-NSDL/67890",
                signature=self._generate_test_signature(pan_content),
                validation_status=ValidationStatus.PENDING
            ),
            DigiLockerDocument(
                doc_id="dl_dl_001",
                doc_name="Driving License",
                doc_type="DRVLC",
                issuer="Transport Department",
                issue_date=datetime(2021, 3, 20),
                category=DocumentCategory.DRIVING_LICENSE,
                size_bytes=320000,
                mime_type="application/pdf",
                uri="digilocker://DRVLC-MH/11223",
                signature=self._generate_test_signature(dl_content),
                validation_status=ValidationStatus.PENDING
            )
        ]
    
    async def import_document(
        self,
        user_id: str,
        doc_id: str
    ) -> Dict:
        """
        Import a single document from DigiLocker with validation
        
        Args:
            user_id: User ID
            doc_id: DigiLocker document ID
            
        Returns:
            Import result with document data and validation status
            
        Raises:
            Exception: If validation fails or document not found
        """
        # Get access token
        access_token = self.authenticator.get_access_token(user_id)
        if not access_token:
            raise Exception("User not authenticated with DigiLocker")
        
        # Find document in cached list
        documents = self.user_documents.get(user_id, [])
        document = next((d for d in documents if d.doc_id == doc_id), None)
        
        if not document:
            raise Exception(f"Document {doc_id} not found")
        
        # In production, make actual API call to fetch document content
        # For now, simulate document content and signature
        document_content = f"<simulated_content_for_{doc_id}>".encode()
        
        # Generate test signature for development
        test_signature = self._generate_test_signature(document_content)
        document.signature = test_signature
        
        # Validate document authenticity
        try:
            validation_status = self.validate_document_authenticity(
                document,
                document_content
            )
            
            # If validation failed, reject import
            if validation_status != ValidationStatus.VALID:
                error_msg = "Document validation failed"
                if document.validation_error:
                    error_msg = f"{error_msg}: {document.validation_error.error_message}"
                
                raise Exception(error_msg)
            
        except Exception as e:
            # Handle validation failures
            document.validation_status = ValidationStatus.FAILED
            document.validation_error = ValidationError(
                error_code="VALIDATION_FAILED",
                error_message=str(e),
                timestamp=datetime.now()
            )
            raise Exception(f"Document validation failed: {str(e)}")
        
        # Document is valid, proceed with import
        
        # Prepare DigiLocker metadata for storage
        digilocker_metadata = {
            "doc_id": document.doc_id,
            "doc_name": document.doc_name,
            "doc_type": document.doc_type,
            "issuer": document.issuer,
            "issue_date": document.issue_date.isoformat() if document.issue_date else None,
            "category": document.category.value,
            "size_bytes": document.size_bytes,
            "mime_type": document.mime_type,
            "uri": document.uri,
            "imported_at": datetime.now().isoformat()
        }
        
        return {
            "doc_id": doc_id,
            "doc_name": document.doc_name,
            "category": document.category,
            "issuer": document.issuer,
            "size_bytes": document.size_bytes,
            "mime_type": document.mime_type,
            "imported_at": datetime.now().isoformat(),
            "source": "digilocker",
            "validation_status": document.validation_status,
            "signature_verified": True,
            "digilocker_metadata": digilocker_metadata,
            "content": document_content.decode()
        }
    
    async def bulk_import(
        self,
        user_id: str,
        doc_ids: List[str]
    ) -> Dict:
        """
        Import multiple documents from DigiLocker with validation
        
        Args:
            user_id: User ID
            doc_ids: List of document IDs to import
            
        Returns:
            Bulk import results with validation details
        """
        results = {
            "total": len(doc_ids),
            "successful": [],
            "failed": []
        }
        
        for doc_id in doc_ids:
            try:
                result = await self.import_document(user_id, doc_id)
                results["successful"].append(result)
            except Exception as e:
                error_message = str(e)
                error_code = "IMPORT_FAILED"
                
                # Extract validation error details if available
                if "validation failed" in error_message.lower():
                    error_code = "VALIDATION_FAILED"
                
                results["failed"].append({
                    "doc_id": doc_id,
                    "error_code": error_code,
                    "error": error_message
                })
        
        return results
    
    async def sync_documents(
        self,
        user_id: str,
        auto_import: bool = False
    ) -> str:
        """
        Sync documents from DigiLocker
        
        Args:
            user_id: User ID
            auto_import: Whether to automatically import new documents
            
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
            # List documents from DigiLocker
            documents = await self.list_documents(user_id)
            
            # If auto_import, import all documents
            if auto_import:
                doc_ids = [d.doc_id for d in documents]
                import_results = await self.bulk_import(user_id, doc_ids)
                
                sync_record.documents_synced = len(import_results["successful"])
                sync_record.documents_failed = len(import_results["failed"])
            else:
                sync_record.documents_synced = len(documents)
            
            sync_record.status = SyncStatus.COMPLETED
            sync_record.completed_at = datetime.now()
            
        except Exception as e:
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.now()
        
        return sync_id
    
    def get_sync_status(self, sync_id: str) -> Optional[Dict]:
        """
        Get status of a sync operation
        
        Args:
            sync_id: Sync operation ID
            
        Returns:
            Sync status information
        """
        if sync_id not in self.sync_history:
            return None
        
        sync_record = self.sync_history[sync_id]
        
        status_info = {
            "sync_id": sync_record.sync_id,
            "user_id": sync_record.user_id,
            "status": sync_record.status,
            "started_at": sync_record.started_at.isoformat(),
            "documents_synced": sync_record.documents_synced,
            "documents_failed": sync_record.documents_failed
        }
        
        if sync_record.completed_at:
            status_info["completed_at"] = sync_record.completed_at.isoformat()
            status_info["duration_seconds"] = (
                sync_record.completed_at - sync_record.started_at
            ).total_seconds()
        
        if sync_record.error_message:
            status_info["error"] = sync_record.error_message
        
        return status_info
    
    def get_sync_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get sync history for user
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            
        Returns:
            List of sync history records
        """
        user_syncs = [
            s for s in self.sync_history.values()
            if s.user_id == user_id
        ]
        
        # Sort by started_at descending
        user_syncs.sort(key=lambda x: x.started_at, reverse=True)
        
        return [
            {
                "sync_id": s.sync_id,
                "started_at": s.started_at.isoformat(),
                "status": s.status,
                "documents_synced": s.documents_synced
            }
            for s in user_syncs[:limit]
        ]
    
    def schedule_auto_sync(
        self,
        user_id: str,
        interval_hours: int = 24
    ) -> Dict:
        """
        Schedule automatic sync for user
        
        Args:
            user_id: User ID
            interval_hours: Sync interval in hours
            
        Returns:
            Schedule information
        """
        # In production, this would integrate with a task scheduler
        next_sync = datetime.now().timestamp() + (interval_hours * 3600)
        
        return {
            "user_id": user_id,
            "auto_sync_enabled": True,
            "interval_hours": interval_hours,
            "next_sync_at": datetime.fromtimestamp(next_sync).isoformat()
        }
    
    def get_document_metadata(
        self,
        user_id: str,
        doc_id: str
    ) -> Optional[Dict]:
        """
        Get metadata for a specific document including validation status
        
        Args:
            user_id: User ID
            doc_id: Document ID
            
        Returns:
            Document metadata with validation information
        """
        documents = self.user_documents.get(user_id, [])
        document = next((d for d in documents if d.doc_id == doc_id), None)
        
        if not document:
            return None
        
        metadata = {
            "doc_id": document.doc_id,
            "doc_name": document.doc_name,
            "doc_type": document.doc_type,
            "issuer": document.issuer,
            "issue_date": document.issue_date.isoformat() if document.issue_date else None,
            "category": document.category,
            "size_bytes": document.size_bytes,
            "mime_type": document.mime_type,
            "validation_status": document.validation_status,
            "has_signature": document.signature is not None
        }
        
        # Include validation error if present
        if document.validation_error:
            metadata["validation_error"] = {
                "error_code": document.validation_error.error_code,
                "error_message": document.validation_error.error_message,
                "timestamp": document.validation_error.timestamp.isoformat()
            }
        
        return metadata
    
    def categorize_document(self, doc_type: str, issuer: str) -> DocumentCategory:
        """
        Automatically categorize document based on type and issuer
        
        Args:
            doc_type: DigiLocker document type code
            issuer: Document issuer
            
        Returns:
            Document category
        """
        doc_type_upper = doc_type.upper()
        issuer_lower = issuer.lower()
        
        if "ADHAR" in doc_type_upper or "uidai" in issuer_lower:
            return DocumentCategory.AADHAAR
        elif "PAN" in doc_type_upper or "income tax" in issuer_lower:
            return DocumentCategory.PAN
        elif "DRVLC" in doc_type_upper or "DL" in doc_type_upper or "transport" in issuer_lower:
            return DocumentCategory.DRIVING_LICENSE
        elif "VOTER" in doc_type_upper or "election" in issuer_lower:
            return DocumentCategory.VOTER_ID
        elif "EDU" in doc_type_upper or "university" in issuer_lower or "board" in issuer_lower:
            return DocumentCategory.EDUCATIONAL
        elif "VAHAN" in doc_type_upper or "vehicle" in issuer_lower:
            return DocumentCategory.VEHICLE
        elif "INSURANCE" in doc_type_upper or "insurance" in issuer_lower:
            return DocumentCategory.INSURANCE
        else:
            return DocumentCategory.OTHER
    
    def _init_test_keys(self):
        """Initialize test RSA key pair for signature verification (development only)"""
        # In production, load DigiLocker's actual public key
        self.test_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.digilocker_public_key = self.test_private_key.public_key()
    
    def _generate_test_signature(self, document_content: bytes) -> str:
        """
        Generate test signature for development
        
        Args:
            document_content: Document content bytes
            
        Returns:
            Base64 encoded signature
        """
        # Create document hash
        doc_hash = hashlib.sha256(document_content).digest()
        
        # Sign with private key
        signature = self.test_private_key.sign(
            doc_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_digital_signature(
        self,
        document_content: bytes,
        signature: str,
        doc_id: str
    ) -> bool:
        """
        Verify digital signature of DigiLocker document
        
        Args:
            document_content: Document content bytes
            signature: Base64 encoded digital signature
            doc_id: Document ID for logging
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Decode signature from base64
            signature_bytes = base64.b64decode(signature)
            
            # Create document hash
            doc_hash = hashlib.sha256(document_content).digest()
            
            # Verify signature using DigiLocker public key
            self.digilocker_public_key.verify(
                signature_bytes,
                doc_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except InvalidSignature:
            print(f"Invalid signature for document {doc_id}")
            return False
        except Exception as e:
            print(f"Signature verification error for document {doc_id}: {e}")
            return False
    
    def validate_document_authenticity(
        self,
        document: DigiLockerDocument,
        document_content: bytes
    ) -> ValidationStatus:
        """
        Validate authenticity of DigiLocker document
        
        Args:
            document: DigiLocker document metadata
            document_content: Document content bytes
            
        Returns:
            Validation status
        """
        # Check if signature exists
        if not document.signature:
            document.validation_status = ValidationStatus.INVALID
            document.validation_error = ValidationError(
                error_code="MISSING_SIGNATURE",
                error_message="Document does not have a digital signature",
                timestamp=datetime.now()
            )
            return ValidationStatus.INVALID
        
        # Verify digital signature
        is_valid = self.verify_digital_signature(
            document_content,
            document.signature,
            document.doc_id
        )
        
        if not is_valid:
            document.validation_status = ValidationStatus.INVALID
            document.validation_error = ValidationError(
                error_code="INVALID_SIGNATURE",
                error_message="Digital signature verification failed",
                timestamp=datetime.now()
            )
            return ValidationStatus.INVALID
        
        # Additional authenticity checks
        # Check issuer is recognized
        if not self._is_recognized_issuer(document.issuer):
            document.validation_status = ValidationStatus.INVALID
            document.validation_error = ValidationError(
                error_code="UNRECOGNIZED_ISSUER",
                error_message=f"Issuer '{document.issuer}' is not recognized",
                timestamp=datetime.now()
            )
            return ValidationStatus.INVALID
        
        # Check document type is valid
        if not self._is_valid_document_type(document.doc_type):
            document.validation_status = ValidationStatus.INVALID
            document.validation_error = ValidationError(
                error_code="INVALID_DOCUMENT_TYPE",
                error_message=f"Document type '{document.doc_type}' is not valid",
                timestamp=datetime.now()
            )
            return ValidationStatus.INVALID
        
        # All checks passed
        document.validation_status = ValidationStatus.VALID
        document.validation_error = None
        return ValidationStatus.VALID
    
    def _is_recognized_issuer(self, issuer: str) -> bool:
        """
        Check if issuer is recognized
        
        Args:
            issuer: Issuer name
            
        Returns:
            True if recognized
        """
        recognized_issuers = [
            "UIDAI",
            "Income Tax Department",
            "Transport Department",
            "Election Commission",
            "Ministry of External Affairs",
            "NSDL",
            "CBSE",
            "State Board",
            "University"
        ]
        
        issuer_lower = issuer.lower()
        return any(
            recognized.lower() in issuer_lower
            for recognized in recognized_issuers
        )
    
    def _is_valid_document_type(self, doc_type: str) -> bool:
        """
        Check if document type is valid
        
        Args:
            doc_type: Document type code
            
        Returns:
            True if valid
        """
        valid_types = [
            "ADHAR", "PANCR", "DRVLC", "VOTER",
            "PASSPORT", "EDU", "VAHAN", "INSURANCE"
        ]
        
        doc_type_upper = doc_type.upper()
        return any(
            valid_type in doc_type_upper
            for valid_type in valid_types
        )
