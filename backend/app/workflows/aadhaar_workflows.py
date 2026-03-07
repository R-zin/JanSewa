"""
Workflow Definitions for Aadhaar Services

Defines automation workflows for common Aadhaar operations.
"""

from app.models.automation import (
    WorkflowDefinition, WorkflowStep, FormField, FieldMapping
)


def get_aadhaar_name_change_workflow() -> WorkflowDefinition:
    """
    Workflow for Aadhaar name change
    """
    return WorkflowDefinition(
        workflow_id="aadhaar_name_change",
        service_id="aadhaar_name_change",
        name="Aadhaar Name Change",
        description="Update name in Aadhaar card",
        portal_url="https://myaadhaar.uidai.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Login to UIDAI Portal",
                description="Navigate to UIDAI portal and login",
                page_url="https://myaadhaar.uidai.gov.in/login",
                actions=[
                    {
                        "type": "fill_field",
                        "field_id": "aadhaar_number",
                        "field_name": "Aadhaar Number",
                        "data_source": "user_profile.aadhaar_number"
                    },
                    {
                        "type": "click",
                        "element_id": "send_otp_button"
                    },
                    {
                        "type": "wait_for_user",
                        "prompt": "Please enter the OTP sent to your mobile"
                    }
                ],
                expected_elements=["aadhaar_number", "send_otp_button"],
                success_indicators=["dashboard", "welcome"]
            ),
            WorkflowStep(
                step_number=2,
                name="Navigate to Update Name",
                description="Go to name update section",
                page_url="https://myaadhaar.uidai.gov.in/update-name",
                actions=[
                    {
                        "type": "click",
                        "element_id": "update_demographics"
                    },
                    {
                        "type": "click",
                        "element_id": "name_update_option"
                    }
                ],
                expected_elements=["update_demographics", "name_update_option"],
                success_indicators=["name_update_form"]
            ),
            WorkflowStep(
                step_number=3,
                name="Fill Name Update Form",
                description="Enter new name and supporting details",
                page_url="https://myaadhaar.uidai.gov.in/update-name/form",
                actions=[
                    {
                        "type": "fill_field",
                        "field_id": "new_name",
                        "field_name": "New Name",
                        "data_source": "extracted_data.name"
                    },
                    {
                        "type": "upload_document",
                        "field_id": "supporting_document",
                        "document_type": "name_proof"
                    },
                    {
                        "type": "fill_field",
                        "field_id": "mobile_number",
                        "data_source": "user_profile.mobile"
                    }
                ],
                expected_elements=["new_name", "supporting_document", "mobile_number"],
                success_indicators=["form_filled"]
            ),
            WorkflowStep(
                step_number=4,
                name="Review and Submit",
                description="Review details and submit application",
                page_url="https://myaadhaar.uidai.gov.in/update-name/review",
                actions=[
                    {
                        "type": "wait_for_user",
                        "prompt": "Please review the details and confirm"
                    },
                    {
                        "type": "click",
                        "element_id": "submit_button"
                    }
                ],
                expected_elements=["submit_button", "review_summary"],
                success_indicators=["success", "acknowledgement", "urn"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="new_name",
                form_field_name="New Name",
                data_source="extracted_data",
                data_field="name",
                required=True
            ),
            FieldMapping(
                form_field_id="mobile_number",
                form_field_name="Mobile Number",
                data_source="user_profile",
                data_field="mobile",
                required=True
            )
        ],
        required_documents=["name_proof"],
        estimated_duration_minutes=15
    )


def get_aadhaar_address_update_workflow() -> WorkflowDefinition:
    """
    Workflow for Aadhaar address update
    """
    return WorkflowDefinition(
        workflow_id="aadhaar_address_update",
        service_id="aadhaar_address_update",
        name="Aadhaar Address Update",
        description="Update address in Aadhaar card",
        portal_url="https://myaadhaar.uidai.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Login to UIDAI Portal",
                description="Navigate to UIDAI portal and login",
                page_url="https://myaadhaar.uidai.gov.in/login",
                actions=[
                    {
                        "type": "fill_field",
                        "field_id": "aadhaar_number",
                        "data_source": "user_profile.aadhaar_number"
                    },
                    {
                        "type": "click",
                        "element_id": "send_otp_button"
                    },
                    {
                        "type": "wait_for_user",
                        "prompt": "Please enter the OTP"
                    }
                ],
                expected_elements=["aadhaar_number", "send_otp_button"],
                success_indicators=["dashboard"]
            ),
            WorkflowStep(
                step_number=2,
                name="Navigate to Update Address",
                description="Go to address update section",
                page_url="https://myaadhaar.uidai.gov.in/update-address",
                actions=[
                    {
                        "type": "click",
                        "element_id": "update_demographics"
                    },
                    {
                        "type": "click",
                        "element_id": "address_update_option"
                    }
                ],
                expected_elements=["update_demographics", "address_update_option"],
                success_indicators=["address_update_form"]
            ),
            WorkflowStep(
                step_number=3,
                name="Fill Address Form",
                description="Enter new address details",
                page_url="https://myaadhaar.uidai.gov.in/update-address/form",
                actions=[
                    {
                        "type": "fill_field",
                        "field_id": "address_line1",
                        "data_source": "extracted_data.address"
                    },
                    {
                        "type": "fill_field",
                        "field_id": "pincode",
                        "data_source": "extracted_data.pincode"
                    },
                    {
                        "type": "upload_document",
                        "field_id": "address_proof",
                        "document_type": "address_proof"
                    }
                ],
                expected_elements=["address_line1", "pincode", "address_proof"],
                success_indicators=["form_filled"]
            ),
            WorkflowStep(
                step_number=4,
                name="Submit Application",
                description="Review and submit",
                page_url="https://myaadhaar.uidai.gov.in/update-address/review",
                actions=[
                    {
                        "type": "wait_for_user",
                        "prompt": "Review and confirm"
                    },
                    {
                        "type": "click",
                        "element_id": "submit_button"
                    }
                ],
                expected_elements=["submit_button"],
                success_indicators=["success", "urn"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="address_line1",
                form_field_name="Address",
                data_source="extracted_data",
                data_field="address",
                required=True
            ),
            FieldMapping(
                form_field_id="pincode",
                form_field_name="PIN Code",
                data_source="extracted_data",
                data_field="pincode",
                required=True
            )
        ],
        required_documents=["address_proof"],
        estimated_duration_minutes=15
    )


def get_aadhaar_mobile_update_workflow() -> WorkflowDefinition:
    """
    Workflow for Aadhaar mobile number update
    """
    return WorkflowDefinition(
        workflow_id="aadhaar_mobile_update",
        service_id="aadhaar_mobile_update",
        name="Aadhaar Mobile Update",
        description="Update mobile number in Aadhaar",
        portal_url="https://myaadhaar.uidai.gov.in",
        steps=[
            WorkflowStep(
                step_number=1,
                name="Login to UIDAI Portal",
                description="Login with Aadhaar",
                page_url="https://myaadhaar.uidai.gov.in/login",
                actions=[
                    {
                        "type": "fill_field",
                        "field_id": "aadhaar_number",
                        "data_source": "user_profile.aadhaar_number"
                    },
                    {
                        "type": "click",
                        "element_id": "send_otp_button"
                    },
                    {
                        "type": "wait_for_user",
                        "prompt": "Enter OTP"
                    }
                ],
                expected_elements=["aadhaar_number"],
                success_indicators=["dashboard"]
            ),
            WorkflowStep(
                step_number=2,
                name="Update Mobile Number",
                description="Enter new mobile number",
                page_url="https://myaadhaar.uidai.gov.in/update-mobile",
                actions=[
                    {
                        "type": "click",
                        "element_id": "update_mobile_option"
                    },
                    {
                        "type": "fill_field",
                        "field_id": "new_mobile",
                        "data_source": "user_input.new_mobile"
                    },
                    {
                        "type": "click",
                        "element_id": "verify_button"
                    },
                    {
                        "type": "wait_for_user",
                        "prompt": "Enter OTP sent to new mobile"
                    }
                ],
                expected_elements=["new_mobile", "verify_button"],
                success_indicators=["verified"]
            ),
            WorkflowStep(
                step_number=3,
                name="Confirm Update",
                description="Confirm mobile update",
                page_url="https://myaadhaar.uidai.gov.in/update-mobile/confirm",
                actions=[
                    {
                        "type": "click",
                        "element_id": "confirm_button"
                    }
                ],
                expected_elements=["confirm_button"],
                success_indicators=["success", "updated"]
            )
        ],
        form_mappings=[
            FieldMapping(
                form_field_id="new_mobile",
                form_field_name="New Mobile Number",
                data_source="user_input",
                data_field="new_mobile",
                required=True
            )
        ],
        required_documents=[],
        estimated_duration_minutes=10
    )


# Workflow registry
AADHAAR_WORKFLOWS = {
    "aadhaar_name_change": get_aadhaar_name_change_workflow,
    "aadhaar_address_update": get_aadhaar_address_update_workflow,
    "aadhaar_mobile_update": get_aadhaar_mobile_update_workflow
}


def get_workflow(workflow_id: str) -> WorkflowDefinition:
    """
    Get workflow by ID
    
    Args:
        workflow_id: Workflow identifier
        
    Returns:
        Workflow definition
    """
    if workflow_id in AADHAAR_WORKFLOWS:
        return AADHAAR_WORKFLOWS[workflow_id]()
    
    raise ValueError(f"Workflow {workflow_id} not found")
