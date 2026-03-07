"""
Unit tests for Form Filler Service

Tests form filling with data prioritization and validation.
Requirements: 12.11, 12.12, 12.13, 12.16, 12.30
"""

import pytest
from app.services.form_filler import (
    FormFiller, DataSource, FilledField, ValidationResult, FormSummary
)


@pytest.fixture
def form_filler():
    """Create form filler instance"""
    return FormFiller()


@pytest.fixture
def sample_form_fields():
    """Sample form field definitions"""
    return [
        {
            "field_id": "name",
            "field_name": "name",
            "field_type": "name",
            "label": "Full Name",
            "required": True
        },
        {
            "field_id": "email",
            "field_name": "email",
            "field_type": "email",
            "label": "Email Address",
            "required": True
        },
        {
            "field_id": "mobile",
            "field_name": "mobile",
            "field_type": "mobile",
            "label": "Mobile Number",
            "required": True
        },
        {
            "field_id": "aadhaar",
            "field_name": "aadhaar_number",
            "field_type": "aadhaar",
            "label": "Aadhaar Number",
            "required": True
        },
        {
            "field_id": "address",
            "field_name": "address",
            "field_type": "text",
            "label": "Address",
            "required": False
        }
    ]


@pytest.fixture
def extracted_data():
    """Sample extracted data from OCR"""
    return {
        "name": "John Doe",
        "aadhaar_number": "123456789012",
        "address": "123 Main St, City, State 123456"
    }


@pytest.fixture
def digilocker_data():
    """Sample DigiLocker data"""
    return {
        "name": "John Doe",
        "dob": "1990-01-01",
        "mobile": "9876543210"
    }


@pytest.fixture
def user_profile():
    """Sample user profile data"""
    return {
        "email": "john.doe@example.com",
        "full_name": "John Doe",
        "mobile": "9876543210"
    }


class TestDataSourcePrioritization:
    """Test data source prioritization - Requirement 12.12"""
    
    def test_extracted_data_has_highest_priority(self, form_filler, extracted_data, digilocker_data, user_profile):
        """Test that extracted data is prioritized over other sources"""
        prioritized = form_filler.prioritize_data_sources(
            extracted_data=extracted_data,
            digilocker_data=digilocker_data,
            user_profile=user_profile
        )
        
        # Name should come from extracted data (highest priority)
        assert prioritized["name"][0] == "John Doe"
        assert prioritized["name"][1] == DataSource.EXTRACTED_DATA
        
        # Aadhaar should come from extracted data
        assert prioritized["aadhaar_number"][0] == "123456789012"
        assert prioritized["aadhaar_number"][1] == DataSource.EXTRACTED_DATA
    
    def test_digilocker_data_second_priority(self, form_filler, digilocker_data, user_profile):
        """Test that DigiLocker data is used when extracted data not available"""
        prioritized = form_filler.prioritize_data_sources(
            extracted_data=None,
            digilocker_data=digilocker_data,
            user_profile=user_profile
        )
        
        # Mobile should come from DigiLocker (second priority)
        assert prioritized["mobile"][0] == "9876543210"
        assert prioritized["mobile"][1] == DataSource.DIGILOCKER
    
    def test_user_profile_lowest_priority(self, form_filler, user_profile):
        """Test that user profile is used when other sources not available"""
        prioritized = form_filler.prioritize_data_sources(
            extracted_data=None,
            digilocker_data=None,
            user_profile=user_profile
        )
        
        # Email should come from user profile (lowest priority)
        assert prioritized["email"][0] == "john.doe@example.com"
        assert prioritized["email"][1] == DataSource.USER_PROFILE
    
    def test_extracted_data_overrides_other_sources(self, form_filler, extracted_data, digilocker_data):
        """Test that extracted data overrides DigiLocker and profile data"""
        # Both have 'name', but extracted should win
        prioritized = form_filler.prioritize_data_sources(
            extracted_data=extracted_data,
            digilocker_data=digilocker_data,
            user_profile=None
        )
        
        assert prioritized["name"][1] == DataSource.EXTRACTED_DATA


class TestFieldMatching:
    """Test field matching - Requirement 12.13"""
    
    def test_direct_field_match(self, form_filler):
        """Test direct field name matching"""
        available_data = {
            "name": ("John Doe", DataSource.EXTRACTED_DATA, 0.9)
        }
        
        match = form_filler.match_field_to_data("name", available_data)
        
        assert match is not None
        assert match[0] == "John Doe"
    
    def test_field_mapping_match(self, form_filler):
        """Test field matching using mappings"""
        available_data = {
            "full_name": ("John Doe", DataSource.USER_PROFILE, 0.8)
        }
        
        # 'name' should match 'full_name' via mapping
        match = form_filler.match_field_to_data("name", available_data)
        
        assert match is not None
        assert match[0] == "John Doe"
    
    def test_normalized_field_match(self, form_filler):
        """Test field matching with normalization"""
        available_data = {
            "mobile_number": ("9876543210", DataSource.DIGILOCKER, 0.95)
        }
        
        # 'mobile' should match 'mobile_number'
        match = form_filler.match_field_to_data("mobile", available_data)
        
        assert match is not None
        assert match[0] == "9876543210"
    
    def test_no_match_returns_none(self, form_filler):
        """Test that no match returns None"""
        available_data = {
            "name": ("John Doe", DataSource.EXTRACTED_DATA, 0.9)
        }
        
        match = form_filler.match_field_to_data("unknown_field", available_data)
        
        assert match is None


class TestFormFilling:
    """Test automatic form filling - Requirements 12.11, 12.13"""
    
    def test_fill_form_with_extracted_data(self, form_filler, sample_form_fields, extracted_data):
        """Test filling form with extracted data"""
        filled_fields = form_filler.fill_form_fields(
            sample_form_fields,
            extracted_data=extracted_data
        )
        
        # Should fill name, aadhaar, and address from extracted data
        assert len(filled_fields) >= 3
        
        # Check name field
        name_field = next((f for f in filled_fields if f.field_id == "name"), None)
        assert name_field is not None
        assert name_field.value == "John Doe"
        assert name_field.source == DataSource.EXTRACTED_DATA
    
    def test_fill_form_with_multiple_sources(
        self, form_filler, sample_form_fields, extracted_data, digilocker_data, user_profile
    ):
        """Test filling form with data from multiple sources"""
        filled_fields = form_filler.fill_form_fields(
            sample_form_fields,
            extracted_data=extracted_data,
            digilocker_data=digilocker_data,
            user_profile=user_profile
        )
        
        # Should fill all fields
        assert len(filled_fields) == 5
        
        # Name should come from extracted data
        name_field = next((f for f in filled_fields if f.field_id == "name"), None)
        assert name_field.source == DataSource.EXTRACTED_DATA
        
        # Email should come from user profile
        email_field = next((f for f in filled_fields if f.field_id == "email"), None)
        assert email_field.source == DataSource.USER_PROFILE
        
        # Mobile should come from DigiLocker
        mobile_field = next((f for f in filled_fields if f.field_id == "mobile"), None)
        assert mobile_field.source == DataSource.DIGILOCKER
    
    def test_fill_form_validates_data(self, form_filler, sample_form_fields, extracted_data):
        """Test that filled fields are validated"""
        filled_fields = form_filler.fill_form_fields(
            sample_form_fields,
            extracted_data=extracted_data
        )
        
        # All filled fields should have validated flag
        for field in filled_fields:
            assert hasattr(field, 'validated')


class TestFormValidation:
    """Test form validation - Requirement 12.16"""
    
    def test_validate_valid_fields(self, form_filler, sample_form_fields):
        """Test validation of valid fields"""
        filled_fields = [
            FilledField(
                field_id="email",
                field_name="Email",
                value="john@example.com",
                source=DataSource.USER_PROFILE,
                confidence=0.8,
                validated=True
            ),
            FilledField(
                field_id="mobile",
                field_name="Mobile",
                value="9876543210",
                source=DataSource.DIGILOCKER,
                confidence=0.95,
                validated=True
            )
        ]
        
        validation_results = form_filler.validate_form_data(
            filled_fields,
            sample_form_fields
        )
        
        # Should have validation results
        assert len(validation_results) > 0
        
        # Email and mobile should be valid
        email_validation = next((v for v in validation_results if v.field_id == "email"), None)
        assert email_validation is not None
        assert email_validation.is_valid
    
    def test_validate_invalid_email(self, form_filler, sample_form_fields):
        """Test validation of invalid email"""
        filled_fields = [
            FilledField(
                field_id="email",
                field_name="Email",
                value="invalid-email",
                source=DataSource.USER_PROFILE,
                confidence=0.8,
                validated=False
            )
        ]
        
        validation_results = form_filler.validate_form_data(
            filled_fields,
            sample_form_fields
        )
        
        email_validation = next((v for v in validation_results if v.field_id == "email"), None)
        assert email_validation is not None
        assert not email_validation.is_valid
        assert "email" in email_validation.error_message.lower()
    
    def test_validate_invalid_mobile(self, form_filler, sample_form_fields):
        """Test validation of invalid mobile number"""
        filled_fields = [
            FilledField(
                field_id="mobile",
                field_name="Mobile",
                value="123",  # Too short
                source=DataSource.USER_PROFILE,
                confidence=0.8,
                validated=False
            )
        ]
        
        validation_results = form_filler.validate_form_data(
            filled_fields,
            sample_form_fields
        )
        
        mobile_validation = next((v for v in validation_results if v.field_id == "mobile"), None)
        assert mobile_validation is not None
        assert not mobile_validation.is_valid
    
    def test_validate_missing_required_fields(self, form_filler, sample_form_fields):
        """Test validation detects missing required fields"""
        # Only fill optional field
        filled_fields = [
            FilledField(
                field_id="address",
                field_name="Address",
                value="123 Main St",
                source=DataSource.EXTRACTED_DATA,
                confidence=0.9,
                validated=True
            )
        ]
        
        validation_results = form_filler.validate_form_data(
            filled_fields,
            sample_form_fields
        )
        
        # Should have validation errors for missing required fields
        errors = [v for v in validation_results if not v.is_valid]
        assert len(errors) > 0


class TestFormSummary:
    """Test form summary generation - Requirement 12.30"""
    
    def test_generate_form_summary(self, form_filler):
        """Test generating form summary for user review"""
        filled_fields = [
            FilledField(
                field_id="name",
                field_name="Name",
                value="John Doe",
                source=DataSource.EXTRACTED_DATA,
                confidence=0.9,
                validated=True
            ),
            FilledField(
                field_id="email",
                field_name="Email",
                value="john@example.com",
                source=DataSource.USER_PROFILE,
                confidence=0.8,
                validated=True
            )
        ]
        
        validation_results = [
            ValidationResult(field_id="name", is_valid=True),
            ValidationResult(field_id="email", is_valid=True)
        ]
        
        summary = form_filler.generate_form_summary(
            filled_fields,
            validation_results,
            total_fields=5
        )
        
        assert summary.total_fields == 5
        assert summary.filled_fields == 2
        assert len(summary.fields) == 2
        assert summary.ready_for_submission
    
    def test_summary_with_low_confidence_warning(self, form_filler):
        """Test summary includes warning for low confidence fields"""
        filled_fields = [
            FilledField(
                field_id="name",
                field_name="Name",
                value="John Doe",
                source=DataSource.EXTRACTED_DATA,
                confidence=0.5,  # Low confidence
                validated=True
            )
        ]
        
        validation_results = [
            ValidationResult(field_id="name", is_valid=True)
        ]
        
        summary = form_filler.generate_form_summary(
            filled_fields,
            validation_results,
            total_fields=1
        )
        
        assert len(summary.warnings) > 0
        assert any("low confidence" in w.lower() for w in summary.warnings)
    
    def test_summary_with_validation_errors(self, form_filler):
        """Test summary indicates validation errors"""
        filled_fields = [
            FilledField(
                field_id="email",
                field_name="Email",
                value="invalid",
                source=DataSource.USER_PROFILE,
                confidence=0.8,
                validated=False
            )
        ]
        
        validation_results = [
            ValidationResult(
                field_id="email",
                is_valid=False,
                error_message="Invalid email format"
            )
        ]
        
        summary = form_filler.generate_form_summary(
            filled_fields,
            validation_results,
            total_fields=1
        )
        
        assert not summary.ready_for_submission
        assert len(summary.warnings) > 0
        assert any("validation errors" in w.lower() for w in summary.warnings)
    
    def test_summary_with_user_profile_warning(self, form_filler):
        """Test summary warns about user profile data"""
        filled_fields = [
            FilledField(
                field_id="email",
                field_name="Email",
                value="john@example.com",
                source=DataSource.USER_PROFILE,
                confidence=0.8,
                validated=True
            )
        ]
        
        validation_results = [
            ValidationResult(field_id="email", is_valid=True)
        ]
        
        summary = form_filler.generate_form_summary(
            filled_fields,
            validation_results,
            total_fields=1
        )
        
        assert len(summary.warnings) > 0
        assert any("user profile" in w.lower() for w in summary.warnings)


class TestFieldValidators:
    """Test individual field validators"""
    
    def test_validate_email(self, form_filler):
        """Test email validation"""
        assert form_filler._validate_field_value("email", "john@example.com")
        assert not form_filler._validate_field_value("email", "invalid-email")
        assert not form_filler._validate_field_value("email", "")
    
    def test_validate_mobile(self, form_filler):
        """Test mobile number validation"""
        assert form_filler._validate_field_value("mobile", "9876543210")
        assert not form_filler._validate_field_value("mobile", "123")
        assert not form_filler._validate_field_value("mobile", "1234567890")  # Doesn't start with 6-9
    
    def test_validate_pincode(self, form_filler):
        """Test PIN code validation"""
        assert form_filler._validate_field_value("pincode", "123456")
        assert not form_filler._validate_field_value("pincode", "12345")
        assert not form_filler._validate_field_value("pincode", "1234567")
    
    def test_validate_aadhaar(self, form_filler):
        """Test Aadhaar number validation"""
        assert form_filler._validate_field_value("aadhaar", "123456789012")
        assert not form_filler._validate_field_value("aadhaar", "12345")
    
    def test_validate_pan(self, form_filler):
        """Test PAN validation"""
        assert form_filler._validate_field_value("pan", "ABCDE1234F")
        assert not form_filler._validate_field_value("pan", "ABC123")


class TestUnfilledFields:
    """Test getting unfilled fields"""
    
    def test_get_unfilled_fields(self, form_filler, sample_form_fields):
        """Test getting list of unfilled fields"""
        filled_fields = [
            FilledField(
                field_id="name",
                field_name="Name",
                value="John Doe",
                source=DataSource.EXTRACTED_DATA,
                confidence=0.9,
                validated=True
            )
        ]
        
        unfilled = form_filler.get_unfilled_fields(
            sample_form_fields,
            filled_fields
        )
        
        # Should have 4 unfilled fields (email, mobile, aadhaar, address)
        assert len(unfilled) == 4
        
        # Name should not be in unfilled
        assert not any(f.get("field_id") == "name" for f in unfilled)
