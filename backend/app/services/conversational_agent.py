import google.generativeai as genai
from typing import Dict, Any, Optional
import logging

from app.core.config import settings
from app.models.session import UserRequest, AgentResponse, ResponseType, Session
from app.services.service_knowledge_base import service_knowledge_base
from app.services.eligibility_engine import eligibility_engine
from app.services.document_manager import document_manager

logger = logging.getLogger(__name__)

# Configure Google AI
genai.configure(api_key=settings.GOOGLE_API_KEY)


class ConversationalAgent:
    """AI-powered conversational agent using Google Gemini"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def process_request(
        self,
        request: UserRequest,
        session: Session
    ) -> AgentResponse:
        """Process user request and generate response"""
        
        # Route based on request type
        if request.request_type == "service_guidance":
            return await self.provide_service_guidance(request, session)
        elif request.request_type == "eligibility_check":
            return await self.assess_eligibility(request, session)
        elif request.request_type == "document_inquiry":
            return await self.handle_document_inquiry(request, session)
        elif request.request_type == "status_tracking":
            return await self.guide_status_tracking(request, session)
        else:
            return await self.handle_clarification(request, session)
    
    async def provide_service_guidance(
        self,
        request: UserRequest,
        session: Session
    ) -> AgentResponse:
        """Provide service guidance"""
        # Extract service intent from message using AI
        prompt = f"""
        User message: {request.message}
        
        Identify which government service the user is asking about.
        Respond with just the service category: aadhaar, certificate, identity_card, or data_access
        """
        
        try:
            response = self.model.generate_content(prompt)
            service_category = response.text.strip().lower()
            
            # Get relevant services
            services = service_knowledge_base.get_all_services()
            
            if services:
                service = services[0]  # Simplified - would use better matching
                
                # Generate response using AI
                guidance_prompt = f"""
                Provide step-by-step guidance for: {service.service_name}
                
                Service details:
                - Description: {service.description}
                - Steps: {len(service.steps)} steps
                - Portal: {service.official_portal_url}
                
                Generate a helpful, conversational response in {request.language}.
                """
                
                ai_response = self.model.generate_content(guidance_prompt)
                
                return AgentResponse(
                    message=ai_response.text,
                    language=request.language,
                    response_type=ResponseType.SERVICE_GUIDE,
                    links=[{
                        "url": service.official_portal_url,
                        "description": f"Official portal for {service.service_name}",
                        "portal_name": service.service_name
                    }]
                )
        except Exception as e:
            logger.error(f"Error in service guidance: {e}")
            return AgentResponse(
                message="I apologize, I'm having trouble processing your request. Please try again.",
                language=request.language,
                response_type=ResponseType.ERROR
            )
    
    async def assess_eligibility(
        self,
        request: UserRequest,
        session: Session
    ) -> AgentResponse:
        """Assess user eligibility for a service"""
        # Simplified implementation
        return AgentResponse(
            message="Let me check your eligibility for this service.",
            language=request.language,
            response_type=ResponseType.ELIGIBILITY_RESULT
        )
    
    async def handle_document_inquiry(
        self,
        request: UserRequest,
        session: Session
    ) -> AgentResponse:
        """Handle document requirement inquiries"""
        return AgentResponse(
            message="Here are the documents you'll need for this service.",
            language=request.language,
            response_type=ResponseType.DOCUMENT_LIST
        )
    
    async def guide_status_tracking(
        self,
        request: UserRequest,
        session: Session
    ) -> AgentResponse:
        """Guide user on tracking service status"""
        return AgentResponse(
            message="You can track your service status using your reference number.",
            language=request.language,
            response_type=ResponseType.STATUS_INFO
        )
    
    async def handle_clarification(
        self,
        request: UserRequest,
        session: Session
    ) -> AgentResponse:
        """Handle clarification requests"""
        return AgentResponse(
            message="Could you please provide more details?",
            language=request.language,
            response_type=ResponseType.CLARIFICATION_QUESTION
        )


conversational_agent = ConversationalAgent()
