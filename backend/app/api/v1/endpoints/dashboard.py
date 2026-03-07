"""
Dashboard API Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.dashboard_service import DashboardService

router = APIRouter()

# Initialize service
dashboard_service = DashboardService()


@router.get("/{user_id}")
async def get_dashboard(user_id: str):
    """
    Get complete dashboard data for user
    """
    try:
        dashboard = dashboard_service.get_dashboard_data(user_id)
        return dashboard
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/summary")
async def get_dashboard_summary(user_id: str):
    """
    Get dashboard summary statistics
    """
    try:
        summary = dashboard_service.get_dashboard_summary(user_id)
        return summary
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/notifications")
async def get_notifications(user_id: str, unread_only: bool = False):
    """
    Get user notifications
    """
    try:
        if unread_only:
            notifications = dashboard_service.get_unread_notifications(user_id)
        else:
            dashboard = dashboard_service.get_dashboard_data(user_id)
            notifications = dashboard.notifications
        
        return {"notifications": notifications}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(user_id: str, notification_id: str):
    """
    Mark notification as read
    """
    try:
        success = dashboard_service.mark_notification_read(user_id, notification_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"message": "Notification marked as read"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/history")
async def get_service_history(
    user_id: str,
    limit: int = 10,
    service_type: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Get service history with filtering
    """
    try:
        history = dashboard_service.get_service_history(
            user_id=user_id,
            limit=limit,
            service_type=service_type,
            status=status
        )
        
        return {"history": history}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AddNotificationRequest(BaseModel):
    title: str
    message: str
    notification_type: str = "info"
    action_url: Optional[str] = None


@router.post("/{user_id}/notifications")
async def add_notification(user_id: str, request: AddNotificationRequest):
    """
    Add a notification
    """
    try:
        notification_id = dashboard_service.add_notification(
            user_id=user_id,
            title=request.title,
            message=request.message,
            notification_type=request.notification_type,
            action_url=request.action_url
        )
        
        return {
            "notification_id": notification_id,
            "message": "Notification added successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
