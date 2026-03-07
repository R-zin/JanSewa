from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class NavigationActionType(str, Enum):
    """Navigation action types"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    UPLOAD = "upload"
    WAIT = "wait"
    SUBMIT = "submit"


class AutomationStatus(str, Enum):
    """Automation session status"""
    INITIALIZING = "initializing"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    WAITING_OTP = "waiting_otp"
    WAITING_CAPTCHA = "waiting_captcha"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FormField(BaseModel):
    """Form field specification"""
    field_id: str
    field_name: str
    field_type: str
    label: str
    required: bool
    value: Optional[Any] = None
    validation_pattern: Optional[str] = None


class NavigationAction(BaseModel):
    """Browser navigation action"""
    action_id: str
    action_type: NavigationActionType
    timestamp: datetime
    target: str
    value: Optional[Any] = None
    success: bool
    error_message: Optional[str] = None


class SessionState(BaseModel):
    """Automation session state"""
    current_url: str
    current_step: int
    total_steps: int
    form_fields_filled: int
    total_form_fields: int
    is_authenticated: bool
    requires_user_action: bool
    user_action_type: Optional[str] = None
    form_data: Dict[str, Any] = {}
    cookies: Dict[str, str] = {}
    session_valid: bool = True
    confirmation_data: Optional[Dict[str, Any]] = None


class ActionLogEntry(BaseModel):
    """Action log entry"""
    timestamp: datetime
    action_type: NavigationActionType
    description: str
    success: bool
    details: Dict[str, Any] = {}


class WorkflowDefinition(BaseModel):
    """Workflow definition for a service"""
    service_id: str
    workflow_name: str
    steps: List[Dict[str, Any]]
    field_mappings: Dict[str, str]
    portal_url: str
    auth_required: bool


class FieldMapping(BaseModel):
    """Mapping between data fields and form fields"""
    data_field: str
    form_field_selector: str
    transformation: Optional[str] = None


class AutomationSessionModel(BaseModel):
    """Automation session model"""
    session_id: str
    user_id: int
    service_id: str
    status: AutomationStatus
    session_state: SessionState
    action_log: List[ActionLogEntry] = []
    created_at: datetime
    completed_at: Optional[datetime] = None
