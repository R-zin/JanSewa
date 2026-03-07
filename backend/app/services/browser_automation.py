"""
Browser Automation Agent Service

Manages browser automation sessions for government portal interactions.
Handles navigation, form filling, and document uploads.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from app.models.automation import (
    FormField, NavigationAction, SessionState, WorkflowDefinition
)
from app.services.form_filler import form_filler, FormSummary


class AutomationStatus(str, Enum):
    """Automation session status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionType(str, Enum):
    """Types of automation actions"""
    NAVIGATE = "navigate"
    FILL_FIELD = "fill_field"
    CLICK = "click"
    UPLOAD_FILE = "upload_file"
    WAIT = "wait"
    SUBMIT = "submit"


class ActionLog(BaseModel):
    """Log entry for automation action"""
    action_id: str
    action_type: ActionType
    timestamp: datetime
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class AutomationSession(BaseModel):
    """Represents a browser automation session"""
    session_id: str
    user_id: str
    service_id: str
    portal_url: str
    status: AutomationStatus
    current_step: int
    total_steps: int
    workflow: WorkflowDefinition
    session_state: SessionState
    action_logs: List[ActionLog]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BrowserAutomationAgent:
    """
    Manages browser automation for government portals.
    Handles form filling, navigation, document uploads, and authentication.
    """

    def __init__(self, credential_store=None):
        """
        Initialize browser automation agent

        Args:
            credential_store: CredentialStore instance for retrieving credentials
        """
        self.sessions: Dict[str, AutomationSession] = {}
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.credential_store = credential_store
        self.pending_otp_sessions: Dict[str, str] = {}  # session_id -> field_id
        self.pending_biometric_sessions: Dict[str, str] = {}  # session_id -> instructions
        self.form_summaries: Dict[str, FormSummary] = {}  # session_id -> form summary

    def create_session(
        self,
        user_id: str,
        service_id: str,
        portal_url: str,
        workflow: WorkflowDefinition
    ) -> str:
        """
        Create a new automation session

        Args:
            user_id: User ID
            service_id: Service being automated
            portal_url: Portal URL
            workflow: Workflow definition

        Returns:
            Session ID
        """
        session_id = f"auto_{user_id}_{service_id}_{datetime.now().timestamp()}"

        session = AutomationSession(
            session_id=session_id,
            user_id=user_id,
            service_id=service_id,
            portal_url=portal_url,
            status=AutomationStatus.IDLE,
            current_step=0,
            total_steps=len(workflow.steps),
            workflow=workflow,
            session_state=SessionState(
                current_url=portal_url,
                current_step=0,
                total_steps=len(workflow.steps),
                form_fields_filled=0,
                total_form_fields=0,
                is_authenticated=False,
                requires_user_action=False,
                user_action_type=None
            ),
            action_logs=[],
            created_at=datetime.now()
        )

        self.sessions[session_id] = session
        return session_id

    def start_session(self, session_id: str) -> bool:
        """
        Start automation session

        Args:
            session_id: Session ID

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.status = AutomationStatus.RUNNING
        session.started_at = datetime.now()

        self._log_action(
            session_id,
            ActionType.NAVIGATE,
            {"url": session.portal_url},
            True
        )

        return True

    def authenticate_portal(
        self,
        session_id: str,
        portal_name: str
    ) -> Dict[str, Any]:
        """
        Authenticate to government portal using stored credentials.
        Handles multiple authentication methods including password, OTP, and biometric.

        Requirements: 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.28

        Args:
            session_id: Session ID
            portal_name: Name of the portal to authenticate

        Returns:
            Authentication result with status and next action
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        # Retrieve credentials from credential store
        if not self.credential_store:
            return {"success": False, "error": "Credential store not configured"}

        credentials = self.credential_store.get_credential(
            session.user_id,
            portal_name
        )

        if not credentials:
            return {
                "success": False,
                "error": "No credentials found for portal",
                "action_required": "store_credentials"
            }

        try:
            # Determine authentication method
            auth_methods = credentials.get("auth_methods", [])

            # Perform credential entry for password-based auth
            if "password" in [m.lower() for m in auth_methods]:
                success = self._enter_credentials(
                    session_id,
                    credentials["username"],
                    credentials.get("password")
                )

                if not success:
                    return {
                        "success": False,
                        "error": "Failed to enter credentials"
                    }

                self._log_action(
                    session_id,
                    ActionType.FILL_FIELD,
                    {
                        "action": "credential_entry",
                        "username": credentials["username"],
                        "auth_method": "password"
                    },
                    True
                )

            # Check if OTP is required
            if any(m.lower() in ["otp", "mobile_otp", "aadhaar_otp"] for m in auth_methods):
                return self._handle_otp_authentication(session_id, credentials)

            # Check if biometric is required
            if "biometric" in [m.lower() for m in auth_methods]:
                return self._handle_biometric_authentication(session_id)

            # Store session cookies after successful authentication
            self._store_session_cookies(session_id)

            return {
                "success": True,
                "message": "Authentication successful",
                "session_valid": True
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {"action": "authentication", "portal": portal_name},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def _enter_credentials(
        self,
        session_id: str,
        username: str,
        password: Optional[str]
    ) -> bool:
        """
        Enter username and password into login form.

        Requirements: 12.3, 12.4

        Args:
            session_id: Session ID
            username: Username/login ID
            password: Password

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Locate username field (by id, name, or common patterns)
            # 2. Fill username
            # 3. Locate password field
            # 4. Fill password
            # 5. Click login button

            # Store in session state for tracking
            session.session_state.form_data["username"] = username
            if password:
                session.session_state.form_data["password"] = "***"  # Don't log actual password

            return True

        except Exception:
            return False

    def _handle_otp_authentication(
        self,
        session_id: str,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle OTP authentication flow.
        Pauses automation and prompts user to enter OTP.

        Requirements: 12.5, 12.6

        Args:
            session_id: Session ID
            credentials: Portal credentials

        Returns:
            Authentication status with OTP prompt
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        # Pause session for OTP entry
        session.status = AutomationStatus.WAITING_FOR_USER
        self.pending_otp_sessions[session_id] = "otp_field"

        # Determine OTP delivery method
        mobile_number = credentials.get("mobile_number")
        otp_message = "Please enter the OTP sent to your registered mobile number"
        if mobile_number:
            # Mask mobile number for privacy
            masked_mobile = f"***{mobile_number[-4:]}" if len(mobile_number) > 4 else "***"
            otp_message = f"Please enter the OTP sent to {masked_mobile}"

        self._log_action(
            session_id,
            ActionType.WAIT,
            {
                "action": "otp_prompt",
                "message": otp_message
            },
            True
        )

        return {
            "success": True,
            "action_required": "otp_entry",
            "message": otp_message,
            "prompt": "Enter OTP",
            "session_paused": True
        }

    def enter_otp(
        self,
        session_id: str,
        otp_value: str
    ) -> Dict[str, Any]:
        """
        Enter OTP and continue authentication.
        Resumes automation within 3 seconds of receiving OTP.

        Requirements: 12.6

        Args:
            session_id: Session ID
            otp_value: OTP entered by user

        Returns:
            Authentication result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        if session_id not in self.pending_otp_sessions:
            return {"success": False, "error": "No OTP pending for this session"}

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Locate OTP input field
            # 2. Fill OTP value
            # 3. Click submit/verify button

            # Store OTP entry (masked for logging)
            session.session_state.form_data["otp"] = "***"

            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {
                    "action": "otp_entry",
                    "otp_length": len(otp_value)
                },
                True
            )

            # Remove from pending and resume session
            del self.pending_otp_sessions[session_id]
            session.status = AutomationStatus.RUNNING

            # Store session cookies after successful OTP verification
            self._store_session_cookies(session_id)

            return {
                "success": True,
                "message": "OTP entered successfully",
                "session_resumed": True
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {"action": "otp_entry"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def _handle_biometric_authentication(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Handle biometric authentication flow.
        Pauses automation and instructs user to complete biometric verification.

        Requirements: 12.7

        Args:
            session_id: Session ID

        Returns:
            Authentication status with biometric instructions
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        # Pause session for biometric verification
        session.status = AutomationStatus.WAITING_FOR_USER

        instructions = (
            "Biometric authentication required. "
            "Please complete the biometric verification on your device:\n"
            "1. Follow the on-screen prompts\n"
            "2. Place your finger on the scanner or look at the camera\n"
            "3. Wait for verification to complete\n"
            "4. Click 'Continue' once verification is successful"
        )

        self.pending_biometric_sessions[session_id] = instructions

        self._log_action(
            session_id,
            ActionType.WAIT,
            {
                "action": "biometric_prompt",
                "instructions": instructions
            },
            True
        )

        return {
            "success": True,
            "action_required": "biometric_verification",
            "message": "Biometric authentication required",
            "instructions": instructions,
            "session_paused": True
        }

    def confirm_biometric_complete(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Confirm biometric verification is complete and resume automation.

        Requirements: 12.7

        Args:
            session_id: Session ID

        Returns:
            Authentication result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        if session_id not in self.pending_biometric_sessions:
            return {"success": False, "error": "No biometric verification pending"}

        session = self.sessions[session_id]

        self._log_action(
            session_id,
            ActionType.WAIT,
            {"action": "biometric_complete"},
            True
        )

        # Remove from pending and resume session
        del self.pending_biometric_sessions[session_id]
        session.status = AutomationStatus.RUNNING

        # Store session cookies after successful biometric verification
        self._store_session_cookies(session_id)

        return {
            "success": True,
            "message": "Biometric verification confirmed",
            "session_resumed": True
        }

    def _store_session_cookies(self, session_id: str) -> bool:
        """
        Store session cookies to maintain login session.

        Requirements: 12.8

        Args:
            session_id: Session ID

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Get all cookies from browser
            # 2. Store session cookies (JSESSIONID, auth tokens, etc.)

            # Simulate storing cookies
            session.session_state.cookies = {
                "JSESSIONID": f"session_{session_id}",
                "auth_token": f"token_{datetime.now().timestamp()}",
                "session_timestamp": datetime.now().isoformat()
            }

            session.session_state.session_valid = True

            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "store_cookies", "cookie_count": len(session.session_state.cookies)},
                True
            )

            return True

        except Exception:
            return False

    def check_session_validity(self, session_id: str) -> bool:
        """
        Check if login session is still valid.

        Requirements: 12.8, 12.9

        Args:
            session_id: Session ID

        Returns:
            True if session is valid
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        # In production, check:
        # 1. If cookies are still valid
        # 2. If session hasn't timed out
        # 3. If we can access authenticated pages

        # Check if cookies exist and session is marked valid
        has_cookies = bool(session.session_state.cookies)
        is_valid = session.session_state.session_valid

        return has_cookies and is_valid

    def detect_session_expiry(self, session_id: str) -> bool:
        """
        Detect if session has expired during automation.

        Requirements: 12.9, 12.27

        Args:
            session_id: Session ID

        Returns:
            True if session has expired
        """
        if session_id not in self.sessions:
            return True

        session = self.sessions[session_id]

        # In production, detect expiry by:
        # 1. Checking for timeout messages on page
        # 2. Detecting redirect to login page
        # 3. Checking if authenticated API calls fail
        # 4. Monitoring cookie expiration

        # Check session validity flag
        if not session.session_state.session_valid:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "session_expired_detected"},
                True
            )
            return True

        # Check if cookies are missing
        if not session.session_state.cookies:
            return True

        return False

    def re_authenticate(
        self,
        session_id: str,
        portal_name: str
    ) -> Dict[str, Any]:
        """
        Automatically re-authenticate when session expires.

        Requirements: 12.9, 12.27

        Args:
            session_id: Session ID
            portal_name: Portal name

        Returns:
            Re-authentication result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        self._log_action(
            session_id,
            ActionType.WAIT,
            {"action": "re_authentication_started", "portal": portal_name},
            True
        )

        # Clear old session state
        session.session_state.cookies = {}
        session.session_state.session_valid = False

        # Attempt authentication again
        result = self.authenticate_portal(session_id, portal_name)

        if result.get("success"):
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "re_authentication_successful"},
                True
            )
        else:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "re_authentication_failed"},
                False,
                result.get("error", "Unknown error")
            )

        return result

    def pause_session(self, session_id: str, reason: str = "") -> bool:
        """
        Pause automation session

        Args:
            session_id: Session ID
            reason: Reason for pausing

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.status = AutomationStatus.PAUSED

        self._log_action(
            session_id,
            ActionType.WAIT,
            {"reason": reason},
            True
        )

        return True

    def resume_session(self, session_id: str) -> bool:
        """
        Resume paused session

        Args:
            session_id: Session ID

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        if session.status != AutomationStatus.PAUSED:
            return False

        session.status = AutomationStatus.RUNNING
        return True

    def navigate_to(self, session_id: str, url: str) -> bool:
        """
        Navigate to URL

        Args:
            session_id: Session ID
            url: Target URL

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to navigate
            session.session_state.current_url = url

            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"url": url},
                True
            )
            return True

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"url": url},
                False,
                str(e)
            )
            return False

    def fill_form_field(
        self,
        session_id: str,
        field: FormField,
        value: str
    ) -> bool:
        """
        Fill a form field

        Args:
            session_id: Session ID
            field: Form field definition
            value: Value to fill

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to fill field
            session.session_state.form_data[field.field_id] = value

            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {
                    "field_id": field.field_id,
                    "field_name": field.field_name,
                    "value_length": len(value)
                },
                True
            )
            return True

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {"field_id": field.field_id},
                False,
                str(e)
            )
            return False

    def upload_document(
        self,
        session_id: str,
        field_id: str,
        document_path: str
    ) -> bool:
        """
        Upload document to form

        Args:
            session_id: Session ID
            field_id: Upload field ID
            document_path: Path to document

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        try:
            # In production, use Selenium/Playwright to upload file
            self._log_action(
                session_id,
                ActionType.UPLOAD_FILE,
                {
                    "field_id": field_id,
                    "document_path": document_path
                },
                True
            )
            return True

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.UPLOAD_FILE,
                {"field_id": field_id},
                False,
                str(e)
            )
            return False

    def click_element(self, session_id: str, element_id: str) -> bool:
        """
        Click an element

        Args:
            session_id: Session ID
            element_id: Element identifier

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        try:
            # In production, use Selenium/Playwright to click
            self._log_action(
                session_id,
                ActionType.CLICK,
                {"element_id": element_id},
                True
            )
            return True

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.CLICK,
                {"element_id": element_id},
                False,
                str(e)
            )
            return False

    def submit_form(self, session_id: str) -> bool:
        """
        Submit current form

        Args:
            session_id: Session ID

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to submit
            self._log_action(
                session_id,
                ActionType.SUBMIT,
                {"form_data_count": len(session.session_state.form_data)},
                True
            )

            # Move to next step
            session.current_step += 1

            # Check if completed
            if session.current_step >= session.total_steps:
                session.status = AutomationStatus.COMPLETED
                session.completed_at = datetime.now()

            return True

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.SUBMIT,
                {},
                False,
                str(e)
            )
            return False

    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """
        Get current session state

        Args:
            session_id: Session ID

        Returns:
            Session state information
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        return {
            "session_id": session.session_id,
            "status": session.status,
            "current_step": session.current_step,
            "total_steps": session.total_steps,
            "progress_percentage": (session.current_step / session.total_steps * 100) if session.total_steps > 0 else 0,
            "current_url": session.session_state.current_url,
            "session_valid": session.session_state.session_valid,
            "has_cookies": bool(session.session_state.cookies),
            "pending_otp": session_id in self.pending_otp_sessions,
            "pending_biometric": session_id in self.pending_biometric_sessions
        }

    def get_action_logs(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get action logs for session

        Args:
            session_id: Session ID
            limit: Maximum number of logs

        Returns:
            List of action logs
        """
        if session_id not in self.sessions:
            return []

        session = self.sessions[session_id]
        logs = session.action_logs[-limit:]

        return [
            {
                "action_id": log.action_id,
                "action_type": log.action_type,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details,
                "success": log.success,
                "error": log.error_message
            }
            for log in logs
        ]

    def _log_action(
        self,
        session_id: str,
        action_type: ActionType,
        details: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log an automation action"""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        action_log = ActionLog(
            action_id=f"action_{len(session.action_logs)}",
            action_type=action_type,
            timestamp=datetime.now(),
            details=details,
            success=success,
            error_message=error_message
        )

        session.action_logs.append(action_log)

    def wait_for_user_input(
        self,
        session_id: str,
        prompt: str,
        input_type: str = "text"
    ) -> bool:
        """
        Pause and wait for user input

        Args:
            session_id: Session ID
            prompt: Prompt message for user
            input_type: Type of input needed

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.status = AutomationStatus.WAITING_FOR_USER

        self._log_action(
            session_id,
            ActionType.WAIT,
            {
                "prompt": prompt,
                "input_type": input_type
            },
            True
        )

        return True

    def provide_user_input(
        self,
        session_id: str,
        input_value: str
    ) -> bool:
        """
        Provide user input and resume

        Args:
            session_id: Session ID
            input_value: User's input

        Returns:
            Success status
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if session.status != AutomationStatus.WAITING_FOR_USER:
            return False

        # Store input and resume
        session.status = AutomationStatus.RUNNING

        return True

    def auto_fill_form(
        self,
        session_id: str,
        form_fields: List[Dict[str, Any]],
        extracted_data: Optional[Dict[str, Any]] = None,
        digilocker_data: Optional[Dict[str, Any]] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Automatically fill form fields using prioritized data sources.
        
        Requirements:
        - 12.11: Populate form fields from user profile, stored documents, or extracted data
        - 12.12: Prioritize extracted data from uploaded documents
        - 12.13: Automatically populate fields when extracted data matches
        
        Args:
            session_id: Session ID
            form_fields: List of form field definitions
            extracted_data: Data extracted from OCR
            digilocker_data: Data from DigiLocker documents
            user_profile: User profile data
            
        Returns:
            Result with filled fields and summary
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.sessions[session_id]
        
        try:
            # Use form filler to fill fields
            filled_fields = form_filler.fill_form_fields(
                form_fields,
                extracted_data,
                digilocker_data,
                user_profile
            )
            
            # Validate filled fields
            validation_results = form_filler.validate_form_data(
                filled_fields,
                form_fields
            )
            
            # Generate summary
            summary = form_filler.generate_form_summary(
                filled_fields,
                validation_results,
                len(form_fields)
            )
            
            # Store summary for later review
            self.form_summaries[session_id] = summary
            
            # Actually fill the fields in the browser
            for filled_field in filled_fields:
                if filled_field.validated:
                    # Find the form field definition
                    field_def = next(
                        (f for f in form_fields if f.get("field_id") == filled_field.field_id),
                        None
                    )
                    
                    if field_def:
                        # Create FormField object
                        form_field = FormField(
                            field_id=filled_field.field_id,
                            field_name=filled_field.field_name,
                            field_type=field_def.get("field_type", "text"),
                            label=filled_field.field_name,
                            required=field_def.get("required", False),
                            value=filled_field.value
                        )
                        
                        # Fill the field
                        self.fill_form_field(session_id, form_field, filled_field.value)
            
            # Update session state
            session.session_state.form_fields_filled = len(filled_fields)
            session.session_state.total_form_fields = len(form_fields)
            
            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {
                    "action": "auto_fill_form",
                    "total_fields": len(form_fields),
                    "filled_fields": len(filled_fields),
                    "extracted_data_used": bool(extracted_data),
                    "digilocker_data_used": bool(digilocker_data),
                    "user_profile_used": bool(user_profile)
                },
                True
            )
            
            return {
                "success": True,
                "filled_fields": len(filled_fields),
                "total_fields": len(form_fields),
                "summary": summary.model_dump(),
                "ready_for_review": True
            }
            
        except Exception as e:
            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {"action": "auto_fill_form"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}
    
    def get_form_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get form filling summary for user review.
        
        Requirements: 12.30 - Display summary of populated fields for user review
        
        Args:
            session_id: Session ID
            
        Returns:
            Form summary or None if not available
        """
        if session_id not in self.form_summaries:
            return None
        
        summary = self.form_summaries[session_id]
        
        return {
            "total_fields": summary.total_fields,
            "filled_fields": summary.filled_fields,
            "fields": [
                {
                    "field_id": f.field_id,
                    "field_name": f.field_name,
                    "value": f.value,
                    "source": f.source,
                    "confidence": f.confidence,
                    "validated": f.validated
                }
                for f in summary.fields
            ],
            "validation_results": [
                {
                    "field_id": v.field_id,
                    "is_valid": v.is_valid,
                    "error_message": v.error_message
                }
                for v in summary.validation_results
            ],
            "ready_for_submission": summary.ready_for_submission,
            "warnings": summary.warnings
        }
    
    def validate_form_before_submission(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Validate form data before submission.
        
        Requirements: 12.16 - Validate form data matches field requirements before submission
        
        Args:
            session_id: Session ID
            
        Returns:
            Validation result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}
        
        if session_id not in self.form_summaries:
            return {
                "success": False,
                "error": "No form summary available. Please fill the form first."
            }
        
        summary = self.form_summaries[session_id]
        
        # Check if ready for submission
        if not summary.ready_for_submission:
            validation_errors = [
                v for v in summary.validation_results if not v.is_valid
            ]
            
            return {
                "success": False,
                "ready_for_submission": False,
                "validation_errors": [
                    {
                        "field_id": v.field_id,
                        "error": v.error_message
                    }
                    for v in validation_errors
                ],
                "message": "Form has validation errors. Please correct them before submission."
            }
        
        self._log_action(
            session_id,
            ActionType.WAIT,
            {"action": "form_validation", "result": "passed"},
            True
        )
        
        return {
            "success": True,
            "ready_for_submission": True,
            "message": "Form validation passed. Ready for submission."
        }
    
    def get_unfilled_fields(
        self,
        session_id: str,
        form_fields: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get list of fields that were not automatically filled.
        
        Args:
            session_id: Session ID
            form_fields: All form field definitions
            
        Returns:
            List of unfilled fields
        """
        if session_id not in self.form_summaries:
            return form_fields
        
        summary = self.form_summaries[session_id]
        
        return form_filler.get_unfilled_fields(
            form_fields,
            summary.fields
        )

    def execute_workflow_step(
        self,
        session_id: str,
        step_index: int
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step.

        Requirements: 12.24 - Automatically proceed through workflow steps

        Args:
            session_id: Session ID
            step_index: Index of step to execute

        Returns:
            Step execution result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        if step_index >= len(session.workflow.steps):
            return {"success": False, "error": "Invalid step index"}

        step = session.workflow.steps[step_index]

        try:
            # Execute step based on action type
            action = step.get("action")

            if action == "navigate":
                url = step.get("url")
                success = self.navigate_to(session_id, url)

                return {
                    "success": success,
                    "step": step_index,
                    "action": action,
                    "url": url
                }

            elif action == "fill_form":
                # Form filling handled separately
                return {
                    "success": True,
                    "step": step_index,
                    "action": action,
                    "message": "Form filling ready"
                }

            elif action == "click":
                element_id = step.get("element_id")
                success = self.click_element(session_id, element_id)

                return {
                    "success": success,
                    "step": step_index,
                    "action": action,
                    "element_id": element_id
                }

            elif action == "submit":
                # Submission requires user confirmation
                return {
                    "success": True,
                    "step": step_index,
                    "action": action,
                    "requires_confirmation": True
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action}"
                }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "execute_step", "step": step_index},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def proceed_to_next_step(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Automatically proceed to the next workflow step.

        Requirements: 12.24 - Automatically proceed through all steps

        Args:
            session_id: Session ID

        Returns:
            Next step execution result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        # Check if workflow is complete
        if session.current_step >= session.total_steps:
            return {
                "success": True,
                "workflow_complete": True,
                "message": "All workflow steps completed"
            }

        # Execute next step
        result = self.execute_workflow_step(session_id, session.current_step)

        if result.get("success"):
            # Update current step
            session.current_step += 1
            session.session_state.current_step = session.current_step

            self._log_action(
                session_id,
                ActionType.WAIT,
                {
                    "action": "step_progression",
                    "step": session.current_step,
                    "total_steps": session.total_steps
                },
                True
            )

        return result

    def handle_page_transition(
        self,
        session_id: str,
        expected_url_pattern: Optional[str] = None,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Handle page transitions during multi-step workflows.

        Requirements: 12.24 - Handle page transitions in multi-step workflows

        Args:
            session_id: Session ID
            expected_url_pattern: Expected URL pattern after transition
            timeout_seconds: Maximum time to wait for transition

        Returns:
            Transition result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Wait for page load
            # 2. Check if URL matches expected pattern
            # 3. Verify page elements are loaded
            # 4. Handle any loading indicators

            # Simulate page transition
            start_time = datetime.now()

            # Wait for page to load (simulated)
            # In production, check for document.readyState === 'complete'

            # Verify transition
            current_url = session.session_state.current_url

            transition_success = True
            if expected_url_pattern:
                # In production, use regex to match URL pattern
                transition_success = expected_url_pattern in current_url

            elapsed_time = (datetime.now() - start_time).total_seconds()

            if not transition_success:
                self._log_action(
                    session_id,
                    ActionType.NAVIGATE,
                    {
                        "action": "page_transition_failed",
                        "expected_pattern": expected_url_pattern,
                        "current_url": current_url
                    },
                    False,
                    "Page transition did not match expected pattern"
                )

                return {
                    "success": False,
                    "error": "Page transition failed",
                    "expected_pattern": expected_url_pattern,
                    "current_url": current_url
                }

            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {
                    "action": "page_transition_complete",
                    "current_url": current_url,
                    "elapsed_time": elapsed_time
                },
                True
            )

            return {
                "success": True,
                "current_url": current_url,
                "elapsed_time": elapsed_time,
                "message": "Page transition successful"
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"action": "page_transition"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def detect_final_submission_page(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Detect if current page is a final submission page.

        Requirements: 12.25 - Detect final submission pages and pause for confirmation

        Args:
            session_id: Session ID

        Returns:
            Detection result with submission page indicators
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Look for submit buttons with text like "Submit", "Confirm", "Final Submit"
            # 2. Check for confirmation messages or warnings
            # 3. Look for review/preview sections
            # 4. Check URL patterns (e.g., /confirm, /review, /submit)

            # Simulate detection
            current_url = session.session_state.current_url

            # Check if this is the last step in workflow
            is_last_step = session.current_step >= session.total_steps - 1

            # Check for submission indicators
            submission_indicators = []

            if is_last_step:
                submission_indicators.append("Last workflow step")

            # In production, check page content for submission keywords
            # For now, assume last step is submission
            is_submission_page = is_last_step

            if is_submission_page:
                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {
                        "action": "final_submission_detected",
                        "indicators": submission_indicators
                    },
                    True
                )

            return {
                "success": True,
                "is_submission_page": is_submission_page,
                "indicators": submission_indicators,
                "current_url": current_url
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "detect_submission_page"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def request_submission_confirmation(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Pause automation and request user confirmation before final submission.

        Requirements: 12.25 - Pause for user confirmation before submitting forms

        Args:
            session_id: Session ID

        Returns:
            Confirmation request result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        # Pause session for user confirmation
        session.status = AutomationStatus.WAITING_FOR_USER
        session.session_state.requires_user_action = True
        session.session_state.user_action_type = "submission_confirmation"

        # Get form summary for user review
        form_summary = self.get_form_summary(session_id)

        confirmation_message = (
            "Ready to submit the form. Please review the filled information "
            "and confirm submission."
        )

        self._log_action(
            session_id,
            ActionType.WAIT,
            {
                "action": "submission_confirmation_requested",
                "message": confirmation_message
            },
            True
        )

        return {
            "success": True,
            "action_required": "submission_confirmation",
            "message": confirmation_message,
            "form_summary": form_summary,
            "session_paused": True
        }

    def confirm_and_submit(
        self,
        session_id: str,
        user_confirmed: bool
    ) -> Dict[str, Any]:
        """
        Submit form after receiving user confirmation.

        Requirements: 12.26 - Click submit button and capture confirmation response

        Args:
            session_id: Session ID
            user_confirmed: Whether user confirmed submission

        Returns:
            Submission result with confirmation details
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        if not user_confirmed:
            # User cancelled submission
            session.status = AutomationStatus.PAUSED
            session.session_state.requires_user_action = False

            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "submission_cancelled_by_user"},
                True
            )

            return {
                "success": True,
                "submitted": False,
                "message": "Submission cancelled by user"
            }

        try:
            # In production, use Selenium/Playwright to:
            # 1. Click the submit button
            # 2. Wait for submission to complete
            # 3. Capture confirmation page/message
            # 4. Extract confirmation number/reference

            # Simulate submission
            submission_time = datetime.now()

            # Click submit button
            submit_success = self.submit_form(session_id)

            if not submit_success:
                return {
                    "success": False,
                    "error": "Failed to submit form"
                }

            # Capture confirmation response
            confirmation_data = self._capture_confirmation_response(session_id)

            # Update session state
            session.status = AutomationStatus.COMPLETED
            session.completed_at = submission_time
            session.session_state.requires_user_action = False

            self._log_action(
                session_id,
                ActionType.SUBMIT,
                {
                    "action": "form_submitted",
                    "confirmation": confirmation_data
                },
                True
            )

            return {
                "success": True,
                "submitted": True,
                "submission_time": submission_time.isoformat(),
                "confirmation": confirmation_data,
                "message": "Form submitted successfully"
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.SUBMIT,
                {"action": "form_submission"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def _capture_confirmation_response(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Capture confirmation details after form submission.

        Requirements: 12.26 - Capture confirmation response

        Args:
            session_id: Session ID

        Returns:
            Confirmation details
        """
        if session_id not in self.sessions:
            return {}

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Extract confirmation number/reference ID
            # 2. Capture confirmation message
            # 3. Take screenshot of confirmation page
            # 4. Extract any tracking URLs or next steps

            # Simulate confirmation capture
            confirmation_data = {
                "confirmation_number": f"CONF{datetime.now().timestamp()}",
                "confirmation_message": "Your application has been submitted successfully",
                "submission_date": datetime.now().isoformat(),
                "service_id": session.service_id,
                "portal_url": session.portal_url,
                "reference_url": session.session_state.current_url,
                "next_steps": [
                    "Check your email for confirmation",
                    "Track status using confirmation number",
                    "Download receipt from portal"
                ]
            }

            # Store confirmation in session state
            session.session_state.confirmation_data = confirmation_data

            return confirmation_data

        except Exception:
            return {
                "confirmation_number": None,
                "confirmation_message": "Submission completed",
                "submission_date": datetime.now().isoformat()
            }

    def save_confirmation_to_dashboard(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Save confirmation details to user dashboard.

        Requirements: 12.21 - Save confirmation details to dashboard

        Args:
            session_id: Session ID

        Returns:
            Save result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        # Get confirmation data
        confirmation_data = session.session_state.confirmation_data

        if not confirmation_data:
            return {
                "success": False,
                "error": "No confirmation data available"
            }

        try:
            # In production, save to database:
            # 1. Create service request record
            # 2. Store confirmation details
            # 3. Link to user dashboard
            # 4. Create notification for user

            dashboard_entry = {
                "user_id": session.user_id,
                "service_id": session.service_id,
                "session_id": session_id,
                "confirmation_number": confirmation_data.get("confirmation_number"),
                "submission_date": confirmation_data.get("submission_date"),
                "status": "submitted",
                "portal_url": session.portal_url,
                "reference_url": confirmation_data.get("reference_url"),
                "next_steps": confirmation_data.get("next_steps", [])
            }

            self._log_action(
                session_id,
                ActionType.WAIT,
                {
                    "action": "save_to_dashboard",
                    "confirmation_number": confirmation_data.get("confirmation_number")
                },
                True
            )

            return {
                "success": True,
                "dashboard_entry": dashboard_entry,
                "message": "Confirmation saved to dashboard"
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "save_to_dashboard"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def execute_multi_step_workflow(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute complete multi-step workflow with automatic progression.

        Requirements:
        - 12.23: End-to-end automation with minimal user intervention
        - 12.24: Automatically proceed through all steps
        - 12.25: Pause for user confirmation before submission
        - 12.29: Complete 80% of actions automatically

        Args:
            session_id: Session ID

        Returns:
            Workflow execution result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        try:
            # Start session if not already started
            if session.status == AutomationStatus.IDLE:
                self.start_session(session_id)

            # Execute workflow steps
            while session.current_step < session.total_steps:
                # Check if session is paused (OTP, CAPTCHA, biometric)
                if session.status == AutomationStatus.WAITING_FOR_USER:
                    return {
                        "success": True,
                        "status": "paused",
                        "reason": session.session_state.user_action_type,
                        "message": "Workflow paused for user action",
                        "current_step": session.current_step,
                        "total_steps": session.total_steps
                    }

                # Check for final submission page BEFORE executing the step
                detection_result = self.detect_final_submission_page(session_id)

                if detection_result.get("is_submission_page"):
                    # Request user confirmation before submission
                    confirmation_result = self.request_submission_confirmation(session_id)
                    # Add status field to match expected format
                    confirmation_result["status"] = "paused"
                    confirmation_result["reason"] = "submission_confirmation"
                    return confirmation_result

                # Execute next step
                step_result = self.proceed_to_next_step(session_id)

                if not step_result.get("success"):
                    return {
                        "success": False,
                        "status": "failed",
                        "error": "Step execution failed",
                        "step": session.current_step,
                        "details": step_result
                    }

                # Handle page transitions
                if step_result.get("action") == "navigate":
                    transition_result = self.handle_page_transition(session_id)

                    if not transition_result.get("success"):
                        return {
                            "success": False,
                            "status": "failed",
                            "error": "Page transition failed",
                            "details": transition_result
                        }

            # Workflow completed
            return {
                "success": True,
                "status": "completed",
                "message": "Multi-step workflow completed successfully",
                "total_steps": session.total_steps
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "execute_workflow"},
                False,
                str(e)
            )
            return {"success": False, "status": "failed", "error": str(e)}

    def detect_navigation_failure(
        self,
        session_id: str,
        expected_url_pattern: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Detect navigation failures during automation.

        Requirements: 12.19 - Detect navigation failures and pause automation

        Args:
            session_id: Session ID
            expected_url_pattern: Expected URL pattern after navigation
            timeout_seconds: Maximum time to wait for navigation

        Returns:
            Detection result with failure indicators
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Check if page loaded successfully (no network errors)
            # 2. Verify URL matches expected pattern
            # 3. Check for error pages (404, 500, timeout)
            # 4. Detect browser errors or crashes
            # 5. Check if page elements are accessible

            current_url = session.session_state.current_url
            navigation_failed = False
            failure_reasons = []

            # Check for error indicators in URL
            error_keywords = ["error", "404", "500", "timeout", "unavailable"]
            if any(keyword in current_url.lower() for keyword in error_keywords):
                navigation_failed = True
                failure_reasons.append("Error page detected in URL")

            # Check if URL matches expected pattern
            if expected_url_pattern and expected_url_pattern not in current_url:
                navigation_failed = True
                failure_reasons.append(f"URL does not match expected pattern: {expected_url_pattern}")

            # In production, check for:
            # - Network errors (ERR_CONNECTION_REFUSED, ERR_NAME_NOT_RESOLVED)
            # - Page load timeout
            # - JavaScript errors preventing page functionality
            # - Missing critical page elements

            if navigation_failed:
                self._log_action(
                    session_id,
                    ActionType.NAVIGATE,
                    {
                        "action": "navigation_failure_detected",
                        "current_url": current_url,
                        "expected_pattern": expected_url_pattern,
                        "failure_reasons": failure_reasons
                    },
                    False,
                    "; ".join(failure_reasons)
                )

                return {
                    "success": True,
                    "navigation_failed": True,
                    "failure_reasons": failure_reasons,
                    "current_url": current_url,
                    "expected_pattern": expected_url_pattern
                }

            return {
                "success": True,
                "navigation_failed": False,
                "current_url": current_url
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"action": "detect_navigation_failure"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def detect_unexpected_page(
        self,
        session_id: str,
        expected_page_indicators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect if current page is unexpected during automation.

        Requirements: 12.27 - Handle unexpected pages and errors gracefully

        Args:
            session_id: Session ID
            expected_page_indicators: List of expected page indicators (titles, URLs, elements)

        Returns:
            Detection result with unexpected page indicators
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        try:
            # In production, use Selenium/Playwright to:
            # 1. Check page title
            # 2. Verify expected elements are present
            # 3. Check for unexpected error messages
            # 4. Detect redirect to login page (session expired)
            # 5. Check for maintenance pages
            # 6. Detect CAPTCHA pages
            # 7. Check for access denied pages

            current_url = session.session_state.current_url
            is_unexpected = False
            unexpected_indicators = []

            # Check for common unexpected page patterns
            unexpected_patterns = [
                "login",
                "error",
                "maintenance",
                "access-denied",
                "forbidden",
                "session-expired",
                "timeout"
            ]

            for pattern in unexpected_patterns:
                if pattern in current_url.lower():
                    is_unexpected = True
                    unexpected_indicators.append(f"Unexpected page pattern: {pattern}")

            # Check if expected indicators are missing
            if expected_page_indicators:
                # In production, check if expected elements/text are present
                # For now, simulate by checking URL
                if not any(indicator in current_url for indicator in expected_page_indicators):
                    is_unexpected = True
                    unexpected_indicators.append("Expected page indicators not found")

            if is_unexpected:
                self._log_action(
                    session_id,
                    ActionType.NAVIGATE,
                    {
                        "action": "unexpected_page_detected",
                        "current_url": current_url,
                        "unexpected_indicators": unexpected_indicators
                    },
                    False,
                    "; ".join(unexpected_indicators)
                )

                return {
                    "success": True,
                    "is_unexpected": True,
                    "unexpected_indicators": unexpected_indicators,
                    "current_url": current_url
                }

            return {
                "success": True,
                "is_unexpected": False,
                "current_url": current_url
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"action": "detect_unexpected_page"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def handle_error_and_pause(
        self,
        session_id: str,
        error_type: str,
        error_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle errors by pausing automation and notifying user.

        Requirements:
        - 12.19: Pause automation on navigation failures
        - 12.27: Handle unexpected pages and errors gracefully

        Args:
            session_id: Session ID
            error_type: Type of error (navigation_failure, unexpected_page, session_timeout)
            error_details: Details about the error

        Returns:
            Error handling result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        try:
            # Pause the session
            session.status = AutomationStatus.PAUSED
            session.session_state.requires_user_action = True
            session.session_state.user_action_type = error_type

            # Generate user-friendly error message
            error_messages = {
                "navigation_failure": "Navigation failed. The page could not be loaded or an error occurred.",
                "unexpected_page": "An unexpected page was encountered. The automation may have been redirected.",
                "session_timeout": "Your session has expired. Please re-authenticate to continue.",
                "page_load_timeout": "The page took too long to load. There may be a network issue.",
                "element_not_found": "A required page element could not be found. The page structure may have changed."
            }

            user_message = error_messages.get(
                error_type,
                f"An error occurred during automation: {error_type}"
            )

            # Log the error
            self._log_action(
                session_id,
                ActionType.WAIT,
                {
                    "action": "error_handled",
                    "error_type": error_type,
                    "error_details": error_details,
                    "user_message": user_message
                },
                True
            )

            return {
                "success": True,
                "session_paused": True,
                "error_type": error_type,
                "message": user_message,
                "error_details": error_details,
                "action_required": "user_intervention",
                "recovery_options": self._get_recovery_options(error_type)
            }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "handle_error"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}

    def _get_recovery_options(self, error_type: str) -> List[Dict[str, str]]:
        """
        Get recovery options for different error types.

        Args:
            error_type: Type of error

        Returns:
            List of recovery options
        """
        recovery_options = {
            "navigation_failure": [
                {"action": "retry", "description": "Retry the navigation"},
                {"action": "skip_step", "description": "Skip this step and continue"},
                {"action": "cancel", "description": "Cancel the automation"}
            ],
            "unexpected_page": [
                {"action": "continue", "description": "Continue from current page"},
                {"action": "go_back", "description": "Go back to previous page"},
                {"action": "restart", "description": "Restart the workflow"},
                {"action": "cancel", "description": "Cancel the automation"}
            ],
            "session_timeout": [
                {"action": "re_authenticate", "description": "Re-authenticate and continue"},
                {"action": "cancel", "description": "Cancel the automation"}
            ],
            "page_load_timeout": [
                {"action": "retry", "description": "Retry loading the page"},
                {"action": "cancel", "description": "Cancel the automation"}
            ],
            "element_not_found": [
                {"action": "retry", "description": "Retry finding the element"},
                {"action": "manual_intervention", "description": "Complete this step manually"},
                {"action": "cancel", "description": "Cancel the automation"}
            ]
        }

        return recovery_options.get(error_type, [
            {"action": "retry", "description": "Retry the operation"},
            {"action": "cancel", "description": "Cancel the automation"}
        ])

    def attempt_error_recovery(
        self,
        session_id: str,
        recovery_action: str
    ) -> Dict[str, Any]:
        """
        Attempt to recover from an error based on user's chosen action.

        Requirements: 12.27 - Handle errors gracefully with recovery

        Args:
            session_id: Session ID
            recovery_action: Recovery action chosen by user

        Returns:
            Recovery result
        """
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}

        session = self.sessions[session_id]

        try:
            if recovery_action == "retry":
                # Retry the last failed action
                session.status = AutomationStatus.RUNNING
                session.session_state.requires_user_action = False

                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_retry"},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "retry",
                    "message": "Retrying the failed operation",
                    "session_resumed": True
                }

            elif recovery_action == "skip_step":
                # Skip the current step and move to next
                session.current_step += 1
                session.status = AutomationStatus.RUNNING
                session.session_state.requires_user_action = False

                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_skip_step", "skipped_step": session.current_step - 1},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "skip_step",
                    "message": "Skipped failed step, continuing with next step",
                    "session_resumed": True
                }

            elif recovery_action == "go_back":
                # Go back to previous step
                if session.current_step > 0:
                    session.current_step -= 1

                session.status = AutomationStatus.RUNNING
                session.session_state.requires_user_action = False

                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_go_back", "current_step": session.current_step},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "go_back",
                    "message": "Returned to previous step",
                    "session_resumed": True
                }

            elif recovery_action == "restart":
                # Restart the workflow from beginning
                session.current_step = 0
                session.status = AutomationStatus.RUNNING
                session.session_state.requires_user_action = False

                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_restart"},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "restart",
                    "message": "Workflow restarted from beginning",
                    "session_resumed": True
                }

            elif recovery_action == "re_authenticate":
                # Trigger re-authentication
                session.session_state.session_valid = False
                session.session_state.cookies = {}

                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_re_authenticate"},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "re_authenticate",
                    "message": "Re-authentication required",
                    "action_required": "authentication"
                }

            elif recovery_action == "continue":
                # Continue from current state
                session.status = AutomationStatus.RUNNING
                session.session_state.requires_user_action = False

                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_continue"},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "continue",
                    "message": "Continuing automation from current state",
                    "session_resumed": True
                }

            elif recovery_action == "manual_intervention":
                # Keep session paused for manual completion
                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_manual_intervention"},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "manual_intervention",
                    "message": "Please complete this step manually, then resume automation",
                    "session_paused": True
                }

            elif recovery_action == "cancel":
                # Cancel the automation
                session.status = AutomationStatus.FAILED

                self._log_action(
                    session_id,
                    ActionType.WAIT,
                    {"action": "recovery_cancel"},
                    True
                )

                return {
                    "success": True,
                    "recovery_action": "cancel",
                    "message": "Automation cancelled by user",
                    "session_cancelled": True
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown recovery action: {recovery_action}"
                }

        except Exception as e:
            self._log_action(
                session_id,
                ActionType.WAIT,
                {"action": "attempt_recovery"},
                False,
                str(e)
            )
            return {"success": False, "error": str(e)}


