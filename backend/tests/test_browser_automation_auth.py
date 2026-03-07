"""
Unit tests for browser automation authentication handling

Tests credential entry, OTP handling, biometric authentication,
session cookie management, and automatic re-authentication.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from app.services.browser_automation import (
    BrowserAutomationAgent,
    AutomationStatus,
    ActionType
)
from app.models.automation import (
    WorkflowDefinition,
    FormField
)


@pytest.fixture
def mock_credential_store():
    """Create mock credential store"""
    store = Mock()
    store.get_credential = Mock(return_value={
        "credential_id": "cred_123",
        "portal_name": "aadhaar_portal",
        "portal_url": "https://uidai.gov.in",
        "username": "test_user",
        "password": "test_password",
        "auth_methods": ["PASSWORD"],
        "mobile_number": "9876543210",
        "aadhaar_number": None
    })
    return store


@pytest.fixture
def automation_agent(mock_credential_store):
    """Create automation agent with mock credential store"""
    return BrowserAutomationAgent(credential_store=mock_credential_store)


@pytest.fixture
def test_workflow():
    """Create test workflow"""
    return WorkflowDefinition(
        service_id="aadhaar_update",
        workflow_name="Aadhaar Update",
        portal_url="https://uidai.gov.in",
        auth_required=True,
        field_mappings={},
        steps=[
            {
                "step_number": 1,
                "step_name": "Login",
                "page_url": "https://uidai.gov.in/login",
                "actions": [],
                "form_fields": []
            }
        ]
    )


class TestCredentialEntry:
    """Test credential entry automation - Requirements 12.2, 12.3, 12.4"""
    
    def test_authenticate_portal_with_password(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test password-based authentication"""
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Start session
        automation_agent.start_session(session_id)
        
        # Authenticate
        result = automation_agent.authenticate_portal(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify authentication succeeded
        assert result["success"] is True
        assert result["session_valid"] is True
        
        # Verify credentials were retrieved
        mock_credential_store.get_credential.assert_called_once_with(
            "user_123",
            "aadhaar_portal"
        )
        
        # Verify action was logged
        logs = automation_agent.get_action_logs(session_id)
        auth_logs = [log for log in logs if "credential_entry" in log["details"].get("action", "")]
        assert len(auth_logs) > 0
    
    def test_authenticate_portal_no_credentials(
        self,
        automation_agent,
        test_workflow
    ):
        """Test authentication when no credentials are stored"""
        # Mock credential store to return None
        automation_agent.credential_store.get_credential = Mock(return_value=None)
        
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Authenticate
        result = automation_agent.authenticate_portal(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify authentication failed
        assert result["success"] is False
        assert "No credentials found" in result["error"]
        assert result["action_required"] == "store_credentials"
    
    def test_authenticate_portal_multiple_auth_methods(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test authentication with multiple methods - Requirements 12.4, 12.28"""
        # Configure credentials with multiple auth methods
        mock_credential_store.get_credential = Mock(return_value={
            "credential_id": "cred_123",
            "portal_name": "aadhaar_portal",
            "portal_url": "https://uidai.gov.in",
            "username": "test_user",
            "password": "test_password",
            "auth_methods": ["PASSWORD", "MOBILE_OTP"],
            "mobile_number": "9876543210",
            "aadhaar_number": None
        })
        
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Authenticate
        result = automation_agent.authenticate_portal(
            session_id,
            "aadhaar_portal"
        )
        
        # Should prompt for OTP after password entry
        assert result["success"] is True
        assert result["action_required"] == "otp_entry"


class TestOTPHandling:
    """Test OTP prompt and entry handling - Requirements 12.5, 12.6"""
    
    def test_otp_authentication_prompt(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test OTP authentication prompts user"""
        # Configure credentials with OTP auth
        mock_credential_store.get_credential = Mock(return_value={
            "credential_id": "cred_123",
            "portal_name": "aadhaar_portal",
            "portal_url": "https://uidai.gov.in",
            "username": "test_user",
            "password": None,
            "auth_methods": ["MOBILE_OTP"],
            "mobile_number": "9876543210",
            "aadhaar_number": None
        })
        
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Authenticate
        result = automation_agent.authenticate_portal(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify OTP prompt
        assert result["success"] is True
        assert result["action_required"] == "otp_entry"
        assert "OTP" in result["message"]
        assert result["session_paused"] is True
        
        # Verify session is paused
        session_state = automation_agent.get_session_state(session_id)
        assert session_state["status"] == AutomationStatus.WAITING_FOR_USER
        assert session_state["pending_otp"] is True
    
    def test_otp_entry_and_resume(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test OTP entry resumes automation within 3 seconds - Requirement 12.6"""
        # Configure credentials with OTP auth
        mock_credential_store.get_credential = Mock(return_value={
            "credential_id": "cred_123",
            "portal_name": "aadhaar_portal",
            "portal_url": "https://uidai.gov.in",
            "username": "test_user",
            "password": None,
            "auth_methods": ["OTP"],
            "mobile_number": "9876543210",
            "aadhaar_number": None
        })
        
        # Create session and authenticate
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        
        # Enter OTP
        start_time = datetime.now()
        result = automation_agent.enter_otp(session_id, "123456")
        end_time = datetime.now()
        
        # Verify OTP entry succeeded
        assert result["success"] is True
        assert result["session_resumed"] is True
        
        # Verify session resumed
        session_state = automation_agent.get_session_state(session_id)
        assert session_state["status"] == AutomationStatus.RUNNING
        assert session_state["pending_otp"] is False
        
        # Verify processing time (should be near-instant in tests)
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 3  # Should complete within 3 seconds
        
        # Verify action was logged
        logs = automation_agent.get_action_logs(session_id)
        otp_logs = [log for log in logs if "otp_entry" in log["details"].get("action", "")]
        assert len(otp_logs) > 0
    
    def test_otp_entry_without_pending_otp(
        self,
        automation_agent,
        test_workflow
    ):
        """Test OTP entry fails when no OTP is pending"""
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Try to enter OTP without authentication
        result = automation_agent.enter_otp(session_id, "123456")
        
        # Verify it fails
        assert result["success"] is False
        assert "No OTP pending" in result["error"]
    
    def test_otp_masked_mobile_number(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test OTP prompt masks mobile number for privacy"""
        # Configure credentials with mobile number
        mock_credential_store.get_credential = Mock(return_value={
            "credential_id": "cred_123",
            "portal_name": "aadhaar_portal",
            "portal_url": "https://uidai.gov.in",
            "username": "test_user",
            "password": None,
            "auth_methods": ["MOBILE_OTP"],
            "mobile_number": "9876543210",
            "aadhaar_number": None
        })
        
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Authenticate
        result = automation_agent.authenticate_portal(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify mobile number is masked
        assert "***3210" in result["message"]
        assert "9876543210" not in result["message"]


class TestBiometricAuthentication:
    """Test biometric authentication handling - Requirement 12.7"""
    
    def test_biometric_authentication_pause(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test biometric authentication pauses and provides instructions"""
        # Configure credentials with biometric auth
        mock_credential_store.get_credential = Mock(return_value={
            "credential_id": "cred_123",
            "portal_name": "aadhaar_portal",
            "portal_url": "https://uidai.gov.in",
            "username": "test_user",
            "password": None,
            "auth_methods": ["BIOMETRIC"],
            "mobile_number": None,
            "aadhaar_number": None
        })
        
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Authenticate
        result = automation_agent.authenticate_portal(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify biometric prompt
        assert result["success"] is True
        assert result["action_required"] == "biometric_verification"
        assert "Biometric authentication required" in result["message"]
        assert result["session_paused"] is True
        assert "instructions" in result
        
        # Verify instructions are provided
        instructions = result["instructions"]
        assert "biometric verification" in instructions.lower()
        assert "finger" in instructions.lower() or "camera" in instructions.lower()
        
        # Verify session is paused
        session_state = automation_agent.get_session_state(session_id)
        assert session_state["status"] == AutomationStatus.WAITING_FOR_USER
        assert session_state["pending_biometric"] is True
    
    def test_biometric_confirmation_and_resume(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test biometric confirmation resumes automation"""
        # Configure credentials with biometric auth
        mock_credential_store.get_credential = Mock(return_value={
            "credential_id": "cred_123",
            "portal_name": "aadhaar_portal",
            "portal_url": "https://uidai.gov.in",
            "username": "test_user",
            "password": None,
            "auth_methods": ["BIOMETRIC"],
            "mobile_number": None,
            "aadhaar_number": None
        })
        
        # Create session and authenticate
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        
        # Confirm biometric complete
        result = automation_agent.confirm_biometric_complete(session_id)
        
        # Verify confirmation succeeded
        assert result["success"] is True
        assert result["session_resumed"] is True
        
        # Verify session resumed
        session_state = automation_agent.get_session_state(session_id)
        assert session_state["status"] == AutomationStatus.RUNNING
        assert session_state["pending_biometric"] is False


class TestSessionCookieManagement:
    """Test session cookie management - Requirement 12.8"""
    
    def test_store_session_cookies_after_auth(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test session cookies are stored after successful authentication"""
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Authenticate
        result = automation_agent.authenticate_portal(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify cookies were stored
        session_state = automation_agent.get_session_state(session_id)
        assert session_state["has_cookies"] is True
        assert session_state["session_valid"] is True
        
        # Verify action was logged
        logs = automation_agent.get_action_logs(session_id)
        cookie_logs = [log for log in logs if "store_cookies" in log["details"].get("action", "")]
        assert len(cookie_logs) > 0
    
    def test_check_session_validity(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test session validity checking"""
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Initially no cookies
        assert automation_agent.check_session_validity(session_id) is False
        
        # Authenticate
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        
        # Now session should be valid
        assert automation_agent.check_session_validity(session_id) is True
    
    def test_session_cookies_maintained_throughout_session(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test session cookies are maintained throughout automation session"""
        # Create session and authenticate
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        
        # Perform various actions
        automation_agent.navigate_to(session_id, "https://uidai.gov.in/form")
        automation_agent.click_element(session_id, "submit_button")
        
        # Verify session is still valid
        assert automation_agent.check_session_validity(session_id) is True
        
        session_state = automation_agent.get_session_state(session_id)
        assert session_state["has_cookies"] is True
        assert session_state["session_valid"] is True


class TestAutomaticReAuthentication:
    """Test automatic re-authentication - Requirements 12.9, 12.27"""
    
    def test_detect_session_expiry(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test session expiry detection"""
        # Create session and authenticate
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        
        # Initially session is valid
        assert automation_agent.detect_session_expiry(session_id) is False
        
        # Simulate session expiry
        session = automation_agent.sessions[session_id]
        session.session_state.session_valid = False
        
        # Now expiry should be detected
        assert automation_agent.detect_session_expiry(session_id) is True
        
        # Verify action was logged
        logs = automation_agent.get_action_logs(session_id)
        expiry_logs = [log for log in logs if "session_expired_detected" in log["details"].get("action", "")]
        assert len(expiry_logs) > 0
    
    def test_automatic_re_authentication(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test automatic re-authentication when session expires"""
        # Create session and authenticate
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        
        # Simulate session expiry
        session = automation_agent.sessions[session_id]
        session.session_state.session_valid = False
        session.session_state.cookies = {}
        
        # Re-authenticate
        result = automation_agent.re_authenticate(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify re-authentication succeeded
        assert result["success"] is True
        assert result["session_valid"] is True
        
        # Verify session is valid again
        assert automation_agent.check_session_validity(session_id) is True
        
        # Verify actions were logged
        logs = automation_agent.get_action_logs(session_id)
        reauth_logs = [
            log for log in logs
            if "re_authentication" in log["details"].get("action", "")
        ]
        assert len(reauth_logs) >= 2  # Started and successful
    
    def test_re_authentication_failure_handling(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test re-authentication failure is handled properly"""
        # Mock credential store to fail
        mock_credential_store.get_credential = Mock(return_value=None)
        
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Try to re-authenticate
        result = automation_agent.re_authenticate(
            session_id,
            "aadhaar_portal"
        )
        
        # Verify re-authentication failed
        assert result["success"] is False
        assert "error" in result
        
        # Verify failure was logged
        logs = automation_agent.get_action_logs(session_id)
        failed_logs = [
            log for log in logs
            if "re_authentication_failed" in log["details"].get("action", "")
        ]
        assert len(failed_logs) > 0


class TestAuthenticationLogging:
    """Test authentication action logging - Requirement 12.20"""
    
    def test_authentication_attempts_logged(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test all authentication attempts are logged"""
        # Create session
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        # Authenticate
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        
        # Get logs
        logs = automation_agent.get_action_logs(session_id)
        
        # Verify authentication was logged
        auth_logs = [
            log for log in logs
            if "credential_entry" in log["details"].get("action", "") or
               "authentication" in log["details"].get("action", "")
        ]
        assert len(auth_logs) > 0
        
        # Verify log contains relevant information
        for log in auth_logs:
            assert "timestamp" in log
            assert "success" in log
            assert "details" in log
    
    def test_otp_entry_logged_without_exposing_otp(
        self,
        automation_agent,
        test_workflow,
        mock_credential_store
    ):
        """Test OTP entry is logged without exposing actual OTP value"""
        # Configure credentials with OTP auth
        mock_credential_store.get_credential = Mock(return_value={
            "credential_id": "cred_123",
            "portal_name": "aadhaar_portal",
            "portal_url": "https://uidai.gov.in",
            "username": "test_user",
            "password": None,
            "auth_methods": ["OTP"],
            "mobile_number": "9876543210",
            "aadhaar_number": None
        })
        
        # Create session and authenticate
        session_id = automation_agent.create_session(
            user_id="user_123",
            service_id="aadhaar_update",
            portal_url="https://uidai.gov.in",
            workflow=test_workflow
        )
        
        automation_agent.authenticate_portal(session_id, "aadhaar_portal")
        automation_agent.enter_otp(session_id, "123456")
        
        # Get logs
        logs = automation_agent.get_action_logs(session_id)
        
        # Verify OTP entry was logged
        otp_logs = [log for log in logs if "otp_entry" in log["details"].get("action", "")]
        assert len(otp_logs) > 0
        
        # Verify actual OTP is not in logs
        for log in otp_logs:
            log_str = str(log)
            assert "123456" not in log_str
            # Should only log OTP length, not value
            assert "otp_length" in log["details"]
