"""
Browser Automation API Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.services.browser_automation import BrowserAutomationAgent
from app.services.credential_store import CredentialStore
from app.services.captcha_handler import CAPTCHAHandler
from app.services.encryption_service import EncryptionService
from app.models.automation import WorkflowDefinition

router = APIRouter()

# Initialize services
encryption_service = EncryptionService()
credential_store = CredentialStore(encryption_service)
automation_agent = BrowserAutomationAgent()
captcha_handler = CAPTCHAHandler()


class StartAutomationRequest(BaseModel):
    user_id: str
    service_id: str
    portal_url: str
    workflow: WorkflowDefinition


@router.post("/start")
async def start_automation(request: StartAutomationRequest):
    """
    Start a browser automation session
    """
    try:
        # Create session
        session_id = automation_agent.create_session(
            user_id=request.user_id,
            service_id=request.service_id,
            portal_url=request.portal_url,
            workflow=request.workflow
        )
        
        # Start automation
        success = automation_agent.start_session(session_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start automation")
        
        return {
            "session_id": session_id,
            "status": "started",
            "message": "Automation session started successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pause")
async def pause_automation(session_id: str, reason: str = ""):
    """
    Pause automation session
    """
    try:
        success = automation_agent.pause_session(session_id, reason)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Automation paused"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/resume")
async def resume_automation(session_id: str):
    """
    Resume paused automation session
    """
    try:
        success = automation_agent.resume_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or not paused")
        
        return {"message": "Automation resumed"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/status")
async def get_automation_status(session_id: str):
    """
    Get automation session status
    """
    try:
        status = automation_agent.get_session_state(session_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/logs")
async def get_automation_logs(session_id: str, limit: int = 50):
    """
    Get automation action logs
    """
    try:
        logs = automation_agent.get_action_logs(session_id, limit)
        return {"logs": logs}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UserInputRequest(BaseModel):
    input_value: str


@router.post("/{session_id}/input")
async def provide_user_input(session_id: str, request: UserInputRequest):
    """
    Provide user input to waiting automation
    """
    try:
        success = automation_agent.provide_user_input(
            session_id,
            request.input_value
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to provide input")
        
        return {"message": "Input provided, automation resumed"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/captcha/{captcha_id}/status")
async def get_captcha_status(captcha_id: str):
    """
    Get CAPTCHA status
    """
    try:
        status = captcha_handler.get_captcha_status(captcha_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="CAPTCHA session not found")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/captcha/{captcha_id}/complete")
async def mark_captcha_complete(captcha_id: str):
    """
    Mark CAPTCHA as completed
    """
    try:
        success = captcha_handler.mark_completed(captcha_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="CAPTCHA session not found")
        
        return {"message": "CAPTCHA marked as completed"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class StoreCredentialRequest(BaseModel):
    user_id: str
    portal_name: str
    portal_url: str
    username: str
    password: Optional[str] = None
    auth_methods: Optional[List[str]] = None
    mobile_number: Optional[str] = None


@router.post("/credentials")
async def store_credential(request: StoreCredentialRequest):
    """
    Store portal credentials
    """
    try:
        credential_id = credential_store.store_credential(
            user_id=request.user_id,
            portal_name=request.portal_name,
            portal_url=request.portal_url,
            username=request.username,
            password=request.password,
            auth_methods=request.auth_methods,
            mobile_number=request.mobile_number
        )
        
        return {
            "credential_id": credential_id,
            "message": "Credentials stored successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials")
async def list_credentials(user_id: str):
    """
    List user's stored credentials
    """
    try:
        credentials = credential_store.list_credentials(user_id)
        return {"credentials": credentials}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/credentials/{credential_id}")
async def delete_credential(credential_id: str):
    """
    Delete stored credential
    """
    try:
        success = credential_store.delete_credential(credential_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        return {"message": "Credential deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
