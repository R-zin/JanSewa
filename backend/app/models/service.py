from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class ServiceCategory(str, Enum):
    """Service category enumeration"""
    AADHAAR = "aadhaar"
    DATA_ACCESS = "data_access"
    RECORD_MODIFICATION = "record_modification"
    STATUS_INQUIRY = "status_inquiry"
    IDENTITY_CARD = "identity_card"
    CERTIFICATE = "certificate"


class ProcessingTime(BaseModel):
    """Processing time information"""
    minimum: str
    maximum: str
    typical: str
    factors: List[str] = []


class ContactInfo(BaseModel):
    """Contact information for government offices"""
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    helpline: Optional[str] = None


class AlternativeDocument(BaseModel):
    """Alternative document option"""
    document_id: str
    document_name: str
    conditions: str


class DocumentRequirement(BaseModel):
    """Document requirement specification"""
    document_id: str
    document_name: str
    official_name: str
    required: bool
    accepts_copies: bool
    requires_attestation: bool
    requires_notarization: bool
    format: Optional[str] = None
    validity_period: Optional[str] = None
    alternatives: List[AlternativeDocument] = []
    obtainment_guidance: str


class ValidationRule(BaseModel):
    """Validation rule for eligibility criteria"""
    rule_type: str
    parameters: Dict = {}


class EligibilityCriterion(BaseModel):
    """Eligibility criterion specification"""
    criterion_id: str
    description: str
    required: bool
    validation_rule: ValidationRule
    failure_message: str
    alternatives: List[str] = []



class ServiceStep(BaseModel):
    """Service step specification"""
    step_number: int
    description: str
    requires_in_person: bool
    online_available: bool
    estimated_duration: str
    notes: Optional[str] = None


class ServiceGuide(BaseModel):
    """Complete service guide"""
    service_id: str
    service_name: str
    category: ServiceCategory
    description: str
    steps: List[ServiceStep]
    eligibility_criteria: List[EligibilityCriterion]
    document_requirements: List[DocumentRequirement]
    processing_time: ProcessingTime
    official_portal_url: str
    contact_info: ContactInfo
    last_updated: datetime
    available_languages: List[str] = ["en", "hi"]
