"""
Document Parser Service

Extracts structured data from government documents using OCR results.
Implements template matching and field extraction for various document types.
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
from datetime import datetime
from pydantic import BaseModel


class DocumentType(str, Enum):
    """Supported document types for parsing"""
    AADHAAR = "aadhaar"
    PAN = "pan"
    DRIVING_LICENSE = "driving_license"
    VOTER_ID = "voter_id"
    PASSPORT = "passport"
    INCOME_CERTIFICATE = "income_certificate"
    CASTE_CERTIFICATE = "caste_certificate"
    OBC_CERTIFICATE = "obc_certificate"
    DOMICILE_CERTIFICATE = "domicile_certificate"
    BIRTH_CERTIFICATE = "birth_certificate"
    DEATH_CERTIFICATE = "death_certificate"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    EDUCATIONAL_CERTIFICATE = "educational_certificate"
    UNKNOWN = "unknown"


class ExtractedField(BaseModel):
    """Represents an extracted data field"""
    field_name: str
    value: str
    confidence: float
    normalized_value: Optional[str] = None


class ParsedDocument(BaseModel):
    """Represents a parsed document with extracted fields"""
    document_type: DocumentType
    fields: List[ExtractedField]
    confidence: float
    raw_text: str


class DocumentParser:
    """
    Parses government documents and extracts structured data fields.
    Uses template matching and pattern recognition.
    """
    
    def __init__(self):
        """Initialize document parser with templates and patterns"""
        self._init_patterns()
        self._init_templates()
    
    def _init_patterns(self):
        """Initialize regex patterns for common data fields"""
        # Aadhaar number: 12 digits with optional spaces
        self.aadhaar_pattern = re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')
        
        # PAN number: 5 letters, 4 digits, 1 letter
        self.pan_pattern = re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b')
        
        # Driving License: varies by state, common format
        self.dl_pattern = re.compile(r'\b[A-Z]{2}\d{13,14}\b')
        
        # Voter ID: 3 letters followed by 7 digits
        self.voter_id_pattern = re.compile(r'\b[A-Z]{3}\d{7}\b')
        
        # Passport: 1 letter followed by 7 digits
        self.passport_pattern = re.compile(r'\b[A-Z]\d{7}\b')
        
        # PIN code: 6 digits
        self.pincode_pattern = re.compile(r'\b\d{6}\b')
        
        # Date patterns (various formats)
        self.date_patterns = [
            re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'),  # DD/MM/YYYY or DD-MM-YYYY
            re.compile(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b'),  # YYYY/MM/DD or YYYY-MM-DD
            re.compile(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b', re.IGNORECASE)
        ]
        
        # Mobile number: 10 digits
        self.mobile_pattern = re.compile(r'\b[6-9]\d{9}\b')
        
        # Email pattern
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    def _init_templates(self):
        """Initialize document templates with expected fields"""
        self.templates = {
            DocumentType.AADHAAR: {
                "keywords": ["aadhaar", "aadhar", "uidai", "unique identification"],
                "fields": ["name", "dob", "gender", "aadhaar_number", "address", "father_name", "mobile"]
            },
            DocumentType.PAN: {
                "keywords": ["income tax", "permanent account number", "pan"],
                "fields": ["name", "father_name", "dob", "pan_number"]
            },
            DocumentType.DRIVING_LICENSE: {
                "keywords": ["driving licence", "driving license", "transport"],
                "fields": ["name", "dob", "dl_number", "address", "issue_date", "validity", "vehicle_class"]
            },
            DocumentType.VOTER_ID: {
                "keywords": ["election commission", "electoral", "voter", "epic"],
                "fields": ["name", "father_name", "dob", "voter_id", "address"]
            },
            DocumentType.PASSPORT: {
                "keywords": ["passport", "republic of india", "immigration"],
                "fields": ["name", "dob", "passport_number", "issue_date", "expiry_date", "place_of_birth"]
            },
            DocumentType.INCOME_CERTIFICATE: {
                "keywords": ["income certificate", "annual income"],
                "fields": ["name", "father_name", "address", "annual_income", "issue_date", "certificate_number"]
            },
            DocumentType.CASTE_CERTIFICATE: {
                "keywords": ["caste certificate", "community certificate"],
                "fields": ["name", "father_name", "caste", "address", "issue_date", "certificate_number"]
            },
            DocumentType.OBC_CERTIFICATE: {
                "keywords": ["obc", "other backward class", "non-creamy layer"],
                "fields": ["name", "father_name", "caste", "address", "issue_date", "certificate_number", "validity"]
            }
        }

    
    def parse_document(self, ocr_text: str, confidence_scores: Optional[Dict[str, float]] = None) -> ParsedDocument:
        """
        Parse OCR text and extract structured data
        
        Args:
            ocr_text: Raw text from OCR
            confidence_scores: Optional confidence scores from OCR
            
        Returns:
            ParsedDocument with extracted fields
        """
        # Identify document type
        doc_type = self._identify_document_type(ocr_text)
        
        # Extract fields based on document type
        if doc_type == DocumentType.AADHAAR:
            fields = self._extract_aadhaar_fields(ocr_text)
        elif doc_type == DocumentType.PAN:
            fields = self._extract_pan_fields(ocr_text)
        elif doc_type == DocumentType.DRIVING_LICENSE:
            fields = self._extract_dl_fields(ocr_text)
        elif doc_type == DocumentType.VOTER_ID:
            fields = self._extract_voter_id_fields(ocr_text)
        elif doc_type == DocumentType.PASSPORT:
            fields = self._extract_passport_fields(ocr_text)
        elif doc_type in [DocumentType.INCOME_CERTIFICATE, DocumentType.CASTE_CERTIFICATE, DocumentType.OBC_CERTIFICATE]:
            fields = self._extract_certificate_fields(ocr_text, doc_type)
        else:
            fields = []
        
        # Calculate overall confidence
        overall_confidence = sum(f.confidence for f in fields) / len(fields) if fields else 0.0
        
        return ParsedDocument(
            document_type=doc_type,
            fields=fields,
            confidence=overall_confidence,
            raw_text=ocr_text
        )
    
    def _identify_document_type(self, text: str) -> DocumentType:
        """
        Identify document type based on keywords and patterns
        
        Args:
            text: OCR text
            
        Returns:
            Identified document type
        """
        text_lower = text.lower()
        
        # Check for ID number patterns first (more specific)
        if self.aadhaar_pattern.search(text):
            return DocumentType.AADHAAR
        if self.pan_pattern.search(text):
            return DocumentType.PAN
        if self.passport_pattern.search(text):
            return DocumentType.PASSPORT
        if self.dl_pattern.search(text):
            return DocumentType.DRIVING_LICENSE
        if self.voter_id_pattern.search(text):
            return DocumentType.VOTER_ID
        
        # Check for keywords
        for doc_type, template in self.templates.items():
            keywords = template.get("keywords", [])
            if any(keyword in text_lower for keyword in keywords):
                return doc_type
        
        return DocumentType.UNKNOWN
    
    def _extract_aadhaar_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields from Aadhaar card"""
        fields = []
        
        # Extract Aadhaar number
        aadhaar_match = self.aadhaar_pattern.search(text)
        if aadhaar_match:
            aadhaar_num = aadhaar_match.group().replace(" ", "")
            fields.append(ExtractedField(
                field_name="aadhaar_number",
                value=aadhaar_match.group(),
                confidence=0.95,
                normalized_value=aadhaar_num
            ))
        
        # Extract name (usually after "Name:" or first line)
        name_match = re.search(r'(?:Name|नाम)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        if name_match:
            fields.append(ExtractedField(
                field_name="name",
                value=name_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract DOB
        dob_match = re.search(r'(?:DOB|Date of Birth|जन्म तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if dob_match:
            dob_str = dob_match.group(1)
            normalized_dob = self._normalize_date(dob_str)
            fields.append(ExtractedField(
                field_name="dob",
                value=dob_str,
                confidence=0.90,
                normalized_value=normalized_dob
            ))
        
        # Extract gender
        gender_match = re.search(r'(?:Gender|लिंग)[:\s]+(Male|Female|MALE|FEMALE|पुरुष|महिला)', text, re.IGNORECASE)
        if gender_match:
            fields.append(ExtractedField(
                field_name="gender",
                value=gender_match.group(1).strip(),
                confidence=0.90
            ))
        
        # Extract address
        address_match = re.search(r'(?:Address|पता)[:\s]+(.+?)(?:\n\n|\d{6})', text, re.IGNORECASE | re.DOTALL)
        if address_match:
            address = address_match.group(1).strip()
            # Extract PIN code from address
            pincode_match = self.pincode_pattern.search(address)
            if pincode_match:
                fields.append(ExtractedField(
                    field_name="pincode",
                    value=pincode_match.group(),
                    confidence=0.95
                ))
            fields.append(ExtractedField(
                field_name="address",
                value=address,
                confidence=0.75
            ))
        
        return fields
    
    def _extract_pan_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields from PAN card"""
        fields = []
        
        # Extract PAN number
        pan_match = self.pan_pattern.search(text)
        if pan_match:
            fields.append(ExtractedField(
                field_name="pan_number",
                value=pan_match.group(),
                confidence=0.95
            ))
        
        # Extract name
        name_match = re.search(r'(?:Name|नाम)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        if name_match:
            fields.append(ExtractedField(
                field_name="name",
                value=name_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract father's name
        father_match = re.search(r"(?:Father'?s? Name|पिता का नाम)[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
        if father_match:
            fields.append(ExtractedField(
                field_name="father_name",
                value=father_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract DOB
        dob_match = re.search(r'(?:DOB|Date of Birth|जन्म तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if dob_match:
            dob_str = dob_match.group(1)
            normalized_dob = self._normalize_date(dob_str)
            fields.append(ExtractedField(
                field_name="dob",
                value=dob_str,
                confidence=0.90,
                normalized_value=normalized_dob
            ))
        
        return fields
    
    def _extract_dl_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields from Driving License"""
        fields = []
        
        # Extract DL number
        dl_match = self.dl_pattern.search(text)
        if dl_match:
            fields.append(ExtractedField(
                field_name="dl_number",
                value=dl_match.group(),
                confidence=0.95
            ))
        
        # Extract name
        name_match = re.search(r'(?:Name|नाम)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        if name_match:
            fields.append(ExtractedField(
                field_name="name",
                value=name_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract DOB
        dob_match = re.search(r'(?:DOB|Date of Birth|जन्म तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if dob_match:
            dob_str = dob_match.group(1)
            normalized_dob = self._normalize_date(dob_str)
            fields.append(ExtractedField(
                field_name="dob",
                value=dob_str,
                confidence=0.90,
                normalized_value=normalized_dob
            ))
        
        # Extract issue date
        issue_match = re.search(r'(?:Issue Date|जारी तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if issue_match:
            issue_str = issue_match.group(1)
            normalized_issue = self._normalize_date(issue_str)
            fields.append(ExtractedField(
                field_name="issue_date",
                value=issue_str,
                confidence=0.90,
                normalized_value=normalized_issue
            ))
        
        # Extract validity
        validity_match = re.search(r'(?:Valid Till|Validity|वैधता)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if validity_match:
            validity_str = validity_match.group(1)
            normalized_validity = self._normalize_date(validity_str)
            fields.append(ExtractedField(
                field_name="validity",
                value=validity_str,
                confidence=0.90,
                normalized_value=normalized_validity
            ))
        
        # Extract vehicle class
        class_match = re.search(r'(?:Class|COV|वर्ग)[:\s]+([A-Z0-9,\s]+)', text, re.IGNORECASE)
        if class_match:
            fields.append(ExtractedField(
                field_name="vehicle_class",
                value=class_match.group(1).strip(),
                confidence=0.80
            ))
        
        # Extract address
        address_match = re.search(r'(?:Address|पता)[:\s]+(.+?)(?:\n\n|\d{6})', text, re.IGNORECASE | re.DOTALL)
        if address_match:
            fields.append(ExtractedField(
                field_name="address",
                value=address_match.group(1).strip(),
                confidence=0.75
            ))
        
        return fields

    
    def _extract_voter_id_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields from Voter ID"""
        fields = []
        
        # Extract Voter ID number
        voter_id_match = self.voter_id_pattern.search(text)
        if voter_id_match:
            fields.append(ExtractedField(
                field_name="voter_id",
                value=voter_id_match.group(),
                confidence=0.95
            ))
        
        # Extract name
        name_match = re.search(r'(?:Name|नाम)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        if name_match:
            fields.append(ExtractedField(
                field_name="name",
                value=name_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract father's name
        father_match = re.search(r"(?:Father'?s? Name|पिता का नाम)[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
        if father_match:
            fields.append(ExtractedField(
                field_name="father_name",
                value=father_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract DOB
        dob_match = re.search(r'(?:DOB|Date of Birth|Age|जन्म तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if dob_match:
            dob_str = dob_match.group(1)
            normalized_dob = self._normalize_date(dob_str)
            fields.append(ExtractedField(
                field_name="dob",
                value=dob_str,
                confidence=0.90,
                normalized_value=normalized_dob
            ))
        
        # Extract address
        address_match = re.search(r'(?:Address|पता)[:\s]+(.+?)(?:\n\n|\d{6})', text, re.IGNORECASE | re.DOTALL)
        if address_match:
            fields.append(ExtractedField(
                field_name="address",
                value=address_match.group(1).strip(),
                confidence=0.75
            ))
        
        return fields
    
    def _extract_passport_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields from Passport"""
        fields = []
        
        # Extract Passport number
        passport_match = self.passport_pattern.search(text)
        if passport_match:
            fields.append(ExtractedField(
                field_name="passport_number",
                value=passport_match.group(),
                confidence=0.95
            ))
        
        # Extract name (surname and given name)
        surname_match = re.search(r'(?:Surname|उपनाम)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        given_name_match = re.search(r'(?:Given Name|दिया गया नाम)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        
        if surname_match and given_name_match:
            full_name = f"{given_name_match.group(1).strip()} {surname_match.group(1).strip()}"
            fields.append(ExtractedField(
                field_name="name",
                value=full_name,
                confidence=0.85
            ))
        elif surname_match:
            fields.append(ExtractedField(
                field_name="name",
                value=surname_match.group(1).strip(),
                confidence=0.80
            ))
        
        # Extract DOB
        dob_match = re.search(r'(?:DOB|Date of Birth|जन्म तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if dob_match:
            dob_str = dob_match.group(1)
            normalized_dob = self._normalize_date(dob_str)
            fields.append(ExtractedField(
                field_name="dob",
                value=dob_str,
                confidence=0.90,
                normalized_value=normalized_dob
            ))
        
        # Extract place of birth
        pob_match = re.search(r'(?:Place of Birth|जन्म स्थान)[:\s]+([A-Za-z\s,]+)', text, re.IGNORECASE)
        if pob_match:
            fields.append(ExtractedField(
                field_name="place_of_birth",
                value=pob_match.group(1).strip(),
                confidence=0.80
            ))
        
        # Extract issue date
        issue_match = re.search(r'(?:Date of Issue|जारी तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if issue_match:
            issue_str = issue_match.group(1)
            normalized_issue = self._normalize_date(issue_str)
            fields.append(ExtractedField(
                field_name="issue_date",
                value=issue_str,
                confidence=0.90,
                normalized_value=normalized_issue
            ))
        
        # Extract expiry date
        expiry_match = re.search(r'(?:Date of Expiry|समाप्ति तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if expiry_match:
            expiry_str = expiry_match.group(1)
            normalized_expiry = self._normalize_date(expiry_str)
            fields.append(ExtractedField(
                field_name="expiry_date",
                value=expiry_str,
                confidence=0.90,
                normalized_value=normalized_expiry
            ))
        
        return fields
    
    def _extract_certificate_fields(self, text: str, doc_type: DocumentType) -> List[ExtractedField]:
        """Extract fields from various certificates"""
        fields = []
        
        # Extract certificate number
        cert_num_match = re.search(r'(?:Certificate No|Cert No|Number|प्रमाण पत्र संख्या)[:\s]+([A-Z0-9/-]+)', text, re.IGNORECASE)
        if cert_num_match:
            fields.append(ExtractedField(
                field_name="certificate_number",
                value=cert_num_match.group(1).strip(),
                confidence=0.90
            ))
        
        # Extract name
        name_match = re.search(r'(?:Name|नाम)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        if name_match:
            fields.append(ExtractedField(
                field_name="name",
                value=name_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract father's name
        father_match = re.search(r"(?:Father'?s? Name|पिता का नाम)[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
        if father_match:
            fields.append(ExtractedField(
                field_name="father_name",
                value=father_match.group(1).strip(),
                confidence=0.85
            ))
        
        # Extract issue date
        issue_match = re.search(r'(?:Issue Date|Date of Issue|Issued on|जारी तिथि)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
        if issue_match:
            issue_str = issue_match.group(1)
            normalized_issue = self._normalize_date(issue_str)
            fields.append(ExtractedField(
                field_name="issue_date",
                value=issue_str,
                confidence=0.90,
                normalized_value=normalized_issue
            ))
        
        # Extract validity (for OBC certificates)
        if doc_type == DocumentType.OBC_CERTIFICATE:
            validity_match = re.search(r'(?:Valid Till|Validity|वैधता)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
            if validity_match:
                validity_str = validity_match.group(1)
                normalized_validity = self._normalize_date(validity_str)
                fields.append(ExtractedField(
                    field_name="validity",
                    value=validity_str,
                    confidence=0.90,
                    normalized_value=normalized_validity
                ))
        
        # Extract caste (for caste/OBC certificates)
        if doc_type in [DocumentType.CASTE_CERTIFICATE, DocumentType.OBC_CERTIFICATE]:
            caste_match = re.search(r'(?:Caste|Community|जाति)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
            if caste_match:
                fields.append(ExtractedField(
                    field_name="caste",
                    value=caste_match.group(1).strip(),
                    confidence=0.85
                ))
        
        # Extract annual income (for income certificates)
        if doc_type == DocumentType.INCOME_CERTIFICATE:
            income_match = re.search(r'(?:Annual Income|Income|वार्षिक आय)[:\s]+(?:Rs\.?|₹)?\s*([0-9,]+)', text, re.IGNORECASE)
            if income_match:
                income_value = income_match.group(1).replace(',', '')
                fields.append(ExtractedField(
                    field_name="annual_income",
                    value=income_match.group(1),
                    confidence=0.85,
                    normalized_value=income_value
                ))
        
        # Extract address
        address_match = re.search(r'(?:Address|पता)[:\s]+(.+?)(?:\n\n|\d{6})', text, re.IGNORECASE | re.DOTALL)
        if address_match:
            fields.append(ExtractedField(
                field_name="address",
                value=address_match.group(1).strip(),
                confidence=0.75
            ))
        
        return fields
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date to YYYY-MM-DD format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Normalized date string in YYYY-MM-DD format
        """
        # Try DD/MM/YYYY or DD-MM-YYYY
        match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Try YYYY/MM/DD or YYYY-MM-DD
        match = re.match(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Try DD Month YYYY
        month_map = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }
        match = re.match(r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            day, month_str, year = match.groups()
            month = month_map[month_str.lower()[:3]]
            return f"{year}-{month}-{day.zfill(2)}"
        
        # Return original if no pattern matches
        return date_str
    
    def validate_id_number(self, id_type: str, id_number: str) -> Tuple[bool, Optional[str]]:
        """
        Validate ID number format
        
        Args:
            id_type: Type of ID (aadhaar, pan, etc.)
            id_number: ID number to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        id_number = id_number.replace(" ", "").upper()
        
        if id_type == "aadhaar":
            if not re.match(r'^\d{12}$', id_number):
                return False, "Aadhaar number must be 12 digits"
            # Verhoeff algorithm check could be added here
            return True, None
        
        elif id_type == "pan":
            if not re.match(r'^[A-Z]{5}\d{4}[A-Z]$', id_number):
                return False, "PAN must be in format: 5 letters, 4 digits, 1 letter"
            return True, None
        
        elif id_type == "passport":
            if not re.match(r'^[A-Z]\d{7}$', id_number):
                return False, "Passport number must be 1 letter followed by 7 digits"
            return True, None
        
        elif id_type == "voter_id":
            if not re.match(r'^[A-Z]{3}\d{7}$', id_number):
                return False, "Voter ID must be 3 letters followed by 7 digits"
            return True, None
        
        return True, None
    
    def extract_address_components(self, address: str) -> Dict[str, str]:
        """
        Parse address into components
        
        Args:
            address: Full address string
            
        Returns:
            Dictionary with address components
        """
        components = {}
        
        # Extract PIN code
        pincode_match = self.pincode_pattern.search(address)
        if pincode_match:
            components['pincode'] = pincode_match.group()
            # Remove PIN code from address for further processing
            address = address.replace(pincode_match.group(), '').strip()
        
        # Extract state (common Indian states)
        states = [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
            'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
            'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
            'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
            'Delhi', 'Puducherry', 'Chandigarh'
        ]
        
        for state in states:
            if state.lower() in address.lower():
                components['state'] = state
                break
        
        # Store remaining address
        components['full_address'] = address.strip()
        
        return components
