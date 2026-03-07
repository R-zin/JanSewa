"""
Integration tests for Browser Automation Form Filling

Tests the integration of form filling with browser automation.
Requirements: 12.11, 12.12, 12.13, 12.16, 12.30
"""

import pytest
from datetime import datetime
from app.services.browser_automation import BrowserAutomationAgent
from app.models.automation import WorkflowDefinition


@pytest.fixture
def browser_agent():
    """Create browser automation agent"""
    return BrowserAutomationAgent()


@pytest.fixture
def workflow():
    """Sample workflow definition"""
    return WorkflowDefinition(
        service_id="aadhaar_update",
        workflow_name="Aadhaar Address Update",
        steps=[
            {"step": 1, "action": "navigate", "url": "https://example.gov.in"},
            {"step": 2, "action": "fill_form", "form_id": "address_form"}
        ],
        field_mappings={
            "name": "applicant_name",
            "address": "current_address"
        },
        portal_url="https://example.gov.in",
        auth_required=True
    )


@pytest.fixture
def form_fields():
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
            "required": True
        }
    ]


@pytest.fixture
def extracted_data():
    """Sample extracted data from OCR"""
    return {
        "name": "John Doe",
        "aadhaar_number": "123456789012",
        "address": "123 Main St, City, State 123456",
        "mobile": "9876543210"
    }


@pytest.fixture
def user_profile():
    """Sample user profile"""
    return {
        "email": "john.doe@example.com",
        "full_name": "John Doe"
    }


class TestAutoFillForm:
    """Test automatic form filling - Requirements 12.11, 12.12, 12.13"""
    
    def test_auto_fill_with_extracted_data(
        self, browser_agent, workflow, form_fields, extracted_data
    ):
        """Test auto-filling form with extracted data"""
        # Create session
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        # Auto-fill form
        result = browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data
        )
        
        assert result["success"]
        assert result["filled_fields"] >= 4  # name, aadhaar, address, mobile
        assert result["ready_for_review"]
        assert "summary" in result
    
    def test_auto_fill_prioritizes_extracted_data(
        self, browser_agent, workflow, form_fields, extracted_data, user_profile
    ):
        """Test that extracted data is prioritized over user profile"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        # Both have 'name', but extracted should be used
        result = browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data,
            user_profile=user_profile
        )
        
        assert result["success"]
        
        # Get summary to check sources
        summary = result["summary"]
        name_field = next(
            (f for f in summary["fields"] if f["field_id"] == "name"),
            None
        )
        
        assert name_field is not None
        assert name_field["source"] == "extracted_data"
    
    def test_auto_fill_with_multiple_sources(
        self, browser_agent, workflow, form_fields, extracted_data, user_profile
    ):
        """Test auto-filling with data from multiple sources"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        result = browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data,
            user_profile=user_profile
        )
        
        assert result["success"]
        assert result["filled_fields"] == 5  # All fields filled
        
        # Check that different sources were used
        summary = result["summary"]
        sources = {f["source"] for f in summary["fields"]}
        assert len(sources) >= 2  # At least 2 different sources
    
    def test_auto_fill_updates_session_state(
        self, browser_agent, workflow, form_fields, extracted_data
    ):
        """Test that auto-fill updates session state"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data
        )
        
        # Check session state
        state = browser_agent.get_session_state(session_id)
        assert state is not None
        assert state["session_id"] == session_id
        # Session state should track filled fields (implementation detail)


class TestFormSummary:
    """Test form summary display - Requirement 12.30"""
    
    def test_get_form_summary(
        self, browser_agent, workflow, form_fields, extracted_data
    ):
        """Test getting form summary for user review"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        # Fill form
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data
        )
        
        # Get summary
        summary = browser_agent.get_form_summary(session_id)
        
        assert summary is not None
        assert "total_fields" in summary
        assert "filled_fields" in summary
        assert "fields" in summary
        assert "validation_results" in summary
        assert "ready_for_submission" in summary
        assert "warnings" in summary
    
    def test_summary_shows_field_sources(
        self, browser_agent, workflow, form_fields, extracted_data, user_profile
    ):
        """Test that summary shows data source for each field"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data,
            user_profile=user_profile
        )
        
        summary = browser_agent.get_form_summary(session_id)
        
        # Each field should have source information
        for field in summary["fields"]:
            assert "source" in field
            assert "confidence" in field
            assert field["source"] in ["extracted_data", "digilocker", "user_profile"]
    
    def test_summary_shows_validation_results(
        self, browser_agent, workflow, form_fields, extracted_data
    ):
        """Test that summary includes validation results"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data
        )
        
        summary = browser_agent.get_form_summary(session_id)
        
        # Should have validation results
        assert len(summary["validation_results"]) > 0
        
        # Each validation result should have required fields
        for validation in summary["validation_results"]:
            assert "field_id" in validation
            assert "is_valid" in validation
    
    def test_summary_before_filling_returns_none(
        self, browser_agent, workflow
    ):
        """Test that summary is None before form is filled"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        summary = browser_agent.get_form_summary(session_id)
        
        assert summary is None


class TestFormValidation:
    """Test form validation before submission - Requirement 12.16"""
    
    def test_validate_form_with_valid_data(
        self, browser_agent, workflow, form_fields, extracted_data, user_profile
    ):
        """Test validation passes with valid data"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        # Fill form with valid data
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data,
            user_profile=user_profile
        )
        
        # Validate
        result = browser_agent.validate_form_before_submission(session_id)
        
        assert result["success"]
        assert result["ready_for_submission"]
    
    def test_validate_form_with_invalid_data(
        self, browser_agent, workflow, form_fields
    ):
        """Test validation fails with invalid data"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        # Fill with invalid data
        invalid_data = {
            "email": "invalid-email",  # Invalid format
            "mobile": "123"  # Too short
        }
        
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=invalid_data
        )
        
        # Validate
        result = browser_agent.validate_form_before_submission(session_id)
        
        assert not result["success"]
        assert not result["ready_for_submission"]
        assert "validation_errors" in result
    
    def test_validate_without_filling_fails(
        self, browser_agent, workflow
    ):
        """Test validation fails if form not filled"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        # Try to validate without filling
        result = browser_agent.validate_form_before_submission(session_id)
        
        assert not result["success"]
        assert "error" in result


class TestUnfilledFields:
    """Test getting unfilled fields"""
    
    def test_get_unfilled_fields(
        self, browser_agent, workflow, form_fields, extracted_data
    ):
        """Test getting list of unfilled fields"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        # Fill only some fields
        partial_data = {
            "name": "John Doe",
            "aadhaar_number": "123456789012"
        }
        
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=partial_data
        )
        
        # Get unfilled fields
        unfilled = browser_agent.get_unfilled_fields(session_id, form_fields)
        
        # Should have unfilled fields (email, mobile, address)
        assert len(unfilled) > 0
        
        # Name and aadhaar should not be in unfilled
        unfilled_ids = {f.get("field_id") for f in unfilled}
        assert "name" not in unfilled_ids
        assert "aadhaar" not in unfilled_ids


class TestActionLogging:
    """Test that form filling actions are logged"""
    
    def test_auto_fill_logs_action(
        self, browser_agent, workflow, form_fields, extracted_data
    ):
        """Test that auto-fill action is logged"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="aadhaar_update",
            portal_url="https://example.gov.in",
            workflow=workflow
        )
        
        browser_agent.auto_fill_form(
            session_id,
            form_fields,
            extracted_data=extracted_data
        )
        
        # Get action logs
        logs = browser_agent.get_action_logs(session_id)
        
        # Should have auto_fill_form action
        auto_fill_log = next(
            (log for log in logs if log.get("details", {}).get("action") == "auto_fill_form"),
            None
        )
        
        assert auto_fill_log is not None
        assert auto_fill_log["success"]
        assert "total_fields" in auto_fill_log["details"]
        assert "filled_fields" in auto_fill_log["details"]
