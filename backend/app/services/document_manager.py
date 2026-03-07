from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.models.service import DocumentRequirement, AlternativeDocument

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages document requirements and validation"""
    
    def get_requirements_for_service(
        self,
        service_id: str,
        document_requirements: List[DocumentRequirement]
    ) -> List[DocumentRequirement]:
        """Get document requirements for a service"""
        return document_requirements
    
    def get_alternatives(
        self,
        document_id: str,
        document_requirements: List[DocumentRequirement]
    ) -> List[AlternativeDocument]:
        """Get alternative documents"""
        for req in document_requirements:
            if req.document_id == document_id:
                return req.alternatives
        return []
    
    def validate_document_format(
        self,
        document_type: str,
        file_format: str
    ) -> bool:
        """Validate document format"""
        allowed_formats = {
            "identity_proof": ["pdf", "jpg", "jpeg", "png"],
            "address_proof": ["pdf", "jpg", "jpeg", "png"],
            "certificate": ["pdf"],
            "default": ["pdf", "jpg", "jpeg", "png"]
        }
        
        formats = allowed_formats.get(document_type, allowed_formats["default"])
        return file_format.lower() in formats
    
    def check_validity(
        self,
        issue_date: datetime,
        validity_period: Optional[str]
    ) -> bool:
        """Check if document is still valid"""
        if not validity_period:
            return True
        
        # Parse validity period (e.g., "6 months", "1 year")
        try:
            if "month" in validity_period:
                months = int(validity_period.split()[0])
                expiry = issue_date + timedelta(days=months * 30)
            elif "year" in validity_period:
                years = int(validity_period.split()[0])
                expiry = issue_date + timedelta(days=years * 365)
            else:
                return True
            
            return datetime.utcnow() < expiry
        except:
            return True
    
    def get_obtainment_guidance(
        self,
        document_id: str,
        document_requirements: List[DocumentRequirement]
    ) -> Optional[str]:
        """Get guidance on obtaining a document"""
        for req in document_requirements:
            if req.document_id == document_id:
                return req.obtainment_guidance
        return None


document_manager = DocumentManager()
