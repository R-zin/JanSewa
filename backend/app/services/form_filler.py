"""
Form Filler Service

Handles automatic form filling with data from multiple sources:
- Extracted data from OCR
- DigiLocker documents
- User profile

Requirements: 12.11, 12.12, 12.13, 12.16, 12.30
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import re


class DataSource(str, Enum):
    """Data source types for form filling"""
    EXTRACTED_DATA = "extracted_data"  # Highest priority
    DIGILOCKER = "digilocker"
    USER_PROFILE = "user_profile"


class ValidationResult(BaseModel):
    """Form field validation result"""
    field_id: str
    is_valid: bool
    error_message: Optional[str] = None
    suggested_value: Optional[str] = None


class FilledField(BaseModel):
    """Represents a filled form field"""
    field_id: str
    field_name: str
    value: str
    source: DataSource
    confidence: float
    validated: bool


class FormSummary(BaseModel):
    """Summary of filled form fields for user review"""
    total_fields: int
    filled_fields: int
    fields: List[FilledField]
    validation_results: List[ValidationResult]
    ready_for_submission: bool
    warnings: List[str] = []


class FormFiller:
    """
    Handles automatic form filling with data prioritization and validation.
    
    Requirements:
    - 12.11: Populate form fields from user profile, stored documents, or extracted data
    - 12.12: Prioritize extracted data from uploaded documents
    - 12.13: Automatically populate fields when extracted data matches
    - 12.16: Validate form data matches field requirements before submission
    - 12.30: Display summary of populated fields for user review
    """
    
    def __init__(self):
        """Initialize form filler"""
        self._init_field_validators()
        self._init_field_mappings()
    
    def _init_field_validators(self):
        """Initialize field validation patterns"""
        self.validators = {
            "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            "mobile": re.compile(r'^[6-9]\d{9}$'),
            "pincode": re.compile(r'^\d{6}$'),
            "aadhaar": re.compile(r'^\d{12}$'),
            "pan": re.compile(r'^[A-Z]{5}\d{4}[A-Z]$'),
            "date": re.compile(r'^\d{4}-\d{2}-\d{2}$'),
            "name": re.compile(r'^[A-Za-z\s]{2,}$'),
        }
    
    def _init_field_mappings(self):
        """Initialize common field name mappings"""
        self.field_mappings = {
            # Name fields
            "name": ["name", "full_name", "applicant_name", "candidate_name"],
            "father_name": ["father_name", "fathers_name", "parent_name"],
            
            # Contact fields
            "email": ["email", "email_address", "email_id"],
            "mobile": ["mobile", "mobile_number", "phone", "contact_number"],
            
            # Address fields
            "address": ["address", "permanent_address", "residential_address"],
            "pincode": ["pincode", "pin_code", "postal_code", "zip"],
            "state": ["state", "state_name"],
            "district": ["district", "district_name"],
            "city": ["city", "town", "village"],
            
            # ID fields
            "aadhaar_number": ["aadhaar", "aadhaar_number", "uid"],
            "pan_number": ["pan", "pan_number", "pan_card"],
            "voter_id": ["voter_id", "epic_number", "electoral_id"],
            "dl_number": ["dl_number", "driving_license", "license_number"],
            "passport_number": ["passport", "passport_number"],
            
            # Date fields
            "dob": ["dob", "date_of_birth", "birth_date"],
            "issue_date": ["issue_date", "date_of_issue"],
            "validity": ["validity", "valid_till", "expiry_date"],
            
            # Other fields
            "gender": ["gender", "sex"],
            "caste": ["caste", "community"],
            "annual_income": ["annual_income", "income", "yearly_income"],
        }
    
    def prioritize_data_sources(
        self,
        extracted_data: Optional[Dict[str, Any]] = None,
        digilocker_data: Optional[Dict[str, Any]] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Any, DataSource, float]]:
        """
        Prioritize data from multiple sources.
        Extracted data has highest priority, followed by DigiLocker, then user profile.
        
        Requirements: 12.12 - Prioritize extracted data from uploaded documents
        
        Args:
            extracted_data: Data extracted from OCR
            digilocker_data: Data from DigiLocker documents
            user_profile: User profile data
            
        Returns:
            Dictionary mapping field names to (value, source, confidence) tuples
        """
        prioritized_data = {}
        
        # Priority 1: Extracted data (highest priority)
        if extracted_data:
            for field_name, field_value in extracted_data.items():
                if field_value:
                    # Extract confidence if available
                    confidence = 0.9  # Default high confidence for extracted data
                    if isinstance(field_value, dict):
                        confidence = field_value.get("confidence", 0.9)
                        field_value = field_value.get("value", field_value)
                    
                    prioritized_data[field_name] = (
                        field_value,
                        DataSource.EXTRACTED_DATA,
                        confidence
                    )
        
        # Priority 2: DigiLocker data
        if digilocker_data:
            for field_name, field_value in digilocker_data.items():
                if field_value and field_name not in prioritized_data:
                    prioritized_data[field_name] = (
                        field_value,
                        DataSource.DIGILOCKER,
                        0.95  # High confidence for DigiLocker data
                    )
        
        # Priority 3: User profile (lowest priority)
        if user_profile:
            for field_name, field_value in user_profile.items():
                if field_value and field_name not in prioritized_data:
                    prioritized_data[field_name] = (
                        field_value,
                        DataSource.USER_PROFILE,
                        0.8  # Medium confidence for user profile
                    )
        
        return prioritized_data
    
    def match_field_to_data(
        self,
        form_field_name: str,
        available_data: Dict[str, Tuple[Any, DataSource, float]]
    ) -> Optional[Tuple[Any, DataSource, float]]:
        """
        Match a form field to available data using field mappings.
        
        Requirements: 12.13 - Automatically populate fields when extracted data matches
        
        Args:
            form_field_name: Name of the form field
            available_data: Prioritized data from all sources
            
        Returns:
            Tuple of (value, source, confidence) if match found, None otherwise
        """
        # Normalize field name
        normalized_field = form_field_name.lower().replace(" ", "_").replace("-", "_")
        
        # Direct match
        if normalized_field in available_data:
            return available_data[normalized_field]
        
        # Check field mappings
        for canonical_name, variations in self.field_mappings.items():
            if normalized_field in variations:
                if canonical_name in available_data:
                    return available_data[canonical_name]
        
        # Fuzzy match - check if any data field contains the form field name
        for data_field, data_value in available_data.items():
            if normalized_field in data_field or data_field in normalized_field:
                return data_value
        
        return None
    
    def fill_form_fields(
        self,
        form_fields: List[Dict[str, Any]],
        extracted_data: Optional[Dict[str, Any]] = None,
        digilocker_data: Optional[Dict[str, Any]] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> List[FilledField]:
        """
        Fill form fields using prioritized data sources.
        
        Requirements:
        - 12.11: Populate form fields from multiple sources
        - 12.12: Prioritize extracted data
        - 12.13: Automatically populate matching fields
        
        Args:
            form_fields: List of form field definitions
            extracted_data: OCR extracted data
            digilocker_data: DigiLocker document data
            user_profile: User profile data
            
        Returns:
            List of filled fields with source information
        """
        # Prioritize data sources
        prioritized_data = self.prioritize_data_sources(
            extracted_data,
            digilocker_data,
            user_profile
        )
        
        filled_fields = []
        
        for field in form_fields:
            field_id = field.get("field_id", "")
            field_name = field.get("field_name", "")
            field_label = field.get("label", field_name)
            
            # Try to match field to available data
            match = self.match_field_to_data(field_name, prioritized_data)
            
            if match:
                value, source, confidence = match
                
                # Validate the value before filling
                is_valid = self._validate_field_value(
                    field.get("field_type", "text"),
                    str(value)
                )
                
                filled_field = FilledField(
                    field_id=field_id,
                    field_name=field_label,
                    value=str(value),
                    source=source,
                    confidence=confidence,
                    validated=is_valid
                )
                
                filled_fields.append(filled_field)
        
        return filled_fields
    
    def validate_form_data(
        self,
        filled_fields: List[FilledField],
        form_field_definitions: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """
        Validate form data before submission.
        
        Requirements: 12.16 - Validate form data matches field requirements
        
        Args:
            filled_fields: List of filled fields
            form_field_definitions: Form field definitions with validation rules
            
        Returns:
            List of validation results
        """
        validation_results = []
        
        # Create lookup for field definitions
        field_defs = {f.get("field_id"): f for f in form_field_definitions}
        
        for filled_field in filled_fields:
            field_def = field_defs.get(filled_field.field_id, {})
            field_type = field_def.get("field_type", "text")
            required = field_def.get("required", False)
            validation_pattern = field_def.get("validation_pattern")
            
            # Check if required field is filled
            if required and not filled_field.value:
                validation_results.append(ValidationResult(
                    field_id=filled_field.field_id,
                    is_valid=False,
                    error_message=f"{filled_field.field_name} is required"
                ))
                continue
            
            # Validate field type
            is_valid, error_msg = self._validate_field_type(
                field_type,
                filled_field.value,
                validation_pattern
            )
            
            validation_results.append(ValidationResult(
                field_id=filled_field.field_id,
                is_valid=is_valid,
                error_message=error_msg
            ))
        
        # Check for missing required fields
        filled_field_ids = {f.field_id for f in filled_fields}
        for field_def in form_field_definitions:
            if field_def.get("required") and field_def.get("field_id") not in filled_field_ids:
                validation_results.append(ValidationResult(
                    field_id=field_def.get("field_id"),
                    is_valid=False,
                    error_message=f"{field_def.get('label', 'Field')} is required but not filled"
                ))
        
        return validation_results
    
    def _validate_field_value(self, field_type: str, value: str) -> bool:
        """
        Basic validation of field value based on type.
        
        Args:
            field_type: Type of field
            value: Value to validate
            
        Returns:
            True if valid
        """
        if not value:
            return False
        
        # Get validator for field type
        validator = self.validators.get(field_type)
        if validator:
            return bool(validator.match(value))
        
        # Default validation - non-empty
        return len(value.strip()) > 0
    
    def _validate_field_type(
        self,
        field_type: str,
        value: str,
        custom_pattern: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate field value against type and custom pattern.
        
        Args:
            field_type: Type of field
            value: Value to validate
            custom_pattern: Custom regex pattern
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return True, None  # Empty values are handled separately
        
        # Custom pattern validation
        if custom_pattern:
            try:
                if not re.match(custom_pattern, value):
                    return False, f"Value does not match required pattern"
            except re.error:
                pass  # Invalid pattern, skip
        
        # Type-specific validation
        if field_type == "email":
            if not self.validators["email"].match(value):
                return False, "Invalid email format"
        
        elif field_type == "mobile":
            if not self.validators["mobile"].match(value):
                return False, "Invalid mobile number (must be 10 digits starting with 6-9)"
        
        elif field_type == "pincode":
            if not self.validators["pincode"].match(value):
                return False, "Invalid PIN code (must be 6 digits)"
        
        elif field_type == "aadhaar":
            if not self.validators["aadhaar"].match(value.replace(" ", "")):
                return False, "Invalid Aadhaar number (must be 12 digits)"
        
        elif field_type == "pan":
            if not self.validators["pan"].match(value.upper()):
                return False, "Invalid PAN format"
        
        elif field_type == "date":
            if not self.validators["date"].match(value):
                return False, "Invalid date format (use YYYY-MM-DD)"
        
        elif field_type == "number":
            try:
                float(value)
            except ValueError:
                return False, "Must be a valid number"
        
        return True, None
    
    def generate_form_summary(
        self,
        filled_fields: List[FilledField],
        validation_results: List[ValidationResult],
        total_fields: int
    ) -> FormSummary:
        """
        Generate summary of filled form fields for user review.
        
        Requirements: 12.30 - Display summary of populated fields for user review
        
        Args:
            filled_fields: List of filled fields
            validation_results: Validation results
            total_fields: Total number of form fields
            
        Returns:
            Form summary for user review
        """
        # Check if all validations passed
        all_valid = all(v.is_valid for v in validation_results)
        
        # Generate warnings
        warnings = []
        
        # Check for low confidence fields
        low_confidence_fields = [
            f for f in filled_fields if f.confidence < 0.7
        ]
        if low_confidence_fields:
            warnings.append(
                f"{len(low_confidence_fields)} field(s) have low confidence. "
                "Please review carefully."
            )
        
        # Check for fields from user profile (may be outdated)
        profile_fields = [
            f for f in filled_fields if f.source == DataSource.USER_PROFILE
        ]
        if profile_fields:
            warnings.append(
                f"{len(profile_fields)} field(s) filled from user profile. "
                "Please verify the information is current."
            )
        
        # Check for validation errors
        validation_errors = [v for v in validation_results if not v.is_valid]
        if validation_errors:
            warnings.append(
                f"{len(validation_errors)} field(s) have validation errors. "
                "Please correct before submission."
            )
        
        return FormSummary(
            total_fields=total_fields,
            filled_fields=len(filled_fields),
            fields=filled_fields,
            validation_results=validation_results,
            ready_for_submission=all_valid and len(filled_fields) > 0,
            warnings=warnings
        )
    
    def get_unfilled_fields(
        self,
        form_fields: List[Dict[str, Any]],
        filled_fields: List[FilledField]
    ) -> List[Dict[str, Any]]:
        """
        Get list of fields that were not automatically filled.
        
        Args:
            form_fields: All form field definitions
            filled_fields: Fields that were filled
            
        Returns:
            List of unfilled field definitions
        """
        filled_field_ids = {f.field_id for f in filled_fields}
        
        unfilled = [
            field for field in form_fields
            if field.get("field_id") not in filled_field_ids
        ]
        
        return unfilled


# Global instance
form_filler = FormFiller()
