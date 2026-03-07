"""
Conversational Agent API Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.conversational_agent import ConversationalAgent
from app.services.service_knowledge_base import ServiceKnowledgeBase
from app.services.eligibility_engine import EligibilityEngine
from app.services.document_manager import DocumentManager
from app.services.session_manager import SessionManager
from app.services.privacy_controls import PrivacyControls

router = APIRouter()

# Initialize services (in production, use dependency injection)
session_manager = SessionManager()
privacy_controls = PrivacyControls()
service_kb = ServiceKnowledgeBase()
eligibility_engine = EligibilityEngine()
document_manager = DocumentManager()
agent = ConversationalAgent()


class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str
    language: str = "en"
    request_type: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    request_type: str
    links: list
    action_items: list
    warnings: list


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process user message and return AI response
    """
    try:
        # Get or create session
        if request.session_id:
            session_id = request.session_id
        else:
            session_id = session_manager.create_session(request.user_id)
        
        # Process request
        response = await agent.process_request(
            user_id=request.user_id,
            session_id=session_id,
            message=request.message,
            language=request.language,
            request_type=request.request_type
        )
        
        return ChatResponse(
            session_id=session_id,
            response=response["response"],
            request_type=response["request_type"],
            links=response.get("links", []),
            action_items=response.get("action_items", []),
            warnings=response.get("warnings", [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services")
async def list_services(category: Optional[str] = None):
    """
    List available government services
    """
    try:
        if category:
            services = service_kb.get_services_by_category(category)
        else:
            services = service_kb.get_all_services()
        
        return {"services": services}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/{service_id}")
async def get_service(service_id: str):
    """
    Get detailed information about a service
    """
    try:
        service = service_kb.get_service(service_id)
        
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        return service
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EligibilityCheckRequest(BaseModel):
    user_id: str
    service_id: str
    user_data: dict


@router.post("/eligibility/check")
async def check_eligibility(request: EligibilityCheckRequest):
    """
    Check eligibility for a service
    """
    try:
        service = service_kb.get_service(request.service_id)
        
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        result = eligibility_engine.evaluate_eligibility(
            service.eligibility_criteria,
            request.user_data
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/requirements/{service_id}")
async def get_document_requirements(service_id: str):
    """
    Get document requirements for a service
    """
    try:
        requirements = document_manager.get_document_requirements(service_id)
        
        if not requirements:
            raise HTTPException(status_code=404, detail="Service not found")
        
        return {"requirements": requirements}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
