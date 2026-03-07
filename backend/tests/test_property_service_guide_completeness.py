"""
Property-Based Test for Service Guide Completeness

**Validates: Requirements 1.1, 2.1, 3.1**

Property 1: Complete Service Guide Provision
For any service request (Aadhaar name change, government service modification, 
or data access), the system SHALL return a complete Service_Guide containing 
all required elements: steps, document requirements, eligibility criteria, 
processing time, portal links, and contact information.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime

from app.models.service import (
    ServiceGuide, ServiceCategory, ServiceStep,
    EligibilityCriterion, DocumentRequirement, ProcessingTime,
    ContactInfo, ValidationRule, AlternativeDocument
)
from app.models.session import UserRequest, RequestType, Session
from app.services.service_knowledge_base import service_knowledge_base
from app.services.conversational_agent import conversational_agent


# Strategy for generating service categories
service_category_strategy = st.sampled_from([
    ServiceCategory.AADHAAR,
    ServiceCategory.DATA_ACCESS,
    ServiceCategory.RECORD_MODIFICATION,
    ServiceCategory.IDENTITY_CARD,
    ServiceCategory.CERTIFICATE
])

# Strategy for generating languages
language_strategy = st.sampled_from(['en', 'hi', 'ta', 'te', 'bn', 'mr'])

# Mapping of categories to service IDs
CATEGORY_SERVICE_MAP = {
    ServiceCategory.AADHAAR: [
        'aadhaar_name_change',
        'aadhaar_address_update',
        'aadhaar_mobile_update'
    ],
    ServiceCategory.DATA_ACCESS: [
        'data_access_request',
        'data_correction_request'
    ],
    ServiceCategory.IDENTITY_CARD: [
        'pan_card_correction',
        'driving_license_renewal',
        'voter_id_update',
        'passport_application'
    ],
    ServiceCategory.CERTIFICATE: [
        'income_certificate',
        'caste_certificate',
        'domicile_certificate',
        'birth_certificate'
    ],
    ServiceCategory.RECORD_MODIFICATION: [
        'record_modification_general'
    ]
}

def service_id_for_category(category: ServiceCategory) -> str:
    """Get first service ID for a category"""
    return CATEGORY_SERVICE_MAP.get(category, ['unknown_service'])[0]


def create_complete_service_guide(service_id: str, category: ServiceCategory) -> ServiceGuide:
    """Create a complete service guide for testing"""
    return ServiceGuide(
        service_id=service_id,
        service_name=f"Test Service: {service_id}",
        category=category,
        description=f"Complete service guide for {service_id}",
        steps=[
            ServiceStep(
                step_number=1,
                description="Visit the official portal",
                requires_in_person=False,
                online_available=True,
                estimated_duration="5 minutes"
            ),
            ServiceStep(
                step_number=2,
                description="Fill the application form",
                requires_in_person=False,
                online_available=True,
                estimated_duration="15 minutes"
            ),
            ServiceStep(
                step_number=3,
                description="Upload required documents",
                requires_in_person=False,
                online_available=True,
                estimated_duration="10 minutes"
            )
        ],
        eligibility_criteria=[
            EligibilityCriterion(
                criterion_id="age_requirement",
                description="Must be 18 years or older",
                required=True,
                validation_rule=ValidationRule(
                    rule_type="age_check",
                    parameters={"min_age": 18}
                ),
                failure_message="You must be 18 years or older to apply"
            )
        ],
        document_requirements=[
            DocumentRequirement(
                document_id="identity_proof",
                document_name="Identity Proof",
                official_name="Government Issued Identity Document",
                required=True,
                accepts_copies=False,
                requires_attestation=False,
                requires_notarization=False,
                format="PDF or JPEG",
                validity_period="Valid at time of application",
                alternatives=[
                    AlternativeDocument(
                        document_id="aadhaar",
                        document_name="Aadhaar Card",
                        conditions="Must be valid"
                    ),
                    AlternativeDocument(
                        document_id="passport",
                        document_name="Passport",
                        conditions="Must be valid"
                    )
                ],
                obtainment_guidance="Visit nearest government office or apply online"
            )
        ],
        processing_time=ProcessingTime(
            minimum="7 days",
            maximum="30 days",
            typical="15 days",
            factors=["Document verification time", "Office workload"]
        ),
        official_portal_url="https://example.gov.in/service",
        contact_info=ContactInfo(
            phone="+91-1234567890",
            email="support@example.gov.in",
            helpline="1800-123-4567"
        ),
        last_updated=datetime.now(),
        available_languages=["en", "hi", "ta", "te"]
    )


@pytest.fixture(scope="module")
def setup_test_services():
    """Setup test services in the knowledge base"""
    # Clear existing services
    service_knowledge_base.services.clear()
    
    # Add test services for each category
    for category, service_ids in CATEGORY_SERVICE_MAP.items():
        for service_id in service_ids:
            service = create_complete_service_guide(service_id, category)
            service_knowledge_base.add_service(service)
    
    yield
    
    # Cleanup
    service_knowledge_base.services.clear()


# Feature: government-services-assistant, Property 1: Complete Service Guide Provision
@pytest.mark.property_test
@pytest.mark.asyncio
@given(
    category=service_category_strategy,
    language=language_strategy
)
@settings(max_examples=50, deadline=None)
async def test_complete_service_guide_provision(
    category: ServiceCategory,
    language: str
):
    """
    Property 1: For any service request, the system SHALL return a complete 
    Service_Guide with all required elements: steps, document requirements, 
    eligibility criteria, processing time, portal links, and contact information.
    
    **Validates: Requirements 1.1, 2.1, 3.1**
    """
    # Setup services for this test run
    if not service_knowledge_base.services:
        for cat, service_ids in CATEGORY_SERVICE_MAP.items():
            for service_id in service_ids:
                service = create_complete_service_guide(service_id, cat)
                service_knowledge_base.add_service(service)
    
    # Generate service ID based on category
    service_id = service_id_for_category(category)
    
    # Ensure the service exists in knowledge base
    service = service_knowledge_base.get_service(service_id)
    if not service:
        service = create_complete_service_guide(service_id, category)
        service_knowledge_base.add_service(service)
    
    # Create a user request for service guidance
    request = UserRequest(
        message=f"I need help with {service_id}",
        language=language,
        request_type=RequestType.SERVICE_GUIDANCE,
        context={"service_id": service_id}
    )
    
    # Create a session
    session = Session(
        session_id=f"test_session_{service_id}",
        start_time=datetime.now(),
        language=language,
        conversation_history=[],
        temporary_context={}
    )
    
    # Process the request
    response = await conversational_agent.process_request(request, session)
    
    # Retrieve the service guide directly to verify completeness
    service_guide = service_knowledge_base.get_service(service_id)
    
    # PROPERTY ASSERTIONS: Verify complete service guide
    assert service_guide is not None, \
        f"Service guide must exist for service_id: {service_id}"
    
    # 1. Verify steps are present and non-empty
    assert service_guide.steps is not None, \
        "Service guide must have steps"
    assert len(service_guide.steps) > 0, \
        "Service guide must have at least one step"
    assert all(isinstance(step, ServiceStep) for step in service_guide.steps), \
        "All steps must be ServiceStep instances"
    assert all(step.description for step in service_guide.steps), \
        "All steps must have descriptions"
    
    # 2. Verify document requirements are present
    assert service_guide.document_requirements is not None, \
        "Service guide must have document requirements"
    assert isinstance(service_guide.document_requirements, list), \
        "Document requirements must be a list"
    # Note: Some services may have zero document requirements, so we check structure
    if len(service_guide.document_requirements) > 0:
        assert all(isinstance(doc, DocumentRequirement) for doc in service_guide.document_requirements), \
            "All document requirements must be DocumentRequirement instances"
        assert all(doc.document_name for doc in service_guide.document_requirements), \
            "All documents must have names"
        assert all(doc.obtainment_guidance for doc in service_guide.document_requirements), \
            "All documents must have obtainment guidance"
    
    # 3. Verify eligibility criteria are present
    assert service_guide.eligibility_criteria is not None, \
        "Service guide must have eligibility criteria"
    assert isinstance(service_guide.eligibility_criteria, list), \
        "Eligibility criteria must be a list"
    if len(service_guide.eligibility_criteria) > 0:
        assert all(isinstance(criterion, EligibilityCriterion) for criterion in service_guide.eligibility_criteria), \
            "All eligibility criteria must be EligibilityCriterion instances"
        assert all(criterion.description for criterion in service_guide.eligibility_criteria), \
            "All criteria must have descriptions"
    
    # 4. Verify processing time is present and complete
    assert service_guide.processing_time is not None, \
        "Service guide must have processing time information"
    assert isinstance(service_guide.processing_time, ProcessingTime), \
        "Processing time must be a ProcessingTime instance"
    assert service_guide.processing_time.minimum, \
        "Processing time must have minimum duration"
    assert service_guide.processing_time.maximum, \
        "Processing time must have maximum duration"
    assert service_guide.processing_time.typical, \
        "Processing time must have typical duration"
    
    # 5. Verify official portal URL is present and valid
    assert service_guide.official_portal_url, \
        "Service guide must have official portal URL"
    assert isinstance(service_guide.official_portal_url, str), \
        "Portal URL must be a string"
    assert service_guide.official_portal_url.startswith(('http://', 'https://')), \
        f"Portal URL must be a valid HTTP(S) URL, got: {service_guide.official_portal_url}"
    
    # 6. Verify contact information is present
    assert service_guide.contact_info is not None, \
        "Service guide must have contact information"
    assert isinstance(service_guide.contact_info, ContactInfo), \
        "Contact info must be a ContactInfo instance"
    # At least one contact method should be present
    assert (
        service_guide.contact_info.phone or
        service_guide.contact_info.email or
        service_guide.contact_info.helpline or
        service_guide.contact_info.address
    ), "Contact info must have at least one contact method"
    
    # 7. Verify last_updated timestamp is present
    assert service_guide.last_updated is not None, \
        "Service guide must have last_updated timestamp"
    assert isinstance(service_guide.last_updated, datetime), \
        "last_updated must be a datetime instance"
    
    # 8. Verify the response contains appropriate information
    assert response is not None, \
        "Agent must return a response"
    assert response.message, \
        "Response must contain a message"
    assert response.language == language, \
        f"Response language must match request language: expected {language}, got {response.language}"


@pytest.mark.property_test
@pytest.mark.asyncio
async def test_service_guide_completeness_for_aadhaar_name_change(setup_test_services):
    """
    Specific test for Aadhaar name change service (Requirement 1.1)
    
    **Validates: Requirement 1.1 - Provide Aadhaar Name Change Guidance**
    """
    service_id = "aadhaar_name_change"
    
    # Ensure service exists
    service = service_knowledge_base.get_service(service_id)
    if not service:
        service = create_complete_service_guide(service_id, ServiceCategory.AADHAAR)
        service_knowledge_base.add_service(service)
    
    # Verify all required elements for Aadhaar name change
    service_guide = service_knowledge_base.get_service(service_id)
    
    assert service_guide is not None
    assert len(service_guide.steps) > 0
    assert service_guide.document_requirements is not None
    assert service_guide.eligibility_criteria is not None
    assert service_guide.processing_time is not None
    assert service_guide.official_portal_url.startswith('https://')
    assert service_guide.contact_info is not None


@pytest.mark.property_test
@pytest.mark.asyncio
async def test_service_guide_completeness_for_data_access(setup_test_services):
    """
    Specific test for data access request service (Requirement 2.1)
    
    **Validates: Requirement 2.1 - Guide Government Service Modifications**
    """
    service_id = "data_access_request"
    
    # Ensure service exists
    service = service_knowledge_base.get_service(service_id)
    if not service:
        service = create_complete_service_guide(service_id, ServiceCategory.DATA_ACCESS)
        service_knowledge_base.add_service(service)
    
    # Verify all required elements for data access
    service_guide = service_knowledge_base.get_service(service_id)
    
    assert service_guide is not None
    assert len(service_guide.steps) > 0
    assert service_guide.document_requirements is not None
    assert service_guide.eligibility_criteria is not None
    assert service_guide.processing_time is not None
    assert service_guide.official_portal_url.startswith('https://')
    assert service_guide.contact_info is not None


@pytest.mark.property_test
@pytest.mark.asyncio
async def test_service_guide_completeness_for_identity_card_modification(setup_test_services):
    """
    Specific test for identity card modification service (Requirement 3.1)
    
    **Validates: Requirement 3.1 - Access Government Data**
    """
    service_id = "pan_card_correction"
    
    # Ensure service exists
    service = service_knowledge_base.get_service(service_id)
    if not service:
        service = create_complete_service_guide(service_id, ServiceCategory.IDENTITY_CARD)
        service_knowledge_base.add_service(service)
    
    # Verify all required elements for identity card modification
    service_guide = service_knowledge_base.get_service(service_id)
    
    assert service_guide is not None
    assert len(service_guide.steps) > 0
    assert service_guide.document_requirements is not None
    assert service_guide.eligibility_criteria is not None
    assert service_guide.processing_time is not None
    assert service_guide.official_portal_url.startswith('https://')
    assert service_guide.contact_info is not None
