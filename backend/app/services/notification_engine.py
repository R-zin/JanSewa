"""
Notification Engine Service

Generates and manages notifications for various events.
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class NotificationType(str, Enum):
    """Notification types"""
    STATUS_CHANGE = "status_change"
    PENDING_ACTION = "pending_action"
    DOCUMENT_EXPIRING = "document_expiring"
    DOCUMENT_EXPIRED = "document_expired"
    STORAGE_WARNING = "storage_warning"
    AUTOMATION_COMPLETE = "automation_complete"
    AUTOMATION_PAUSED = "automation_paused"
    DIGILOCKER_SYNC = "digilocker_sync"
    OCR_COMPLETE = "ocr_complete"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationTemplate(BaseModel):
    """Template for notification generation"""
    notification_type: NotificationType
    title_template: str
    message_template: str
    priority: NotificationPriority
    action_url_template: Optional[str] = None


class NotificationEngine:
    """
    Generates notifications for various system events.
    """
    
    def __init__(self):
        """Initialize notification engine"""
        self._init_templates()
    
    def _init_templates(self):
        """Initialize notification templates"""
        self.templates = {
            NotificationType.STATUS_CHANGE: NotificationTemplate(
                notification_type=NotificationType.STATUS_CHANGE,
                title_template="Service Request Status Updated",
                message_template="Your {service_name} request is now {status}",
                priority=NotificationPriority.MEDIUM,
                action_url_template="/requests/{request_id}"
            ),
            NotificationType.PENDING_ACTION: NotificationTemplate(
                notification_type=NotificationType.PENDING_ACTION,
                title_template="Action Required",
                message_template="Your {service_name} request requires your attention: {action}",
                priority=NotificationPriority.HIGH,
                action_url_template="/requests/{request_id}"
            ),
            NotificationType.DOCUMENT_EXPIRING: NotificationTemplate(
                notification_type=NotificationType.DOCUMENT_EXPIRING,
                title_template="Document Expiring Soon",
                message_template="Your {document_name} will expire on {expiry_date}",
                priority=NotificationPriority.MEDIUM,
                action_url_template="/documents/{document_id}"
            ),
            NotificationType.DOCUMENT_EXPIRED: NotificationTemplate(
                notification_type=NotificationType.DOCUMENT_EXPIRED,
                title_template="Document Expired",
                message_template="Your {document_name} has expired. Please renew it.",
                priority=NotificationPriority.HIGH,
                action_url_template="/documents/{document_id}"
            ),
            NotificationType.STORAGE_WARNING: NotificationTemplate(
                notification_type=NotificationType.STORAGE_WARNING,
                title_template="Storage Limit Warning",
                message_template="You are using {percentage}% of your storage. Consider deleting old documents.",
                priority=NotificationPriority.MEDIUM,
                action_url_template="/documents"
            ),
            NotificationType.AUTOMATION_COMPLETE: NotificationTemplate(
                notification_type=NotificationType.AUTOMATION_COMPLETE,
                title_template="Automation Completed",
                message_template="Your {service_name} automation has completed successfully",
                priority=NotificationPriority.MEDIUM,
                action_url_template="/automation/{session_id}"
            ),
            NotificationType.AUTOMATION_PAUSED: NotificationTemplate(
                notification_type=NotificationType.AUTOMATION_PAUSED,
                title_template="Automation Paused",
                message_template="Your automation is paused: {reason}",
                priority=NotificationPriority.HIGH,
                action_url_template="/automation/{session_id}"
            ),
            NotificationType.DIGILOCKER_SYNC: NotificationTemplate(
                notification_type=NotificationType.DIGILOCKER_SYNC,
                title_template="DigiLocker Sync Complete",
                message_template="Synced {count} documents from DigiLocker",
                priority=NotificationPriority.LOW,
                action_url_template="/digilocker"
            ),
            NotificationType.OCR_COMPLETE: NotificationTemplate(
                notification_type=NotificationType.OCR_COMPLETE,
                title_template="Document Processing Complete",
                message_template="Text extraction completed for {document_name}",
                priority=NotificationPriority.LOW,
                action_url_template="/documents/{document_id}"
            )
        }
    
    def generate_notification(
        self,
        notification_type: NotificationType,
        context: Dict
    ) -> Dict:
        """
        Generate notification from template
        
        Args:
            notification_type: Type of notification
            context: Context data for template
            
        Returns:
            Notification data
        """
        if notification_type not in self.templates:
            raise ValueError(f"Unknown notification type: {notification_type}")
        
        template = self.templates[notification_type]
        
        # Format title and message
        title = template.title_template.format(**context)
        message = template.message_template.format(**context)
        
        # Format action URL if template exists
        action_url = None
        if template.action_url_template:
            try:
                action_url = template.action_url_template.format(**context)
            except KeyError:
                pass
        
        return {
            "title": title,
            "message": message,
            "type": self._get_notification_display_type(template.priority),
            "priority": template.priority,
            "action_url": action_url,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_notification_display_type(self, priority: NotificationPriority) -> str:
        """Map priority to display type"""
        mapping = {
            NotificationPriority.LOW: "info",
            NotificationPriority.MEDIUM: "info",
            NotificationPriority.HIGH: "warning",
            NotificationPriority.URGENT: "error"
        }
        return mapping.get(priority, "info")
    
    def generate_status_change_notification(
        self,
        service_name: str,
        status: str,
        request_id: str
    ) -> Dict:
        """Generate notification for status change"""
        return self.generate_notification(
            NotificationType.STATUS_CHANGE,
            {
                "service_name": service_name,
                "status": status,
                "request_id": request_id
            }
        )
    
    def generate_pending_action_notification(
        self,
        service_name: str,
        action: str,
        request_id: str
    ) -> Dict:
        """Generate notification for pending action"""
        return self.generate_notification(
            NotificationType.PENDING_ACTION,
            {
                "service_name": service_name,
                "action": action,
                "request_id": request_id
            }
        )
    
    def generate_document_expiry_notification(
        self,
        document_name: str,
        expiry_date: str,
        document_id: str,
        is_expired: bool = False
    ) -> Dict:
        """Generate notification for document expiry"""
        notification_type = (
            NotificationType.DOCUMENT_EXPIRED if is_expired
            else NotificationType.DOCUMENT_EXPIRING
        )
        
        return self.generate_notification(
            notification_type,
            {
                "document_name": document_name,
                "expiry_date": expiry_date,
                "document_id": document_id
            }
        )
    
    def generate_storage_warning_notification(
        self,
        percentage: float
    ) -> Dict:
        """Generate notification for storage warning"""
        return self.generate_notification(
            NotificationType.STORAGE_WARNING,
            {"percentage": f"{percentage:.1f}"}
        )
    
    def check_document_expiry(
        self,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Check documents for expiry and generate notifications
        
        Args:
            documents: List of documents with expiry dates
            
        Returns:
            List of notifications
        """
        notifications = []
        now = datetime.now()
        
        for doc in documents:
            if not doc.get("expiry_date"):
                continue
            
            expiry_date = datetime.fromisoformat(doc["expiry_date"])
            days_until_expiry = (expiry_date - now).days
            
            # Expired
            if days_until_expiry < 0:
                notif = self.generate_document_expiry_notification(
                    document_name=doc["name"],
                    expiry_date=expiry_date.strftime("%Y-%m-%d"),
                    document_id=doc["document_id"],
                    is_expired=True
                )
                notifications.append(notif)
            
            # Expiring within 30 days
            elif days_until_expiry <= 30:
                notif = self.generate_document_expiry_notification(
                    document_name=doc["name"],
                    expiry_date=expiry_date.strftime("%Y-%m-%d"),
                    document_id=doc["document_id"],
                    is_expired=False
                )
                notifications.append(notif)
        
        return notifications
