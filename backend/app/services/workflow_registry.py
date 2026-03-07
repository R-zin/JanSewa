"""
Workflow Registry Service

Central registry for all automation workflows.
"""

from typing import Dict, List, Optional
from app.models.automation import WorkflowDefinition
from app.workflows.aadhaar_workflows import AADHAAR_WORKFLOWS
from app.workflows.identity_card_workflows import IDENTITY_CARD_WORKFLOWS
from app.workflows.certificate_workflows import CERTIFICATE_WORKFLOWS


class WorkflowRegistry:
    """
    Central registry for all automation workflows.
    """
    
    def __init__(self):
        """Initialize workflow registry"""
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """Load all workflows from modules"""
        # Load Aadhaar workflows
        for workflow_id, workflow_func in AADHAAR_WORKFLOWS.items():
            self.workflows[workflow_id] = workflow_func()
        
        # Load identity card workflows
        for workflow_id, workflow_func in IDENTITY_CARD_WORKFLOWS.items():
            self.workflows[workflow_id] = workflow_func()
        
        # Load certificate workflows
        for workflow_id, workflow_func in CERTIFICATE_WORKFLOWS.items():
            self.workflows[workflow_id] = workflow_func()
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """
        Get workflow by ID
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow definition or None
        """
        return self.workflows.get(workflow_id)
    
    def list_workflows(
        self,
        service_id: Optional[str] = None,
        portal_url: Optional[str] = None
    ) -> List[Dict]:
        """
        List available workflows with optional filtering
        
        Args:
            service_id: Filter by service ID
            portal_url: Filter by portal URL
            
        Returns:
            List of workflow summaries
        """
        workflows = list(self.workflows.values())
        
        # Apply filters
        if service_id:
            workflows = [w for w in workflows if w.service_id == service_id]
        
        if portal_url:
            workflows = [w for w in workflows if w.portal_url == portal_url]
        
        # Return summaries
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "description": w.description,
                "service_id": w.service_id,
                "portal_url": w.portal_url,
                "total_steps": len(w.steps),
                "estimated_duration_minutes": w.estimated_duration_minutes,
                "required_documents": w.required_documents
            }
            for w in workflows
        ]
    
    def get_workflow_by_service(self, service_id: str) -> Optional[WorkflowDefinition]:
        """
        Get workflow for a service
        
        Args:
            service_id: Service ID
            
        Returns:
            Workflow definition or None
        """
        for workflow in self.workflows.values():
            if workflow.service_id == service_id:
                return workflow
        
        return None
    
    def validate_workflow(self, workflow_id: str) -> Dict:
        """
        Validate workflow definition
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Validation result
        """
        workflow = self.get_workflow(workflow_id)
        
        if not workflow:
            return {
                "valid": False,
                "errors": ["Workflow not found"]
            }
        
        errors = []
        
        # Check steps
        if not workflow.steps or len(workflow.steps) == 0:
            errors.append("Workflow has no steps")
        
        # Check step numbering
        for i, step in enumerate(workflow.steps):
            if step.step_number != i + 1:
                errors.append(f"Step {i+1} has incorrect step_number: {step.step_number}")
        
        # Check form mappings
        for mapping in workflow.form_mappings:
            if mapping.required and not mapping.data_field:
                errors.append(f"Required field {mapping.form_field_id} has no data_field")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": []
        }
    
    def get_workflow_statistics(self) -> Dict:
        """
        Get statistics about registered workflows
        
        Returns:
            Statistics dictionary
        """
        total_workflows = len(self.workflows)
        
        # Count by category
        aadhaar_count = len([w for w in self.workflows.values() if 'aadhaar' in w.workflow_id])
        identity_count = len([w for w in self.workflows.values() if any(
            x in w.workflow_id for x in ['pan', 'dl', 'voter', 'passport']
        )])
        certificate_count = len([w for w in self.workflows.values() if 'certificate' in w.workflow_id])
        
        # Calculate average steps
        avg_steps = sum(len(w.steps) for w in self.workflows.values()) / total_workflows if total_workflows > 0 else 0
        
        # Calculate average duration
        avg_duration = sum(
            w.estimated_duration_minutes for w in self.workflows.values()
        ) / total_workflows if total_workflows > 0 else 0
        
        return {
            "total_workflows": total_workflows,
            "by_category": {
                "aadhaar": aadhaar_count,
                "identity_cards": identity_count,
                "certificates": certificate_count
            },
            "average_steps": round(avg_steps, 1),
            "average_duration_minutes": round(avg_duration, 1)
        }


# Global registry instance
workflow_registry = WorkflowRegistry()
