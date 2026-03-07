from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class RequestType(str, Enum):
    """Request type enumeration"""
    SERVICE_GUIDANCE = "service_guidance"
    ELIGIBILITY_CHECK = "eligibility_check"
    DOCUMENT_INQUIRY = "document_inquiry"
    STATUS_TRACKING = "status_tracking"
    CLARIFICATION = "clarification"


class ResponseType(str, Enum):
    """Response type enumeration"""
    SERVICE_GUIDE = "service_guide"
    ELIGIBILITY_RESULT = "eligibility_result"
    DOCUMENT_LIST = "document_list"
    STATUS_INFO = "status_info"
    CLARIFICATION_QUESTION = "clarification_question"
    ERROR = "error"


class ActionItem(BaseModel):
    """Action item for user"""
    action_type: str
    description: str
    deadline: Optional[datetime] = None


class PortalLink(BaseModel):
    """Portal link information"""
    url: str
    description: str
    portal_name: str


class SecurityWarning(BaseModel):
    """Security warning"""
    warning_type: str
    message: str
    severity: str


class UserRequest(BaseModel):
    """User request model"""
    message: str
    language: str = "en"
    request_type: RequestType
    context: Dict[str, Any] = {}


class AgentResponse(BaseModel):
    """Agent response model"""
    message: str
    language: str
    response_type: ResponseType
    action_items: List[ActionItem] = []
    links: List[PortalLink] = []
    follow_up_questions: List[str] = []
    warnings: List[SecurityWarning] = []


class ConversationTurn(BaseModel):
    """Single conversation turn"""
    timestamp: datetime
    user_message: str
    agent_response: str
    request_type: RequestType


class Session(BaseModel):
    """Session model"""
    session_id: str
    start_time: datetime
    language: str
    conversation_history: List[ConversationTurn] = []
    temporary_context: Dict[str, Any] = {}


class UserProfile(BaseModel):
    """User profile model"""
    user_id: int
    email: str
    full_name: Optional[str] = None
    language_preference: str = "en"
    created_at: datetime


class UserPreferences(BaseModel):
    """User preferences"""
    language: str = "en"
    voice_input_enabled: bool = False
    auto_sync_digilocker: bool = False
    sync_frequency: str = "manual"
