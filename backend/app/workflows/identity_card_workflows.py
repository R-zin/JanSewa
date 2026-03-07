"""
Workflow Definitions for Identity Card Services

Defines automation workflows for PAN, Driving License, Voter ID, and Passport.
"""

from app.models.automation import (
    WorkflowDefinition, WorkflowStep, FieldMapping
)


def get_pan_correction_workflow() -> WorkflowDefinition:
    """Workflow for PAN card corrections"""
    return WorkflowDefinition(
        workflow_id="pan_correction",
        service_id="pan_correction",
        name="PAN Card Correction",
        description="Correct details in PAN card",
        portal_url="https://www.onlineservices.nsdl.com/paam/requestAndDownloadEPAN.html",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Access PAN Correction Portal",
                description="Navigate to NSDL PAN correction",
                page_url="https://www.onlineservices.nsdl.com/paam/requestAndDownloadEPAN.html",
                actions=[
                    {"type": "click", "element_id": "correction_option"}
                ],
                expected_elements=["correction_option"],
                success_indicators=["correction_form"]
            ),
            WorkflowStep(
                step_number=2,
                name="Fill Correction Form",
                description="Enter correction details",
                page_url="https://www.onlineservices.nsdl.com/paam/correction",
                actions=[
                    {"type": "fill_field", "field_id": "pan_number", "data_source": "extracted_data.pan_number"},
                    {"type": "fill_field", "field_id": "name", "data_source": "extracted_data.name"},
                    {"type": "fill_field", "field_id": "dob", "data_source": "extracted_data.dob"},
                    {"type": "upload_document", "field_id": "identity_proof"}
                ],
                expected_elements=["pan_number", "name", "dob"],
                success_indicators=["form_complete"]
            ),
            WorkflowStep(
                step_number=3,
                name="Payment",
                description="Complete payment for correction",
                page_url="https://www.onlineservices.nsdl.com/paam/payment",
                actions=[
                    {"type": "wait_for_user", "prompt": "Complete payment process"}
                ],
                expected_elements=["payment_gateway"],
                success_indicators=["payment_success"]
            ),
            WorkflowStep(
                step_number=4,
                name="Submit Application",
                description="Final submission",
                page_url="https://www.onlineservices.nsdl.com/paam/submit",
                actions=[
                    {"type": "click", "element_id": "final_submit"}
                ],
                expected_elements=["final_submit"],
                success_indicators=["acknowledgement", "token"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="pan_number",
                form_field_name="PAN Number",
                data_source="extracted_data",
                data_field="pan_number",
                required=True
            )
        ],
        required_documents=["identity_proof", "address_proof"],
        estimated_duration_minutes=20
    )


def get_driving_license_renewal_workflow() -> WorkflowDefinition:
    """Workflow for Driving License renewal"""
    return WorkflowDefinition(
        workflow_id="dl_renewal",
        service_id="dl_renewal",
        name="Driving License Renewal",
        description="Renew driving license online",
        portal_url="https://parivahan.gov.in/parivahan",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Login to Parivahan",
                description="Login to transport portal",
                page_url="https://parivahan.gov.in/parivahan/login",
                actions=[
                    {"type": "fill_field", "field_id": "dl_number", "data_source": "extracted_data.dl_number"},
                    {"type": "fill_field", "field_id": "dob", "data_source": "extracted_data.dob"},
                    {"type": "wait_for_user", "prompt": "Complete CAPTCHA"}
                ],
                expected_elements=["dl_number", "dob"],
                success_indicators=["dashboard"]
            ),
            WorkflowStep(
                step_number=2,
                name="Select Renewal Option",
                description="Choose license renewal",
                page_url="https://parivahan.gov.in/parivahan/renewal",
                actions=[
                    {"type": "click", "element_id": "renewal_option"}
                ],
                expected_elements=["renewal_option"],
                success_indicators=["renewal_form"]
            ),
            WorkflowStep(
                step_number=3,
                name="Fill Renewal Form",
                description="Enter renewal details",
                page_url="https://parivahan.gov.in/parivahan/renewal/form",
                actions=[
                    {"type": "fill_field", "field_id": "address", "data_source": "extracted_data.address"},
                    {"type": "fill_field", "field_id": "mobile", "data_source": "user_profile.mobile"},
                    {"type": "upload_document", "field_id": "medical_certificate"}
                ],
                expected_elements=["address", "mobile"],
                success_indicators=["form_complete"]
            ),
            WorkflowStep(
                step_number=4,
                name="Submit and Pay",
                description="Submit application and pay fee",
                page_url="https://parivahan.gov.in/parivahan/renewal/submit",
                actions=[
                    {"type": "wait_for_user", "prompt": "Review and complete payment"},
                    {"type": "click", "element_id": "submit_button"}
                ],
                expected_elements=["submit_button"],
                success_indicators=["success", "application_number"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="dl_number",
                form_field_name="DL Number",
                data_source="extracted_data",
                data_field="dl_number",
                required=True
            )
        ],
        required_documents=["medical_certificate", "address_proof"],
        estimated_duration_minutes=25
    )


def get_voter_id_update_workflow() -> WorkflowDefinition:
    """Workflow for Voter ID updates"""
    return WorkflowDefinition(
        workflow_id="voter_id_update",
        service_id="voter_id_update",
        name="Voter ID Update",
        description="Update details in Voter ID",
        portal_url="https://voters.eci.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Access Voter Portal",
                description="Navigate to ECI portal",
                page_url="https://voters.eci.gov.in",
                actions=[
                    {"type": "click", "element_id": "correction_option"}
                ],
                expected_elements=["correction_option"],
                success_indicators=["correction_form"]
            ),
            WorkflowStep(
                step_number=2,
                name="Fill Correction Form",
                description="Enter correction details",
                page_url="https://voters.eci.gov.in/correction",
                actions=[
                    {"type": "fill_field", "field_id": "epic_number", "data_source": "extracted_data.voter_id"},
                    {"type": "fill_field", "field_id": "name", "data_source": "extracted_data.name"},
                    {"type": "upload_document", "field_id": "supporting_doc"}
                ],
                expected_elements=["epic_number", "name"],
                success_indicators=["form_filled"]
            ),
            WorkflowStep(
                step_number=3,
                name="Submit Application",
                description="Submit correction request",
                page_url="https://voters.eci.gov.in/submit",
                actions=[
                    {"type": "click", "element_id": "submit_button"}
                ],
                expected_elements=["submit_button"],
                success_indicators=["success", "reference_number"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="epic_number",
                form_field_name="EPIC Number",
                data_source="extracted_data",
                data_field="voter_id",
                required=True
            )
        ],
        required_documents=["identity_proof", "address_proof"],
        estimated_duration_minutes=15
    )


# Workflow registry
IDENTITY_CARD_WORKFLOWS = {
    "pan_correction": get_pan_correction_workflow,
    "dl_renewal": get_driving_license_renewal_workflow,
    "voter_id_update": get_voter_id_update_workflow
}


def get_workflow(workflow_id: str) -> WorkflowDefinition:
    """Get workflow by ID"""
    if workflow_id in IDENTITY_CARD_WORKFLOWS:
        return IDENTITY_CARD_WORKFLOWS[workflow_id]()
    
    raise ValueError(f"Workflow {workflow_id} not found")
