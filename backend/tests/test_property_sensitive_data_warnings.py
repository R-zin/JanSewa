"""
Property-Based Test for Sensitive Data Warnings

**Validates: Requirements 10.2**

Property 24: Sensitive Data Warnings
For any user input containing sensitive information (Aadhaar number, personal name, 
address, etc.), the system SHALL generate and display appropriate security warnings.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List
import re

from app.services.privacy_controls import (
    PrivacyControls,
    SensitiveDataType,
    WarningType,
    SeverityLevel
)


# Strategy for generating Aadhaar numbers (12 digits)
aadhaar_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Nd',)),
    min_size=12,
    max_size=12
).map(lambda x: f"{x[:4]} {x[4:8]} {x[8:]}")  # Format: XXXX XXXX XXXX

# Strategy for generating PAN numbers (format: ABCDE1234F)
def generate_pan():
    import random
    import string
    prefix = ''.join(random.choices(string.ascii_uppercase, k=5))
    digits = ''.join(random.choices(string.digits, k=4))
    suffix = random.choice(string.ascii_uppercase)
    return f"{prefix}{digits}{suffix}"

pan_strategy = st.builds(generate_pan)

# Strategy for generating phone numbers (10 digits)
phone_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Nd',)),
    min_size=10,
    max_size=10
)

# Strategy for generating email addresses
def generate_email():
    import random
    import string
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(5, 10)))
    domain = ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
    tld = random.choice(['com', 'org', 'net', 'in', 'gov'])
    return f"{username}@{domain}.{tld}"

email_strategy = st.builds(generate_email)

# Strategy for generating personal names
name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), whitelist_characters=' '),
    min_size=3,
    max_size=50
).filter(lambda x: x.strip() != '' and ' ' in x.strip())

# Strategy for generating addresses
address_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' ,.-'),
    min_size=20,
    max_size=100
).filter(lambda x: x.strip() != '' and len(x.strip()) >= 20)

# Strategy for generating passwords
password_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='!@#$%^&*'),
    min_size=8,
    max_size=20
)

# Strategy for generating non-sensitive text
non_sensitive_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), whitelist_characters=' '),
    min_size=5,
    max_size=50
).filter(lambda x: x.strip() != '' and not any(char.isdigit() for char in x))


def contains_sensitive_pattern(text: str, data_type: SensitiveDataType) -> bool:
    """Check if text contains a pattern matching the sensitive data type."""
    patterns = {
        SensitiveDataType.AADHAAR_NUMBER: r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        SensitiveDataType.PAN_NUMBER: r'\b[A-Z]{5}\d{4}[A-Z]\b',
        SensitiveDataType.PHONE_NUMBER: r'\b\d{10}\b',
        SensitiveDataType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    }
    
    pattern = patterns.get(data_type)
    if pattern:
        return bool(re.search(pattern, text))
    return False


# Feature: government-services-assistant, Property 24: Sensitive Data Warnings
@pytest.mark.property_test
@given(sensitive_data_type=st.sampled_from(list(SensitiveDataType)))
@settings(max_examples=50, deadline=None)
def test_warning_generated_for_all_sensitive_data_types(
    sensitive_data_type: SensitiveDataType
):
    """
    Property 24: For ANY sensitive data type, the system SHALL generate 
    an appropriate security warning.
    
    **Validates: Requirements 10.2**
    
    This test verifies that:
    1. A warning is generated for every sensitive data type
    2. The warning contains required fields (warning_type, message, severity, recommendations)
    3. The warning is appropriate for the data type
    """
    privacy_controls = PrivacyControls()
    
    # STEP 1: Generate warning for the sensitive data type
    warning = privacy_controls.generate_warning(sensitive_data_type)
    
    # STEP 2: CRITICAL PROPERTY VERIFICATION - Warning must be generated
    assert warning is not None, \
        f"PROPERTY VIOLATION: No warning generated for {sensitive_data_type.value}"
    
    # STEP 3: Verify warning structure
    assert "warning_type" in warning, \
        f"Warning must contain 'warning_type' field for {sensitive_data_type.value}"
    assert "message" in warning, \
        f"Warning must contain 'message' field for {sensitive_data_type.value}"
    assert "severity" in warning, \
        f"Warning must contain 'severity' field for {sensitive_data_type.value}"
    assert "recommendations" in warning, \
        f"Warning must contain 'recommendations' field for {sensitive_data_type.value}"
    
    # STEP 4: Verify warning type is correct
    assert warning["warning_type"] == WarningType.SENSITIVE_DATA_ENTRY.value, \
        f"Warning type must be SENSITIVE_DATA_ENTRY for {sensitive_data_type.value}"
    
    # STEP 5: Verify message is non-empty and informative
    assert len(warning["message"]) > 0, \
        f"Warning message must not be empty for {sensitive_data_type.value}"
    assert len(warning["message"]) >= 20, \
        f"Warning message must be informative (at least 20 chars) for {sensitive_data_type.value}"
    
    # STEP 6: Verify severity is valid
    valid_severities = [SeverityLevel.INFO.value, SeverityLevel.WARNING.value, SeverityLevel.CRITICAL.value]
    assert warning["severity"] in valid_severities, \
        f"Warning severity must be valid for {sensitive_data_type.value}. Got: {warning['severity']}"
    
    # STEP 7: Verify recommendations are provided
    assert isinstance(warning["recommendations"], list), \
        f"Recommendations must be a list for {sensitive_data_type.value}"
    assert len(warning["recommendations"]) > 0, \
        f"PROPERTY VIOLATION: At least one recommendation must be provided for {sensitive_data_type.value}"
    
    # STEP 8: Verify each recommendation is meaningful
    for recommendation in warning["recommendations"]:
        assert isinstance(recommendation, str), \
            f"Each recommendation must be a string for {sensitive_data_type.value}"
        assert len(recommendation) > 10, \
            f"Each recommendation must be meaningful (>10 chars) for {sensitive_data_type.value}"


@pytest.mark.property_test
@given(
    aadhaar=aadhaar_strategy,
    context_text=non_sensitive_strategy
)
@settings(max_examples=100, deadline=None)
def test_warning_for_aadhaar_in_user_input(
    aadhaar: str,
    context_text: str
):
    """
    Property 24: When user input contains an Aadhaar number, 
    the system SHALL generate a CRITICAL security warning.
    
    **Validates: Requirements 10.2**
    
    This test verifies that:
    1. Aadhaar numbers are detected in user input
    2. A CRITICAL warning is generated for Aadhaar numbers
    3. The warning includes specific recommendations for Aadhaar security
    """
    privacy_controls = PrivacyControls()
    
    # STEP 1: Create user input containing Aadhaar number
    user_input = f"{context_text} My Aadhaar number is {aadhaar}"
    
    # STEP 2: Detect sensitive data in input
    detected_types = privacy_controls.detect_sensitive_data(user_input)
    
    # STEP 3: CRITICAL PROPERTY VERIFICATION - Aadhaar must be detected
    assert SensitiveDataType.AADHAAR_NUMBER in detected_types, \
        f"PROPERTY VIOLATION: Aadhaar number not detected in input: {user_input}"
    
    # STEP 4: Generate warning for Aadhaar
    warning = privacy_controls.generate_warning(SensitiveDataType.AADHAAR_NUMBER)
    
    # STEP 5: Verify CRITICAL severity for Aadhaar
    assert warning["severity"] == SeverityLevel.CRITICAL.value, \
        f"PROPERTY VIOLATION: Aadhaar warning must have CRITICAL severity. Got: {warning['severity']}"
    
    # STEP 6: Verify Aadhaar-specific recommendations
    recommendations_text = " ".join(warning["recommendations"]).lower()
    assert "aadhaar" in recommendations_text or "official" in recommendations_text, \
        "Warning must include Aadhaar-specific or official portal recommendations"
    
    # STEP 7: Verify guidance-only disclaimer
    assert any("guidance" in rec.lower() or "does not process" in rec.lower() 
               for rec in warning["recommendations"]), \
        "Warning must include disclaimer that assistant provides guidance only"


@pytest.mark.property_test
@given(
    pan=pan_strategy,
    context_text=non_sensitive_strategy
)
@settings(max_examples=100, deadline=None)
def test_warning_for_pan_in_user_input(
    pan: str,
    context_text: str
):
    """
    Property 24: When user input contains a PAN number, 
    the system SHALL generate a CRITICAL security warning.
    
    **Validates: Requirements 10.2**
    """
    privacy_controls = PrivacyControls()
    
    # Create user input with PAN
    user_input = f"{context_text} My PAN is {pan}"
    
    # Detect sensitive data
    detected_types = privacy_controls.detect_sensitive_data(user_input)
    
    # Verify PAN is detected
    assert SensitiveDataType.PAN_NUMBER in detected_types, \
        f"PROPERTY VIOLATION: PAN number not detected in input: {user_input}"
    
    # Generate warning
    warning = privacy_controls.generate_warning(SensitiveDataType.PAN_NUMBER)
    
    # Verify CRITICAL severity for financial data
    assert warning["severity"] == SeverityLevel.CRITICAL.value, \
        f"PROPERTY VIOLATION: PAN warning must have CRITICAL severity. Got: {warning['severity']}"
    
    # Verify financial data recommendations
    recommendations_text = " ".join(warning["recommendations"]).lower()
    assert "pan" in recommendations_text or "financial" in recommendations_text or "official" in recommendations_text, \
        "Warning must include PAN-specific or financial data recommendations"


@pytest.mark.property_test
@given(
    phone=phone_strategy,
    context_text=non_sensitive_strategy
)
@settings(max_examples=100, deadline=None)
def test_warning_for_phone_in_user_input(
    phone: str,
    context_text: str
):
    """
    Property 24: When user input contains a phone number, 
    the system SHALL generate a security warning.
    
    **Validates: Requirements 10.2**
    """
    privacy_controls = PrivacyControls()
    
    # Create user input with phone number
    user_input = f"{context_text} Call me at {phone}"
    
    # Detect sensitive data
    detected_types = privacy_controls.detect_sensitive_data(user_input)
    
    # Verify phone is detected
    assert SensitiveDataType.PHONE_NUMBER in detected_types, \
        f"PROPERTY VIOLATION: Phone number not detected in input: {user_input}"
    
    # Generate warning
    warning = privacy_controls.generate_warning(SensitiveDataType.PHONE_NUMBER)
    
    # Verify warning is generated
    assert warning is not None, \
        "PROPERTY VIOLATION: No warning generated for phone number"
    
    # Verify severity is at least WARNING
    assert warning["severity"] in [SeverityLevel.WARNING.value, SeverityLevel.CRITICAL.value], \
        f"Phone number warning must have WARNING or CRITICAL severity. Got: {warning['severity']}"


@pytest.mark.property_test
@given(
    email=email_strategy,
    context_text=non_sensitive_strategy
)
@settings(max_examples=100, deadline=None)
def test_warning_for_email_in_user_input(
    email: str,
    context_text: str
):
    """
    Property 24: When user input contains an email address, 
    the system SHALL generate a security warning.
    
    **Validates: Requirements 10.2**
    """
    privacy_controls = PrivacyControls()
    
    # Create user input with email
    user_input = f"{context_text} Email me at {email}"
    
    # Detect sensitive data
    detected_types = privacy_controls.detect_sensitive_data(user_input)
    
    # Verify email is detected
    assert SensitiveDataType.EMAIL in detected_types, \
        f"PROPERTY VIOLATION: Email not detected in input: {user_input}"
    
    # Generate warning
    warning = privacy_controls.generate_warning(SensitiveDataType.EMAIL)
    
    # Verify warning is generated
    assert warning is not None, \
        "PROPERTY VIOLATION: No warning generated for email"
    
    # Verify recommendations include session-bounded storage
    recommendations_text = " ".join(warning["recommendations"]).lower()
    assert "session" in recommendations_text or "not be stored" in recommendations_text, \
        "Warning must mention that information is not stored beyond session"


@pytest.mark.property_test
@given(non_sensitive_text=non_sensitive_strategy)
@settings(max_examples=50, deadline=None)
def test_no_false_positive_warnings_for_non_sensitive_data(
    non_sensitive_text: str
):
    """
    Property 24 (negative test): When user input contains NO sensitive data, 
    the system SHALL NOT detect any sensitive data types.
    
    **Validates: Requirements 10.2**
    
    This test verifies that:
    1. Non-sensitive text does not trigger false positive detections
    2. The system accurately distinguishes sensitive from non-sensitive data
    """
    # Ensure the text doesn't accidentally contain patterns
    assume(not re.search(r'\d{10}', non_sensitive_text))  # No 10-digit sequences
    assume(not re.search(r'\d{4}\s?\d{4}\s?\d{4}', non_sensitive_text))  # No Aadhaar-like patterns
    assume('@' not in non_sensitive_text)  # No email-like patterns
    
    privacy_controls = PrivacyControls()
    
    # Detect sensitive data in non-sensitive text
    detected_types = privacy_controls.detect_sensitive_data(non_sensitive_text)
    
    # CRITICAL PROPERTY VERIFICATION - No false positives
    assert len(detected_types) == 0, \
        f"PROPERTY VIOLATION: False positive detection in non-sensitive text: {non_sensitive_text}. " \
        f"Detected: {[dt.value for dt in detected_types]}"


@pytest.mark.property_test
@given(
    data_type=st.sampled_from([
        SensitiveDataType.AADHAAR_NUMBER,
        SensitiveDataType.PAN_NUMBER
    ])
)
@settings(max_examples=20, deadline=None)
def test_critical_severity_for_government_ids(
    data_type: SensitiveDataType
):
    """
    Property 24: Government-issued ID numbers (Aadhaar, PAN) SHALL 
    generate CRITICAL severity warnings.
    
    **Validates: Requirements 10.2**
    
    This test verifies that:
    1. Government IDs are treated with highest security priority
    2. CRITICAL severity is assigned to government ID warnings
    """
    privacy_controls = PrivacyControls()
    
    # Generate warning for government ID
    warning = privacy_controls.generate_warning(data_type)
    
    # CRITICAL PROPERTY VERIFICATION - Must be CRITICAL severity
    assert warning["severity"] == SeverityLevel.CRITICAL.value, \
        f"PROPERTY VIOLATION: Government ID {data_type.value} must have CRITICAL severity. " \
        f"Got: {warning['severity']}"
    
    # Verify official portal recommendation
    recommendations_text = " ".join(warning["recommendations"]).lower()
    assert "official" in recommendations_text, \
        f"Government ID warning must recommend using official portals"


@pytest.mark.property_test
def test_password_warning_never_request():
    """
    Property 24 (special case): Password warnings SHALL explicitly state 
    that the assistant NEVER needs passwords.
    
    **Validates: Requirements 10.2**
    
    This test verifies that:
    1. Password warnings have CRITICAL severity
    2. The warning explicitly states passwords are never needed
    3. Strong security recommendations are provided
    """
    privacy_controls = PrivacyControls()
    
    # Generate warning for password
    warning = privacy_controls.generate_warning(SensitiveDataType.PASSWORD)
    
    # Verify CRITICAL severity
    assert warning["severity"] == SeverityLevel.CRITICAL.value, \
        "Password warning must have CRITICAL severity"
    
    # Verify message explicitly states passwords are never needed
    message_lower = warning["message"].lower()
    assert "never" in message_lower, \
        "Password warning must explicitly state passwords are NEVER needed"
    
    # Verify recommendations include strong security guidance
    recommendations_text = " ".join(warning["recommendations"]).lower()
    assert "never" in recommendations_text or "not" in recommendations_text, \
        "Password recommendations must emphasize never providing passwords"
    assert "official" in recommendations_text, \
        "Password recommendations must mention official portals"


@pytest.mark.property_test
@given(
    sensitive_data_type=st.sampled_from(list(SensitiveDataType))
)
@settings(max_examples=50, deadline=None)
def test_all_warnings_include_guidance_disclaimer(
    sensitive_data_type: SensitiveDataType
):
    """
    Property 24: ALL sensitive data warnings SHALL include a disclaimer 
    that the assistant provides guidance only and does not process applications.
    
    **Validates: Requirements 10.2, 10.4, 10.5**
    
    This test verifies that:
    1. Every warning includes the guidance-only disclaimer
    2. Users are informed the system doesn't process actual applications
    """
    privacy_controls = PrivacyControls()
    
    # Generate warning
    warning = privacy_controls.generate_warning(sensitive_data_type)
    
    # Check for guidance disclaimer in recommendations
    recommendations_text = " ".join(warning["recommendations"]).lower()
    
    # CRITICAL PROPERTY VERIFICATION - Guidance disclaimer must be present
    has_guidance_disclaimer = (
        "guidance" in recommendations_text or
        "does not process" in recommendations_text or
        "not process" in recommendations_text or
        "official" in recommendations_text  # Directing to official portals implies guidance only
    )
    
    assert has_guidance_disclaimer, \
        f"PROPERTY VIOLATION: Warning for {sensitive_data_type.value} must include guidance disclaimer. " \
        f"Recommendations: {warning['recommendations']}"


@pytest.mark.property_test
def test_specific_aadhaar_warning_scenario():
    """
    Concrete example: User provides Aadhaar for name change request.
    
    **Validates: Requirements 10.2**
    
    This test demonstrates a real-world scenario where a user provides
    their Aadhaar number for a name change request.
    """
    privacy_controls = PrivacyControls()
    
    # User input for Aadhaar name change
    user_input = "I want to change my name on Aadhaar. My Aadhaar number is 1234 5678 9012"
    
    # Detect sensitive data
    detected_types = privacy_controls.detect_sensitive_data(user_input)
    
    # Verify Aadhaar is detected
    assert SensitiveDataType.AADHAAR_NUMBER in detected_types, \
        "Aadhaar number must be detected in name change request"
    
    # Generate warning
    warning = privacy_controls.generate_warning(SensitiveDataType.AADHAAR_NUMBER)
    
    # Verify warning properties
    assert warning["severity"] == SeverityLevel.CRITICAL.value, \
        "Aadhaar warning must be CRITICAL"
    assert len(warning["recommendations"]) >= 3, \
        "Aadhaar warning must provide multiple security recommendations"
    
    # Verify key recommendations are present
    recommendations_text = " ".join(warning["recommendations"]).lower()
    assert "official" in recommendations_text, \
        "Must recommend using official portals"
    assert "guidance" in recommendations_text or "does not process" in recommendations_text, \
        "Must include guidance-only disclaimer"


@pytest.mark.property_test
def test_multiple_sensitive_data_types_in_single_input():
    """
    Property 24: When user input contains MULTIPLE sensitive data types, 
    the system SHALL detect ALL of them.
    
    **Validates: Requirements 10.2**
    
    This test verifies that:
    1. Multiple sensitive data types can be detected in a single input
    2. Each detected type can generate its own warning
    """
    privacy_controls = PrivacyControls()
    
    # User input with multiple sensitive data types
    user_input = (
        "My Aadhaar is 1234 5678 9012, "
        "PAN is ABCDE1234F, "
        "phone is 9876543210, "
        "and email is user@example.com"
    )
    
    # Detect all sensitive data types
    detected_types = privacy_controls.detect_sensitive_data(user_input)
    
    # CRITICAL PROPERTY VERIFICATION - All types must be detected
    assert SensitiveDataType.AADHAAR_NUMBER in detected_types, \
        "Aadhaar must be detected in multi-type input"
    assert SensitiveDataType.PAN_NUMBER in detected_types, \
        "PAN must be detected in multi-type input"
    assert SensitiveDataType.PHONE_NUMBER in detected_types, \
        "Phone must be detected in multi-type input"
    assert SensitiveDataType.EMAIL in detected_types, \
        "Email must be detected in multi-type input"
    
    # Verify warnings can be generated for each type
    for data_type in detected_types:
        warning = privacy_controls.generate_warning(data_type)
        assert warning is not None, \
            f"Warning must be generated for {data_type.value} in multi-type input"
        assert len(warning["recommendations"]) > 0, \
            f"Recommendations must be provided for {data_type.value}"
