from datetime import datetime
from app.models.service import (
    ServiceGuide, ServiceCategory, ServiceStep,
    EligibilityCriterion, DocumentRequirement, ProcessingTime,
    ContactInfo, AlternativeDocument, ValidationRule
)


# Aadhaar Name Change Service
aadhaar_name_change = ServiceGuide(
    service_id="aadhaar_name_change",
    service_name="Aadhaar Name Change",
    category=ServiceCategory.AADHAAR,
    description="Update your name on Aadhaar card",
    steps=[
        ServiceStep(
            step_number=1,
            description="Visit UIDAI self-service portal or Aadhaar center",
            requires_in_person=False,
            online_available=True,
            estimated_duration="10 minutes"
        ),
        ServiceStep(
            step_number=2,
            description="Login with Aadhaar number and OTP",
            requires_in_person=False,
            online_available=True,
            estimated_duration="5 minutes"
        ),
        ServiceStep(
            step_number=3,
            description="Select 'Update Aadhaar' and choose name correction/change",
            requires_in_person=False,
            online_available=True,
            estimated_duration="5 minutes"
        ),
        ServiceStep(
            step_number=4,
            description="Upload supporting documents",
            requires_in_person=False,
            online_available=True,
            estimated_duration="10 minutes"
        ),
        ServiceStep(
            step_number=5,
            description="Pay fee and submit request",
            requires_in_person=False,
            online_available=True,
            estimated_duration="5 minutes"
        )
    ],
    eligibility_criteria=[
        EligibilityCriterion(
            criterion_id="has_aadhaar",
            description="Must have existing Aadhaar card",
            required=True,
            validation_rule=ValidationRule(rule_type="exists", parameters={}),
            failure_message="You need an existing Aadhaar card to update it"
        )
    ],
    document_requirements=[
        DocumentRequirement(
            document_id="proof_of_identity",
            document_name="Proof of Identity",
            official_name="POI Document",
            required=True,
            accepts_copies=False,
            requires_attestation=True,
            requires_notarization=False,
            alternatives=[
                AlternativeDocument(
                    document_id="passport",
                    document_name="Passport",
                    conditions="Valid passport"
                ),
                AlternativeDocument(
                    document_id="pan_card",
                    document_name="PAN Card",
                    conditions="Valid PAN card"
                )
            ],
            obtainment_guidance="Visit nearest government office"
        )
    ],
    processing_time=ProcessingTime(
        minimum="7 days",
        maximum="90 days",
        typical="30 days",
        factors=["Document verification time", "Center workload"]
    ),
    official_portal_url="https://myaadhaar.uidai.gov.in",
    contact_info=ContactInfo(
        phone="1947",
        email="help@uidai.gov.in",
        helpline="1947 (toll-free)"
    ),
    last_updated=datetime.utcnow(),
    available_languages=["en", "hi"]
)


# OBC Certificate Service
obc_certificate = ServiceGuide(
    service_id="obc_certificate",
    service_name="OBC Certificate Application",
    category=ServiceCategory.CERTIFICATE,
    description="Apply for Other Backward Classes certificate",
    steps=[
        ServiceStep(
            step_number=1,
            description="Visit state government portal or Tehsil office",
            requires_in_person=False,
            online_available=True,
            estimated_duration="15 minutes"
        ),
        ServiceStep(
            step_number=2,
            description="Fill application form with personal details",
            requires_in_person=False,
            online_available=True,
            estimated_duration="20 minutes"
        ),
        ServiceStep(
            step_number=3,
            description="Upload required documents",
            requires_in_person=False,
            online_available=True,
            estimated_duration="10 minutes"
        ),
        ServiceStep(
            step_number=4,
            description="Submit application and pay fee",
            requires_in_person=False,
            online_available=True,
            estimated_duration="5 minutes"
        ),
        ServiceStep(
            step_number=5,
            description="Attend verification if required",
            requires_in_person=True,
            online_available=False,
            estimated_duration="1 hour",
            notes="May be required based on state rules"
        )
    ],
    eligibility_criteria=[
        EligibilityCriterion(
            criterion_id="belongs_to_obc",
            description="Must belong to OBC category",
            required=True,
            validation_rule=ValidationRule(rule_type="category_check", parameters={}),
            failure_message="Applicant must belong to OBC category"
        )
    ],
    document_requirements=[
        DocumentRequirement(
            document_id="identity_proof",
            document_name="Identity Proof",
            official_name="Identity Document",
            required=True,
            accepts_copies=True,
            requires_attestation=True,
            requires_notarization=False,
            alternatives=[],
            obtainment_guidance="Aadhaar or Voter ID"
        ),
        DocumentRequirement(
            document_id="address_proof",
            document_name="Address Proof",
            official_name="Residence Proof",
            required=True,
            accepts_copies=True,
            requires_attestation=True,
            requires_notarization=False,
            alternatives=[],
            obtainment_guidance="Utility bill or rent agreement"
        )
    ],
    processing_time=ProcessingTime(
        minimum="15 days",
        maximum="60 days",
        typical="30 days",
        factors=["Verification process", "Office workload"]
    ),
    official_portal_url="https://edistrict.gov.in",
    contact_info=ContactInfo(
        phone="1800-XXX-XXXX",
        email="support@edistrict.gov.in"
    ),
    last_updated=datetime.utcnow(),
    available_languages=["en", "hi"]
)


# Service registry
SERVICES_REGISTRY = {
    "aadhaar_name_change": aadhaar_name_change,
    "obc_certificate": obc_certificate
}
