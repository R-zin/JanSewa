"""
Dashboard Service

Aggregates and manages dashboard data for users.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.models.dashboard import (
    DashboardData, ServiceRequestSummary, Notification, 
    DocumentWarning
)


class DashboardService:
    """
    Manages user dashboard data aggregation and display.
    """
    
    def __init__(self):
        """Initialize dashboard service"""
        self.user_dashboards: Dict[str, DashboardData] = {}
    
    def get_dashboard_data(self, user_id: str) -> DashboardData:
        """
        Get complete dashboard data for user
        
        Args:
            user_id: User ID
            
        Returns:
            Dashboard data
        """
        if user_id not in self.user_dashboards:
            # Create initial dashboard
            self.user_dashboards[user_id] = DashboardData(
                user_id=user_id,
                active_requests=[],
                recent_documents=[],
                notifications=[],
                storage_usage=StorageUsage(
                    used_bytes=0,
                    total_bytes=104857600,  # 100MB
                    percentage=0.0
                ),
                quick_links=[],
                service_history=[]
            )
        
        return self.user_dashboards[user_id]
    
    def add_service_request(
        self,
        user_id: str,
        service_id: str,
        service_name: str,
        status: str
    ) -> str:
        """
        Add a service request to dashboard
        
        Args:
            user_id: User ID
            service_id: Service ID
            service_name: Service name
            status: Request status
            
        Returns:
            Request ID
        """
        dashboard = self.get_dashboard_data(user_id)
        
        request_id = f"req_{user_id}_{service_id}_{datetime.now().timestamp()}"
        
        request = ServiceRequestSummary(
            request_id=request_id,
            service_id=service_id,
            service_name=service_name,
            status=status,
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        dashboard.active_requests.append(request)
        
        return request_id
    
    def update_service_request_status(
        self,
        user_id: str,
        request_id: str,
        status: str,
        progress: Optional[int] = None
    ) -> bool:
        """
        Update service request status
        
        Args:
            user_id: User ID
            request_id: Request ID
            status: New status
            progress: Progress percentage
            
        Returns:
            Success status
        """
        dashboard = self.get_dashboard_data(user_id)
        
        for request in dashboard.active_requests:
            if request.request_id == request_id:
                request.status = status
                request.last_updated = datetime.now()
                if progress is not None:
                    request.progress_percentage = progress
                return True
        
        return False
    
    def add_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: Optional[str] = None
    ) -> str:
        """
        Add notification to dashboard
        
        Args:
            user_id: User ID
            title: Notification title
            message: Notification message
            notification_type: Type (info, warning, error, success)
            action_url: Optional action URL
            
        Returns:
            Notification ID
        """
        dashboard = self.get_dashboard_data(user_id)
        
        notification_id = f"notif_{user_id}_{datetime.now().timestamp()}"
        
        notification = Notification(
            notification_id=notification_id,
            title=title,
            message=message,
            type=notification_type,
            timestamp=datetime.now(),
            read=False,
            action_url=action_url
        )
        
        dashboard.notifications.append(notification)
        
        return notification_id
    
    def mark_notification_read(
        self,
        user_id: str,
        notification_id: str
    ) -> bool:
        """
        Mark notification as read
        
        Args:
            user_id: User ID
            notification_id: Notification ID
            
        Returns:
            Success status
        """
        dashboard = self.get_dashboard_data(user_id)
        
        for notification in dashboard.notifications:
            if notification.notification_id == notification_id:
                notification.read = True
                return True
        
        return False
    
    def get_unread_notifications(self, user_id: str) -> List[Notification]:
        """
        Get unread notifications
        
        Args:
            user_id: User ID
            
        Returns:
            List of unread notifications
        """
        dashboard = self.get_dashboard_data(user_id)
        return [n for n in dashboard.notifications if not n.read]
    
    def update_storage_usage(
        self,
        user_id: str,
        used_bytes: int,
        total_bytes: int = 104857600
    ):
        """
        Update storage usage
        
        Args:
            user_id: User ID
            used_bytes: Bytes used
            total_bytes: Total bytes available
        """
        dashboard = self.get_dashboard_data(user_id)
        
        percentage = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0
        
        dashboard.storage_usage = StorageUsage(
            used_bytes=used_bytes,
            total_bytes=total_bytes,
            percentage=percentage
        )
        
        # Add warning if storage is high
        if percentage > 80:
            self.add_notification(
                user_id,
                "Storage Warning",
                f"You are using {percentage:.1f}% of your storage. Consider deleting old documents.",
                "warning"
            )
    
    def add_document_warning(
        self,
        user_id: str,
        document_id: str,
        document_name: str,
        warning_type: str,
        message: str
    ):
        """
        Add document warning
        
        Args:
            user_id: User ID
            document_id: Document ID
            document_name: Document name
            warning_type: Warning type (expiring, expired, invalid)
            message: Warning message
        """
        dashboard = self.get_dashboard_data(user_id)
        
        warning = DocumentWarning(
            document_id=document_id,
            document_name=document_name,
            warning_type=warning_type,
            message=message,
            timestamp=datetime.now()
        )
        
        # Also create notification
        self.add_notification(
            user_id,
            f"Document {warning_type.title()}",
            message,
            "warning",
            f"/documents/{document_id}"
        )
    
    def get_service_history(
        self,
        user_id: str,
        limit: int = 10,
        service_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get service history with filtering
        
        Args:
            user_id: User ID
            limit: Maximum records
            service_type: Filter by service type
            status: Filter by status
            
        Returns:
            Filtered service history
        """
        dashboard = self.get_dashboard_data(user_id)
        
        history = dashboard.service_history
        
        # Apply filters
        if service_type:
            history = [h for h in history if h.get("service_type") == service_type]
        
        if status:
            history = [h for h in history if h.get("status") == status]
        
        # Sort by date descending
        history = sorted(
            history,
            key=lambda x: x.get("created_at", datetime.min),
            reverse=True
        )
        
        return history[:limit]
    
    def add_quick_link(
        self,
        user_id: str,
        title: str,
        url: str,
        icon: Optional[str] = None
    ):
        """
        Add quick access link
        
        Args:
            user_id: User ID
            title: Link title
            url: Link URL
            icon: Optional icon name
        """
        dashboard = self.get_dashboard_data(user_id)
        
        quick_link = {
            "title": title,
            "url": url,
            "icon": icon
        }
        
        # Avoid duplicates
        if quick_link not in dashboard.quick_links:
            dashboard.quick_links.append(quick_link)
    
    def get_dashboard_summary(self, user_id: str) -> Dict:
        """
        Get dashboard summary statistics
        
        Args:
            user_id: User ID
            
        Returns:
            Summary statistics
        """
        dashboard = self.get_dashboard_data(user_id)
        
        return {
            "active_requests": len(dashboard.active_requests),
            "unread_notifications": len([n for n in dashboard.notifications if not n.read]),
            "total_documents": len(dashboard.recent_documents),
            "storage_percentage": dashboard.storage_usage.percentage,
            "pending_actions": len([r for r in dashboard.active_requests if r.status == "pending"])
        }
