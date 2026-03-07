from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.models.service import (
    ServiceGuide, ServiceCategory, ServiceStep,
    EligibilityCriterion, DocumentRequirement, ProcessingTime, ContactInfo
)

logger = logging.getLogger(__name__)


class ServiceKnowledgeBase:
    """Service knowledge base for storing and retrieving service information"""
    
    def __init__(self):
        self.services: Dict[str, ServiceGuide] = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize service data"""
        # This will be populated in task 5.2
        pass
    
    def get_service(self, service_id: str) -> Optional[ServiceGuide]:
        """Retrieve service guide by ID"""
        return self.services.get(service_id)
    
    def get_services_by_category(self, category: ServiceCategory) -> List[ServiceGuide]:
        """Get all services in a category"""
        return [
            service for service in self.services.values()
            if service.category == category
        ]
    
    def search_services(self, query: str) -> List[ServiceGuide]:
        """Search services by name or description"""
        query_lower = query.lower()
        return [
            service for service in self.services.values()
            if query_lower in service.service_name.lower() or
               query_lower in service.description.lower()
        ]
    
    def add_service(self, service: ServiceGuide) -> bool:
        """Add or update a service"""
        self.services[service.service_id] = service
        logger.info(f"Service added/updated: {service.service_id}")
        return True
    
    def get_last_updated(self, service_id: str) -> Optional[datetime]:
        """Get last update timestamp for a service"""
        service = self.get_service(service_id)
        return service.last_updated if service else None
    
    def get_all_services(self) -> List[ServiceGuide]:
        """Get all available services"""
        return list(self.services.values())


service_knowledge_base = ServiceKnowledgeBase()
