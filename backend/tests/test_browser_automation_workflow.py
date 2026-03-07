"""
Tests for Browser Automation Multi-Step Workflow

Tests workflow step progression, page transitions, final submission confirmation,
and confirmation capture and storage.

Requirements: 12.21, 12.24, 12.25, 12.26
"""

import pytest
from datetime import datetime
from app.services.browser_automation import BrowserAutomationAgent, AutomationStatus
from app.models.automation import WorkflowDefinition, SessionState


@pytest.fixture
def browser_agent():
    """Create browser automation agent"""
    return BrowserAutomationAgent()


@pytest.fixture
def multi_step_workflow():
    """Multi-step workflow definition"""
    return WorkflowDefinition(
        service_id="income_certificate",
        workflow_name="Income Certificate Application",
        steps=[
            {"step": 1, "action": "navigate", "url": "https://example.gov.in/login"},
            {"step": 2, "action": "fill_form", "form_id": "login_form"},
            {"step": 3, "action": "navigate", "url": "https://example.gov.in/application"},
            {"step": 4, "action": "fill_form", "form_id": "application_form"},
            {"step": 5, "action": "navigate", "url": "https://example.gov.in/review"},
            {"step": 6, "action": "submit", "form_id": "final_submit"}
        ],
        field_mappings={
            "name": "applicant_name",
            "income": "annual_income"
        },
        portal_url="https://example.gov.in",
        auth_required=True
    )


class TestWorkflowStepProgression:
    """Test workflow step progression logic - Requirement 12.24"""
    
    def test_execute_workflow_step_navigate(self, browser_agent, multi_step_workflow):
        """Test executing a navigation step"""
        # Create session
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Execute first step (navigate)
        result = browser_agent.execute_workflow_step(session_id, 0)
        
        assert result["success"] is True
        assert result["action"] == "navigate"
        assert result["url"] == "https://example.gov.in/login"
    
    def test_execute_workflow_step_fill_form(self, browser_agent, multi_step_workflow):
        """Test executing a form fill step"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Execute form fill step
        result = browser_agent.execute_workflow_step(session_id, 1)
        
        assert result["success"] is True
        assert result["action"] == "fill_form"
    
    def test_execute_workflow_step_submit(self, browser_agent, multi_step_workflow):
        """Test executing a submit step"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Execute submit step
        result = browser_agent.execute_workflow_step(session_id, 5)
        
        assert result["success"] is True
        assert result["action"] == "submit"
        assert result["requires_confirmation"] is True
    
    def test_proceed_to_next_step(self, browser_agent, multi_step_workflow):
        """Test automatic progression to next step"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Start session
        browser_agent.start_session(session_id)
        
        # Get initial step
        initial_step = browser_agent.sessions[session_id].current_step
        
        # Proceed to next step
        result = browser_agent.proceed_to_next_step(session_id)
        
        assert result["success"] is True
        
        # Verify step incremented
        new_step = browser_agent.sessions[session_id].current_step
        assert new_step == initial_step + 1
    
    def test_workflow_completion_detection(self, browser_agent, multi_step_workflow):
        """Test detection of workflow completion"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Set to last step
        session = browser_agent.sessions[session_id]
        session.current_step = session.total_steps
        
        # Try to proceed
        result = browser_agent.proceed_to_next_step(session_id)
        
        assert result["success"] is True
        assert result["workflow_complete"] is True


class TestPageTransitionHandling:
    """Test page transition handling - Requirement 12.24"""
    
    def test_handle_page_transition_success(self, browser_agent, multi_step_workflow):
        """Test successful page transition"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Navigate to a page
        browser_agent.navigate_to(session_id, "https://example.gov.in/application")
        
        # Handle page transition
        result = browser_agent.handle_page_transition(
            session_id,
            expected_url_pattern="application"
        )
        
        assert result["success"] is True
        assert "application" in result["current_url"]
        assert "elapsed_time" in result
    
    def test_handle_page_transition_without_pattern(self, browser_agent, multi_step_workflow):
        """Test page transition without expected URL pattern"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Navigate to a page
        browser_agent.navigate_to(session_id, "https://example.gov.in/form")
        
        # Handle page transition without pattern
        result = browser_agent.handle_page_transition(session_id)
        
        assert result["success"] is True
        assert result["current_url"] == "https://example.gov.in/form"
    
    def test_handle_page_transition_failure(self, browser_agent, multi_step_workflow):
        """Test page transition failure when URL doesn't match"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Navigate to a page
        browser_agent.navigate_to(session_id, "https://example.gov.in/error")
        
        # Handle page transition with different expected pattern
        result = browser_agent.handle_page_transition(
            session_id,
            expected_url_pattern="success"
        )
        
        assert result["success"] is False
        assert "error" in result


class TestFinalSubmissionConfirmation:
    """Test final submission confirmation - Requirement 12.25"""
    
    def test_detect_final_submission_page(self, browser_agent, multi_step_workflow):
        """Test detection of final submission page"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Set to last step
        session = browser_agent.sessions[session_id]
        session.current_step = session.total_steps - 1
        
        # Detect submission page
        result = browser_agent.detect_final_submission_page(session_id)
        
        assert result["success"] is True
        assert result["is_submission_page"] is True
        assert len(result["indicators"]) > 0
    
    def test_detect_non_submission_page(self, browser_agent, multi_step_workflow):
        """Test detection when not on submission page"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Set to middle step
        session = browser_agent.sessions[session_id]
        session.current_step = 2
        
        # Detect submission page
        result = browser_agent.detect_final_submission_page(session_id)
        
        assert result["success"] is True
        assert result["is_submission_page"] is False
    
    def test_request_submission_confirmation(self, browser_agent, multi_step_workflow):
        """Test requesting user confirmation before submission"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Request confirmation
        result = browser_agent.request_submission_confirmation(session_id)
        
        assert result["success"] is True
        assert result["action_required"] == "submission_confirmation"
        assert result["session_paused"] is True
        assert "message" in result
        
        # Verify session is paused
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.WAITING_FOR_USER
        assert session.session_state.user_action_type == "submission_confirmation"
    
    def test_confirm_and_submit_with_confirmation(self, browser_agent, multi_step_workflow):
        """Test submission after user confirms"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Request confirmation first
        browser_agent.request_submission_confirmation(session_id)
        
        # User confirms
        result = browser_agent.confirm_and_submit(session_id, user_confirmed=True)
        
        assert result["success"] is True
        assert result["submitted"] is True
        assert "confirmation" in result
        assert "submission_time" in result
        
        # Verify session is completed
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.COMPLETED
    
    def test_confirm_and_submit_without_confirmation(self, browser_agent, multi_step_workflow):
        """Test cancellation when user doesn't confirm"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Request confirmation first
        browser_agent.request_submission_confirmation(session_id)
        
        # User cancels
        result = browser_agent.confirm_and_submit(session_id, user_confirmed=False)
        
        assert result["success"] is True
        assert result["submitted"] is False
        assert "cancelled" in result["message"].lower()
        
        # Verify session is paused, not completed
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.PAUSED


class TestConfirmationCapture:
    """Test confirmation capture and storage - Requirement 12.26"""
    
    def test_capture_confirmation_response(self, browser_agent, multi_step_workflow):
        """Test capturing confirmation details after submission"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Capture confirmation
        confirmation = browser_agent._capture_confirmation_response(session_id)
        
        assert "confirmation_number" in confirmation
        assert "confirmation_message" in confirmation
        assert "submission_date" in confirmation
        assert "service_id" in confirmation
        assert confirmation["service_id"] == "income_certificate"
        assert "next_steps" in confirmation
        assert len(confirmation["next_steps"]) > 0
    
    def test_confirmation_stored_in_session(self, browser_agent, multi_step_workflow):
        """Test that confirmation is stored in session state"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Request and confirm submission
        browser_agent.request_submission_confirmation(session_id)
        browser_agent.confirm_and_submit(session_id, user_confirmed=True)
        
        # Verify confirmation stored
        session = browser_agent.sessions[session_id]
        assert session.session_state.confirmation_data is not None
        assert "confirmation_number" in session.session_state.confirmation_data
    
    def test_save_confirmation_to_dashboard(self, browser_agent, multi_step_workflow):
        """Test saving confirmation to dashboard - Requirement 12.21"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Submit and capture confirmation
        browser_agent.request_submission_confirmation(session_id)
        browser_agent.confirm_and_submit(session_id, user_confirmed=True)
        
        # Save to dashboard
        result = browser_agent.save_confirmation_to_dashboard(session_id)
        
        assert result["success"] is True
        assert "dashboard_entry" in result
        
        entry = result["dashboard_entry"]
        assert entry["user_id"] == "user123"
        assert entry["service_id"] == "income_certificate"
        assert "confirmation_number" in entry
        assert "submission_date" in entry
        assert entry["status"] == "submitted"
    
    def test_save_confirmation_without_data(self, browser_agent, multi_step_workflow):
        """Test saving confirmation when no confirmation data exists"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Try to save without submission
        result = browser_agent.save_confirmation_to_dashboard(session_id)
        
        assert result["success"] is False
        assert "error" in result


class TestMultiStepWorkflowExecution:
    """Test complete multi-step workflow execution - Requirements 12.23, 12.24, 12.29"""
    
    def test_execute_multi_step_workflow_basic(self, browser_agent, multi_step_workflow):
        """Test basic multi-step workflow execution"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Execute workflow
        result = browser_agent.execute_multi_step_workflow(session_id)
        
        # Should pause for submission confirmation
        assert result["success"] is True
        assert result["status"] == "paused"
        assert result["reason"] == "submission_confirmation"
    
    def test_execute_multi_step_workflow_with_pauses(self, browser_agent, multi_step_workflow):
        """Test workflow execution with user action pauses"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Start workflow
        browser_agent.start_session(session_id)
        
        # Simulate OTP pause
        session = browser_agent.sessions[session_id]
        session.status = AutomationStatus.WAITING_FOR_USER
        session.session_state.user_action_type = "otp_entry"
        
        # Execute workflow
        result = browser_agent.execute_multi_step_workflow(session_id)
        
        assert result["success"] is True
        assert result["status"] == "paused"
        assert result["reason"] == "otp_entry"
    
    def test_workflow_action_logging(self, browser_agent, multi_step_workflow):
        """Test that workflow actions are logged"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Execute some steps
        browser_agent.start_session(session_id)
        browser_agent.proceed_to_next_step(session_id)
        browser_agent.proceed_to_next_step(session_id)
        
        # Get action logs
        logs = browser_agent.get_action_logs(session_id)
        
        assert len(logs) > 0
        
        # Verify step progression is logged
        step_logs = [log for log in logs if "step_progression" in log.get("details", {}).get("action", "")]
        assert len(step_logs) > 0
    
    def test_workflow_state_tracking(self, browser_agent, multi_step_workflow):
        """Test workflow state is properly tracked"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Start and execute steps
        browser_agent.start_session(session_id)
        browser_agent.proceed_to_next_step(session_id)
        
        # Get session state
        state = browser_agent.get_session_state(session_id)
        
        assert state is not None
        assert "current_step" in state
        assert "total_steps" in state
        assert "progress_percentage" in state
        assert state["total_steps"] == len(multi_step_workflow.steps)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow scenarios"""
    
    def test_complete_workflow_with_confirmation(self, browser_agent, multi_step_workflow):
        """Test complete workflow from start to confirmation"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Execute workflow until confirmation
        result = browser_agent.execute_multi_step_workflow(session_id)
        assert result["status"] == "paused"
        assert result["reason"] == "submission_confirmation"
        
        # User confirms
        submit_result = browser_agent.confirm_and_submit(session_id, user_confirmed=True)
        assert submit_result["success"] is True
        assert submit_result["submitted"] is True
        
        # Save to dashboard
        save_result = browser_agent.save_confirmation_to_dashboard(session_id)
        assert save_result["success"] is True
        
        # Verify session completed
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.COMPLETED
        assert session.completed_at is not None
    
    def test_workflow_with_cancellation(self, browser_agent, multi_step_workflow):
        """Test workflow cancellation at confirmation"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="income_certificate",
            portal_url="https://example.gov.in",
            workflow=multi_step_workflow
        )
        
        # Execute workflow until confirmation
        result = browser_agent.execute_multi_step_workflow(session_id)
        assert result["status"] == "paused"
        
        # User cancels
        submit_result = browser_agent.confirm_and_submit(session_id, user_confirmed=False)
        assert submit_result["success"] is True
        assert submit_result["submitted"] is False
        
        # Verify session is paused, not completed
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.PAUSED
        assert session.completed_at is None
