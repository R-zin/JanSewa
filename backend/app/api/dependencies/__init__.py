"""
API Dependencies Package

Provides reusable FastAPI dependencies for:
- Authorization and access control
- Resource ownership validation
- Permission checking
"""

from app.api.dependencies.authorization import (
    require_permission,
    get_user_document,
    get_user_service_request,
    get_user_automation_session,
    get_user_credential,
    require_read_own_documents,
    require_write_own_documents,
    require_delete_own_documents,
    require_read_own_requests,
    require_write_own_requests,
    require_start_own_automation,
    require_control_own_automation,
    require_manage_users,
    require_view_audit_logs,
)

__all__ = [
    "require_permission",
    "get_user_document",
    "get_user_service_request",
    "get_user_automation_session",
    "get_user_credential",
    "require_read_own_documents",
    "require_write_own_documents",
    "require_delete_own_documents",
    "require_read_own_requests",
    "require_write_own_requests",
    "require_start_own_automation",
    "require_control_own_automation",
    "require_manage_users",
    "require_view_audit_logs",
]
