from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentCategory(str, Enum):
    """Document category enumeration"""
    IDENTITY = "identity"
    ADDRESS_PROOF = "address_proof"
    INCOME = "income"
    EDUCATION = "education"
    VEHICLE = "vehicle"
    CERTIFICATE = "certificate"
    OTHER = "other"


class DocumentMetadata(BaseModel):
    """Document metadata"""
    document_type: str
    upload_date: datetime
    expiration_date: Optional[datetime] = None
    file_size: int
    file_format: str
    is_digilocker: bool = False
    digilocker_metadata: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    extraction_confidence: Optional[float] = None


class DocumentSummary(BaseModel):
    """Document summary for listings"""
    document_id: int
    document_name: str
    document_type: str
    category: DocumentCategory
    upload_date: datetime
    expiration_date: Optional[datetime] = None
    file_size: int
    is_digilocker: bool
    extraction_status: str


class StorageQuota(BaseModel):
    """Storage quota information"""
    used_mb: float
    total_mb: float
    available_mb: float
    document_count: int


class EncryptedDocument(BaseModel):
    """Encrypted document model"""
    document_id: int
    encrypted_data: bytes
    encryption_metadata: Dict[str, Any]
