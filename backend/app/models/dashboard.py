from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ServiceRequestSummary(BaseModel):
    """Service request summary for dashboard"""
    request_id: int
    service_name: str
    status: str
    reference_number: Optional[str] = None
    created_at: datetime
    estimated_completion: Optional[datetime] = None


class DocumentWarning(BaseModel):
    """Document warning"""
    document_id: int
    document_name: str
    warning_type: str
    message: str
    expiration_date: Optional[datetime] = None


class ServiceHistoryEntry(BaseModel):
    """Service history entry"""
    service_name: str
    completion_date: datetime
    reference_number: Optional[str] = None
    status: str


class Notification(BaseModel):
    """User notification"""
    notification_id: int
    notification_type: str
    title: str
    message: str
    created_at: datetime
    read: bool = False
    action_required: bool = False


class DashboardData(BaseModel):
    """Complete dashboard data"""
    active_requests: List[ServiceRequestSummary]
    recent_documents: List[Dict]
    service_history: List[ServiceHistoryEntry]
    notifications: List[Notification]
    storage_usage: Dict[str, float]
    quick_links: List[Dict[str, str]]
    last_login: Optional[datetime] = None
    digilocker_connected: bool = False
