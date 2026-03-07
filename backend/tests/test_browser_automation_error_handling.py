"""
Tests for Browser Automation Error Handling and Recovery

Tests navigation failure detection, session timeout detection, unexpected page handling,
and error recovery mechanisms.

Requirements: 12.19, 12.27
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
def test_workflow():
    """Test workflow definition"""
    return WorkflowDefinition(
        service_id="test_service",
        workflow_name="Test Service Application",
        steps=[
            {"step": 1, "action": "navigate", "url": "https://example.gov.in/login"},
            {"step": 2, "action": "fill_form", "form_id": "login_form"},
            {"step": 3, "action": "navigate", "url": "https://example.gov.in/application"},
            {"step": 4, "action": "submit", "form_id": "application_form"}
        ],
        field_mappings={},
        portal_url="https://example.gov.in",
        auth_required=True
    )


class TestNavigationFailureDetection:
    """Test navigation failure detection - Requirement 12.19"""
    
    def test_detect_navigation_failure_error_url(self, browser_agent, test_workflow):
        """Test detection of navigation failure from error URL"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to error page
        browser_agent.navigate_to(session_id, "https://example.gov.in/error/404")
        
        # Detect navigation failure
        result = browser_agent.detect_navigation_failure(session_id)
        
        assert result["success"] is True
        assert result["navigation_failed"] is True
        assert len(result["failure_reasons"]) > 0
        assert "Error page detected" in result["failure_reasons"][0]
    
    def test_detect_navigation_failure_url_mismatch(self, browser_agent, test_workflow):
        """Test detection of navigation failure from URL mismatch"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to unexpected page
        browser_agent.navigate_to(session_id, "https://example.gov.in/unexpected")
        
        # Detect navigation failure with expected pattern
        result = browser_agent.detect_navigation_failure(
            session_id,
            expected_url_pattern="application"
        )
        
        assert result["success"] is True
        assert result["navigation_failed"] is True
        assert any("does not match expected pattern" in reason for reason in result["failure_reasons"])
    
    def test_detect_navigation_success(self, browser_agent, test_workflow):
        """Test successful navigation detection"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to correct page
        browser_agent.navigate_to(session_id, "https://example.gov.in/application")
        
        # Detect navigation with matching pattern
        result = browser_agent.detect_navigation_failure(
            session_id,
            expected_url_pattern="application"
        )
        
        assert result["success"] is True
        assert result["navigation_failed"] is False
    
    def test_detect_navigation_failure_timeout_url(self, browser_agent, test_workflow):
        """Test detection of timeout in URL"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to timeout page
        browser_agent.navigate_to(session_id, "https://example.gov.in/timeout")
        
        # Detect navigation failure
        result = browser_agent.detect_navigation_failure(session_id)
        
        assert result["success"] is True
        assert result["navigation_failed"] is True
        assert "Error page detected" in result["failure_reasons"][0]


class TestUnexpectedPageDetection:
    """Test unexpected page detection - Requirement 12.27"""
    
    def test_detect_unexpected_login_page(self, browser_agent, test_workflow):
        """Test detection of unexpected redirect to login page"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to login page (unexpected during workflow)
        browser_agent.navigate_to(session_id, "https://example.gov.in/login")
        
        # Detect unexpected page
        result = browser_agent.detect_unexpected_page(
            session_id,
            expected_page_indicators=["application", "form"]
        )
        
        assert result["success"] is True
        assert result["is_unexpected"] is True
        assert len(result["unexpected_indicators"]) > 0
    
    def test_detect_unexpected_error_page(self, browser_agent, test_workflow):
        """Test detection of unexpected error page"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to error page
        browser_agent.navigate_to(session_id, "https://example.gov.in/error")
        
        # Detect unexpected page
        result = browser_agent.detect_unexpected_page(session_id)
        
        assert result["success"] is True
        assert result["is_unexpected"] is True
        assert any("error" in indicator.lower() for indicator in result["unexpected_indicators"])
    
    def test_detect_unexpected_maintenance_page(self, browser_agent, test_workflow):
        """Test detection of maintenance page"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to maintenance page
        browser_agent.navigate_to(session_id, "https://example.gov.in/maintenance")
        
        # Detect unexpected page
        result = browser_agent.detect_unexpected_page(session_id)
        
        assert result["success"] is True
        assert result["is_unexpected"] is True
        assert any("maintenance" in indicator.lower() for indicator in result["unexpected_indicators"])
    
    def test_detect_expected_page(self, browser_agent, test_workflow):
        """Test detection when page is as expected"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to expected page
        browser_agent.navigate_to(session_id, "https://example.gov.in/application")
        
        # Detect unexpected page with matching indicators
        result = browser_agent.detect_unexpected_page(
            session_id,
            expected_page_indicators=["application"]
        )
        
        assert result["success"] is True
        assert result["is_unexpected"] is False
    
    def test_detect_session_expired_page(self, browser_agent, test_workflow):
        """Test detection of session expired page"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Navigate to session expired page
        browser_agent.navigate_to(session_id, "https://example.gov.in/session-expired")
        
        # Detect unexpected page
        result = browser_agent.detect_unexpected_page(session_id)
        
        assert result["success"] is True
        assert result["is_unexpected"] is True
        assert any("session-expired" in indicator.lower() for indicator in result["unexpected_indicators"])


class TestErrorHandlingAndPause:
    """Test error handling and automation pause - Requirements 12.19, 12.27"""
    
    def test_handle_navigation_failure_error(self, browser_agent, test_workflow):
        """Test handling navigation failure by pausing"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session
        browser_agent.start_session(session_id)
        
        # Handle navigation failure
        result = browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={"url": "https://example.gov.in/error"}
        )
        
        assert result["success"] is True
        assert result["session_paused"] is True
        assert result["error_type"] == "navigation_failure"
        assert "message" in result
        assert "recovery_options" in result
        
        # Verify session is paused
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.PAUSED
        assert session.session_state.requires_user_action is True
    
    def test_handle_unexpected_page_error(self, browser_agent, test_workflow):
        """Test handling unexpected page by pausing"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session
        browser_agent.start_session(session_id)
        
        # Handle unexpected page
        result = browser_agent.handle_error_and_pause(
            session_id,
            error_type="unexpected_page",
            error_details={"current_url": "https://example.gov.in/login"}
        )
        
        assert result["success"] is True
        assert result["session_paused"] is True
        assert result["error_type"] == "unexpected_page"
        assert len(result["recovery_options"]) > 0
        
        # Verify session is paused
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.PAUSED
    
    def test_handle_session_timeout_error(self, browser_agent, test_workflow):
        """Test handling session timeout"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session
        browser_agent.start_session(session_id)
        
        # Handle session timeout
        result = browser_agent.handle_error_and_pause(
            session_id,
            error_type="session_timeout",
            error_details={}
        )
        
        assert result["success"] is True
        assert result["session_paused"] is True
        assert result["error_type"] == "session_timeout"
        assert "re-authenticate" in result["message"].lower() or "session" in result["message"].lower()
    
    def test_error_handling_logs_action(self, browser_agent, test_workflow):
        """Test that error handling logs the action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Handle error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={"url": "https://example.gov.in/error"}
        )
        
        # Get action logs
        logs = browser_agent.get_action_logs(session_id)
        
        # Verify error was logged
        error_logs = [log for log in logs if "error_handled" in log.get("details", {}).get("action", "")]
        assert len(error_logs) > 0
        assert error_logs[0]["details"]["error_type"] == "navigation_failure"
    
    def test_recovery_options_for_different_errors(self, browser_agent, test_workflow):
        """Test that different error types provide appropriate recovery options"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Test navigation failure recovery options
        result1 = browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={}
        )
        assert any(opt["action"] == "retry" for opt in result1["recovery_options"])
        
        # Test unexpected page recovery options
        result2 = browser_agent.handle_error_and_pause(
            session_id,
            error_type="unexpected_page",
            error_details={}
        )
        assert any(opt["action"] == "go_back" for opt in result2["recovery_options"])
        
        # Test session timeout recovery options
        result3 = browser_agent.handle_error_and_pause(
            session_id,
            error_type="session_timeout",
            error_details={}
        )
        assert any(opt["action"] == "re_authenticate" for opt in result3["recovery_options"])


class TestErrorRecovery:
    """Test error recovery mechanisms - Requirement 12.27"""
    
    def test_recovery_retry_action(self, browser_agent, test_workflow):
        """Test retry recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Pause session with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={}
        )
        
        # Attempt retry recovery
        result = browser_agent.attempt_error_recovery(session_id, "retry")
        
        assert result["success"] is True
        assert result["recovery_action"] == "retry"
        assert result["session_resumed"] is True
        
        # Verify session is running again
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.RUNNING
        assert session.session_state.requires_user_action is False
    
    def test_recovery_skip_step_action(self, browser_agent, test_workflow):
        """Test skip step recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session and set to step 1
        browser_agent.start_session(session_id)
        session = browser_agent.sessions[session_id]
        session.current_step = 1
        
        # Pause with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={}
        )
        
        # Skip step
        result = browser_agent.attempt_error_recovery(session_id, "skip_step")
        
        assert result["success"] is True
        assert result["recovery_action"] == "skip_step"
        assert result["session_resumed"] is True
        
        # Verify step was incremented
        assert session.current_step == 2
    
    def test_recovery_go_back_action(self, browser_agent, test_workflow):
        """Test go back recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session and set to step 2
        browser_agent.start_session(session_id)
        session = browser_agent.sessions[session_id]
        session.current_step = 2
        
        # Pause with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="unexpected_page",
            error_details={}
        )
        
        # Go back
        result = browser_agent.attempt_error_recovery(session_id, "go_back")
        
        assert result["success"] is True
        assert result["recovery_action"] == "go_back"
        assert result["session_resumed"] is True
        
        # Verify step was decremented
        assert session.current_step == 1
    
    def test_recovery_restart_action(self, browser_agent, test_workflow):
        """Test restart recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session and set to step 2
        browser_agent.start_session(session_id)
        session = browser_agent.sessions[session_id]
        session.current_step = 2
        
        # Pause with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="unexpected_page",
            error_details={}
        )
        
        # Restart
        result = browser_agent.attempt_error_recovery(session_id, "restart")
        
        assert result["success"] is True
        assert result["recovery_action"] == "restart"
        assert result["session_resumed"] is True
        
        # Verify step was reset to 0
        assert session.current_step == 0
    
    def test_recovery_re_authenticate_action(self, browser_agent, test_workflow):
        """Test re-authenticate recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Set up session with valid cookies
        session = browser_agent.sessions[session_id]
        session.session_state.session_valid = True
        session.session_state.cookies = {"JSESSIONID": "test123"}
        
        # Pause with session timeout
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="session_timeout",
            error_details={}
        )
        
        # Re-authenticate
        result = browser_agent.attempt_error_recovery(session_id, "re_authenticate")
        
        assert result["success"] is True
        assert result["recovery_action"] == "re_authenticate"
        assert result["action_required"] == "authentication"
        
        # Verify session state was cleared
        assert session.session_state.session_valid is False
        assert len(session.session_state.cookies) == 0
    
    def test_recovery_continue_action(self, browser_agent, test_workflow):
        """Test continue recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Pause with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="unexpected_page",
            error_details={}
        )
        
        # Continue
        result = browser_agent.attempt_error_recovery(session_id, "continue")
        
        assert result["success"] is True
        assert result["recovery_action"] == "continue"
        assert result["session_resumed"] is True
        
        # Verify session is running
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.RUNNING
    
    def test_recovery_manual_intervention_action(self, browser_agent, test_workflow):
        """Test manual intervention recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Pause with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="element_not_found",
            error_details={}
        )
        
        # Manual intervention
        result = browser_agent.attempt_error_recovery(session_id, "manual_intervention")
        
        assert result["success"] is True
        assert result["recovery_action"] == "manual_intervention"
        assert result["session_paused"] is True
        
        # Verify session remains paused
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.PAUSED
    
    def test_recovery_cancel_action(self, browser_agent, test_workflow):
        """Test cancel recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Pause with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={}
        )
        
        # Cancel
        result = browser_agent.attempt_error_recovery(session_id, "cancel")
        
        assert result["success"] is True
        assert result["recovery_action"] == "cancel"
        assert result["session_cancelled"] is True
        
        # Verify session is failed
        session = browser_agent.sessions[session_id]
        assert session.status == AutomationStatus.FAILED
    
    def test_recovery_unknown_action(self, browser_agent, test_workflow):
        """Test handling of unknown recovery action"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Pause with error
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={}
        )
        
        # Unknown action
        result = browser_agent.attempt_error_recovery(session_id, "unknown_action")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_recovery_logs_action(self, browser_agent, test_workflow):
        """Test that recovery attempts are logged"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Pause and recover
        browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details={}
        )
        browser_agent.attempt_error_recovery(session_id, "retry")
        
        # Get action logs
        logs = browser_agent.get_action_logs(session_id)
        
        # Verify recovery was logged
        recovery_logs = [log for log in logs if "recovery" in log.get("details", {}).get("action", "")]
        assert len(recovery_logs) > 0


class TestSessionTimeoutDetection:
    """Test session timeout detection and re-authentication - Requirements 12.9, 12.27"""
    
    def test_detect_session_expiry_when_invalid(self, browser_agent, test_workflow):
        """Test detection of expired session"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Set session as invalid
        session = browser_agent.sessions[session_id]
        session.session_state.session_valid = False
        
        # Detect expiry
        is_expired = browser_agent.detect_session_expiry(session_id)
        
        assert is_expired is True
    
    def test_detect_session_expiry_when_no_cookies(self, browser_agent, test_workflow):
        """Test detection of expired session when cookies are missing"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Clear cookies
        session = browser_agent.sessions[session_id]
        session.session_state.cookies = {}
        
        # Detect expiry
        is_expired = browser_agent.detect_session_expiry(session_id)
        
        assert is_expired is True
    
    def test_detect_session_valid(self, browser_agent, test_workflow):
        """Test detection when session is valid"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Set up valid session
        session = browser_agent.sessions[session_id]
        session.session_state.session_valid = True
        session.session_state.cookies = {"JSESSIONID": "test123"}
        
        # Detect expiry
        is_expired = browser_agent.detect_session_expiry(session_id)
        
        assert is_expired is False
    
    def test_session_expiry_logs_detection(self, browser_agent, test_workflow):
        """Test that session expiry detection is logged"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Set session as invalid
        session = browser_agent.sessions[session_id]
        session.session_state.session_valid = False
        
        # Detect expiry
        browser_agent.detect_session_expiry(session_id)
        
        # Get action logs
        logs = browser_agent.get_action_logs(session_id)
        
        # Verify expiry was logged
        expiry_logs = [log for log in logs if "session_expired_detected" in log.get("details", {}).get("action", "")]
        assert len(expiry_logs) > 0


class TestIntegratedErrorHandling:
    """Test integrated error handling in workflows"""
    
    def test_workflow_handles_navigation_failure(self, browser_agent, test_workflow):
        """Test that workflow properly handles navigation failures"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session
        browser_agent.start_session(session_id)
        
        # Simulate navigation to error page
        browser_agent.navigate_to(session_id, "https://example.gov.in/error")
        
        # Detect and handle failure
        detection = browser_agent.detect_navigation_failure(session_id)
        
        if detection["navigation_failed"]:
            result = browser_agent.handle_error_and_pause(
                session_id,
                error_type="navigation_failure",
                error_details=detection
            )
            
            assert result["session_paused"] is True
            assert len(result["recovery_options"]) > 0
    
    def test_workflow_handles_unexpected_page(self, browser_agent, test_workflow):
        """Test that workflow properly handles unexpected pages"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session
        browser_agent.start_session(session_id)
        
        # Simulate navigation to unexpected page
        browser_agent.navigate_to(session_id, "https://example.gov.in/maintenance")
        
        # Detect and handle unexpected page
        detection = browser_agent.detect_unexpected_page(
            session_id,
            expected_page_indicators=["application"]
        )
        
        if detection["is_unexpected"]:
            result = browser_agent.handle_error_and_pause(
                session_id,
                error_type="unexpected_page",
                error_details=detection
            )
            
            assert result["session_paused"] is True
            assert any(opt["action"] == "go_back" for opt in result["recovery_options"])
    
    def test_complete_error_recovery_flow(self, browser_agent, test_workflow):
        """Test complete error detection, handling, and recovery flow"""
        session_id = browser_agent.create_session(
            user_id="user123",
            service_id="test_service",
            portal_url="https://example.gov.in",
            workflow=test_workflow
        )
        
        # Start session
        browser_agent.start_session(session_id)
        initial_status = browser_agent.sessions[session_id].status
        assert initial_status == AutomationStatus.RUNNING
        
        # Simulate error
        browser_agent.navigate_to(session_id, "https://example.gov.in/error")
        detection = browser_agent.detect_navigation_failure(session_id)
        assert detection["navigation_failed"] is True
        
        # Handle error
        error_result = browser_agent.handle_error_and_pause(
            session_id,
            error_type="navigation_failure",
            error_details=detection
        )
        assert error_result["session_paused"] is True
        assert browser_agent.sessions[session_id].status == AutomationStatus.PAUSED
        
        # Recover
        recovery_result = browser_agent.attempt_error_recovery(session_id, "retry")
        assert recovery_result["success"] is True
        assert recovery_result["session_resumed"] is True
        assert browser_agent.sessions[session_id].status == AutomationStatus.RUNNING
