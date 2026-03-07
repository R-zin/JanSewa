import re
import logging
from typing import Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class DataType(str, Enum):
    """Data type classification"""
    CONVERSATION_CONTEXT = "conversation_context"
    USER_PREFERENCE = "user_preference"
    PERSONAL_INFO = "personal_info"
    SENSITIVE_INFO = "sensitive_info"


class SensitiveDataType(str, Enum):
    """Sensitive data types"""
    AADHAAR_NUMBER = "aadhaar_number"
    PAN_NUMBER = "pan_number"
    PERSONAL_NAME = "personal_name"
    ADDRESS = "address"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    PASSWORD = "password"


class WarningType(str, Enum):
    """Warning types"""
    SENSITIVE_DATA_ENTRY = "sensitive_data_entry"
    LINK_VERIFICATION = "link_verification"
    GUIDANCE_ONLY = "guidance_only"


class SeverityLevel(str, Enum):
    """Severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PrivacyControls:
    """Privacy controls for data handling"""
    
    # PII detection patterns
    PII_PATTERNS = {
        SensitiveDataType.AADHAAR_NUMBER: r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        SensitiveDataType.PAN_NUMBER: r'\b[A-Z]{5}\d{4}[A-Z]\b',
        SensitiveDataType.PHONE_NUMBER: r'\b\d{10}\b',
        SensitiveDataType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    }
    
    def generate_warning(self, sensitive_data_type: SensitiveDataType) -> Dict[str, Any]:
        """
        Generate security warnings for sensitive data types.
        
        Args:
            sensitive_data_type: The type of sensitive data being handled
            
        Returns:
            Dictionary containing warning information with keys:
                - warning_type: Type of warning (always SENSITIVE_DATA_ENTRY)
                - message: Human-readable warning message
                - severity: Severity level (WARNING or CRITICAL)
                - recommendations: List of security recommendations
        """
        warnings_config = {
            SensitiveDataType.AADHAAR_NUMBER: {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "You are providing your Aadhaar number. This is highly sensitive personal information.",
                "severity": SeverityLevel.CRITICAL.value,
                "recommendations": [
                    "Only provide Aadhaar details on official government portals",
                    "Verify the website URL before entering your Aadhaar number",
                    "This assistant provides guidance only and does not process actual applications",
                    "Never share your Aadhaar number via email or unsecured channels"
                ]
            },
            SensitiveDataType.PAN_NUMBER: {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "You are providing your PAN number. This is sensitive financial information.",
                "severity": SeverityLevel.CRITICAL.value,
                "recommendations": [
                    "Only provide PAN details on official government portals",
                    "Verify the website authenticity before entering your PAN",
                    "This assistant provides guidance only and does not process actual applications",
                    "Keep your PAN information confidential"
                ]
            },
            SensitiveDataType.PERSONAL_NAME: {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "You are providing personal name information.",
                "severity": SeverityLevel.WARNING.value,
                "recommendations": [
                    "Ensure you are on a secure connection",
                    "This information will not be stored beyond your current session",
                    "This assistant provides guidance only and does not process actual applications",
                    "Verify you are interacting with legitimate services"
                ]
            },
            SensitiveDataType.ADDRESS: {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "You are providing your address. This is personally identifiable information.",
                "severity": SeverityLevel.WARNING.value,
                "recommendations": [
                    "Only provide address details when necessary for the service",
                    "This information will not be stored beyond your current session",
                    "This assistant provides guidance only and does not process actual applications",
                    "Verify the authenticity of the service before providing address details"
                ]
            },
            SensitiveDataType.PHONE_NUMBER: {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "You are providing your phone number. This is personal contact information.",
                "severity": SeverityLevel.WARNING.value,
                "recommendations": [
                    "Only provide phone number on trusted platforms",
                    "This information will not be stored beyond your current session",
                    "This assistant provides guidance only and does not process actual applications",
                    "Be cautious of unsolicited calls or messages"
                ]
            },
            SensitiveDataType.EMAIL: {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "You are providing your email address. This is personal contact information.",
                "severity": SeverityLevel.WARNING.value,
                "recommendations": [
                    "Only provide email on trusted platforms",
                    "This information will not be stored beyond your current session",
                    "This assistant provides guidance only and does not process actual applications",
                    "Be cautious of phishing emails"
                ]
            },
            SensitiveDataType.PASSWORD: {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "CRITICAL: Never provide passwords to this assistant.",
                "severity": SeverityLevel.CRITICAL.value,
                "recommendations": [
                    "This assistant NEVER needs your password",
                    "Only enter passwords directly on official government portals",
                    "Use strong, unique passwords for each service",
                    "Enable two-factor authentication when available"
                ]
            }
        }
        
        warning = warnings_config.get(sensitive_data_type)
        if not warning:
            # Default warning for unknown sensitive data types
            warning = {
                "warning_type": WarningType.SENSITIVE_DATA_ENTRY.value,
                "message": "You are providing sensitive information. Please exercise caution.",
                "severity": SeverityLevel.WARNING.value,
                "recommendations": [
                    "Only provide sensitive information on official portals",
                    "Verify the authenticity of the service",
                    "This information will not be stored beyond your current session"
                ]
            }
        
        logger.info(f"Generated security warning for {sensitive_data_type.value}")
        return warning
    
    def detect_sensitive_data(self, text: str) -> List[SensitiveDataType]:
        """
        Detect sensitive data types in user input.
        
        Args:
            text: User input text to analyze
            
        Returns:
            List of detected sensitive data types
        """
        detected_types = []
        
        for data_type, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, text):
                detected_types.append(data_type)
                logger.warning(f"Detected {data_type.value} in user input")
        
        return detected_types
