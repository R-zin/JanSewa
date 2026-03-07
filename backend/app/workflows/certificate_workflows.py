"""
Workflow Definitions for Certificate Services

Defines automation workflows for various certificate applications.
"""

from app.models.automation import (
    WorkflowDefinition, WorkflowStep, FieldMapping
)


def get_income_certificate_workflow() -> WorkflowDefinition:
    """Workflow for income certificate application"""
    return WorkflowDefinition(
        workflow_id="income_certificate",
        service_id="income_certificate",
        name="Income Certificate Application",
        description="Apply for income certificate online",
        portal_url="https://edistrict.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Login to e-District",
                description="Login to state e-district portal",
                page_url="https://edistrict.gov.in/login",
                actions=[
                    {"type": "fill_field", "field_id": "username", "data_source": "credentials.username"},
                    {"type": "fill_field", "field_id": "password", "data_source": "credentials.password"},
                    {"type": "wait_for_user", "prompt": "Complete CAPTCHA"}
                ],
                expected_elements=["username", "password"],
                success_indicators=["dashboard"]
            ),
            WorkflowStep(
                step_number=2,
                name="Select Income Certificate",
                description="Choose income certificate service",
                page_url="https://edistrict.gov.in/services",
                actions=[
                    {"type": "click", "element_id": "income_certificate_option"}
                ],
                expected_elements=["income_certificate_option"],
                success_indicators=["application_form"]
            ),
            WorkflowStep(
                step_number=3,
                name="Fill Application Form",
                description="Enter applicant details",
                page_url="https://edistrict.gov.in/income-certificate/form",
                actions=[
                    {"type": "fill_field", "field_id": "applicant_name", "data_source": "extracted_data.name"},
                    {"type": "fill_field", "field_id": "father_name", "data_source": "extracted_data.father_name"},
                    {"type": "fill_field", "field_id": "address", "data_source": "extracted_data.address"},
                    {"type": "fill_field", "field_id": "mobile", "data_source": "user_profile.mobile"},
                    {"type": "fill_field", "field_id": "purpose", "data_source": "user_input.purpose"},
                    {"type": "upload_document", "field_id": "identity_proof"},
                    {"type": "upload_document", "field_id": "address_proof"}
                ],
                expected_elements=["applicant_name", "father_name", "address"],
                success_indicators=["form_complete"]
            ),
            WorkflowStep(
                step_number=4,
                name="Submit Application",
                description="Review and submit",
                page_url="https://edistrict.gov.in/income-certificate/submit",
                actions=[
                    {"type": "wait_for_user", "prompt": "Review application details"},
                    {"type": "click", "element_id": "submit_button"}
                ],
                expected_elements=["submit_button"],
                success_indicators=["success", "application_number"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="applicant_name",
                form_field_name="Applicant Name",
                data_source="extracted_data",
                data_field="name",
                required=True
            ),
            FieldMapping(
                form_field_id="father_name",
                form_field_name="Father's Name",
                data_source="extracted_data",
                data_field="father_name",
                required=True
            )
        ],
        required_documents=["identity_proof", "address_proof"],
        estimated_duration_minutes=20
    )


def get_caste_certificate_workflow() -> WorkflowDefinition:
    """Workflow for caste certificate application"""
    return WorkflowDefinition(
        workflow_id="caste_certificate",
        service_id="caste_certificate",
        name="Caste Certificate Application",
        description="Apply for caste certificate",
        portal_url="https://edistrict.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Login to Portal",
                description="Login to e-district",
                page_url="https://edistrict.gov.in/login",
                actions=[
                    {"type": "fill_field", "field_id": "username", "data_source": "credentials.username"},
                    {"type": "fill_field", "field_id": "password", "data_source": "credentials.password"}
                ],
                expected_elements=["username", "password"],
                success_indicators=["dashboard"]
            ),
            WorkflowStep(
                step_number=2,
                name="Fill Caste Certificate Form",
                description="Enter application details",
                page_url="https://edistrict.gov.in/caste-certificate/form",
                actions=[
                    {"type": "click", "element_id": "caste_certificate_option"},
                    {"type": "fill_field", "field_id": "name", "data_source": "extracted_data.name"},
                    {"type": "fill_field", "field_id": "caste", "data_source": "user_input.caste"},
                    {"type": "fill_field", "field_id": "address", "data_source": "extracted_data.address"},
                    {"type": "upload_document", "field_id": "caste_proof"}
                ],
                expected_elements=["name", "caste"],
                success_indicators=["form_complete"]
            ),
            WorkflowStep(
                step_number=3,
                name="Submit",
                description="Submit application",
                page_url="https://edistrict.gov.in/caste-certificate/submit",
                actions=[
                    {"type": "click", "element_id": "submit_button"}
                ],
                expected_elements=["submit_button"],
                success_indicators=["success", "application_id"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="name",
                form_field_name="Name",
                data_source="extracted_data",
                data_field="name",
                required=True
            )
        ],
        required_documents=["caste_proof", "identity_proof"],
        estimated_duration_minutes=20
    )


def get_domicile_certificate_workflow() -> WorkflowDefinition:
    """Workflow for domicile certificate"""
    return WorkflowDefinition(
        workflow_id="domicile_certificate",
        service_id="domicile_certificate",
        name="Domicile Certificate Application",
        description="Apply for domicile certificate",
        portal_url="https://edistrict.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Login",
                description="Login to portal",
                page_url="https://edistrict.gov.in/login",
                actions=[
                    {"type": "fill_field", "field_id": "username", "data_source": "credentials.username"},
                    {"type": "fill_field", "field_id": "password", "data_source": "credentials.password"}
                ],
                expected_elements=["username"],
                success_indicators=["dashboard"]
            ),
            WorkflowStep(
                step_number=2,
                name="Fill Application",
                description="Enter domicile details",
                page_url="https://edistrict.gov.in/domicile/form",
                actions=[
                    {"type": "click", "element_id": "domicile_option"},
                    {"type": "fill_field", "field_id": "name", "data_source": "extracted_data.name"},
                    {"type": "fill_field", "field_id": "residence_years", "data_source": "user_input.years"},
                    {"type": "upload_document", "field_id": "residence_proof"}
                ],
                expected_elements=["name", "residence_years"],
                success_indicators=["form_complete"]
            ),
            WorkflowStep(
                step_number=3,
                name="Submit",
                description="Submit application",
                page_url="https://edistrict.gov.in/domicile/submit",
                actions=[
                    {"type": "click", "element_id": "submit_button"}
                ],
                expected_elements=["submit_button"],
                success_indicators=["success"]
            )
        ],
        form_mappings=[],
        required_documents=["residence_proof", "identity_proof"],
        estimated_duration_minutes=15
    )


def get_birth_certificate_workflow() -> WorkflowDefinition:
    """Workflow for birth certificate request"""
    return WorkflowDefinition(
        workflow_id="birth_certificate",
        service_id="birth_certificate",
        name="Birth Certificate Request",
        description="Request birth certificate",
        portal_url="https://crsorgi.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Access CRS Portal",
                description="Navigate to civil registration portal",
                page_url="https://crsorgi.gov.in",
                actions=[
                    {"type": "click", "element_id": "birth_certificate_option"}
                ],
                expected_elements=["birth_certificate_option"],
                success_indicators=["search_form"]
            ),
            WorkflowStep(
                step_number=2,
                name="Search Birth Record",
                description="Search for birth registration",
                page_url="https://crsorgi.gov.in/birth/search",
                actions=[
                    {"type": "fill_field", "field_id": "registration_number", "data_source": "user_input.reg_number"},
                    {"type": "fill_field", "field_id": "dob", "data_source": "user_input.dob"},
                    {"type": "click", "element_id": "search_button"}
                ],
                expected_elements=["registration_number", "dob"],
                success_indicators=["record_found"]
            ),
            WorkflowStep(
                step_number=3,
                name="Request Certificate",
                description="Request certificate issuance",
                page_url="https://crsorgi.gov.in/birth/request",
                actions=[
                    {"type": "click", "element_id": "request_certificate"},
                    {"type": "wait_for_user", "prompt": "Complete payment if required"}
                ],
                expected_elements=["request_certificate"],
                success_indicators=["success", "download_link"]
            )
        ],
        form_mappings=[],
        required_documents=[],
        estimated_duration_minutes=10
    )


# Workflow registry
CERTIFICATE_WORKFLOWS = {
    "income_certificate": get_income_certificate_workflow,
    "caste_certificate": get_caste_certificate_workflow,
    "domicile_certificate": get_domicile_certificate_workflow,
    "birth_certificate": get_birth_certificate_workflow
}


def get_workflow(workflow_id: str) -> WorkflowDefinition:
    """Get workflow by ID"""
    if workflow_id in CERTIFICATE_WORKFLOWS:
        return CERTIFICATE_WORKFLOWS[workflow_id]()
    
    raise ValueError(f"Workflow {workflow_id} not found")
