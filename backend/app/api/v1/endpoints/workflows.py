"""
Workflow API Endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.workflow_registry import workflow_registry

router = APIRouter()


@router.get("/")
async def list_workflows(
    service_id: Optional[str] = None,
    portal_url: Optional[str] = None
):
    """
    List available workflows
    """
    try:
        workflows = workflow_registry.list_workflows(service_id, portal_url)
        return {"workflows": workflows}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """
    Get workflow definition
    """
    try:
        workflow = workflow_registry.get_workflow(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return workflow
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}/validate")
async def validate_workflow(workflow_id: str):
    """
    Validate workflow definition
    """
    try:
        result = workflow_registry.validate_workflow(workflow_id)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/service/{service_id}")
async def get_workflow_by_service(service_id: str):
    """
    Get workflow for a service
    """
    try:
        workflow = workflow_registry.get_workflow_by_service(service_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="No workflow found for service")
        
        return workflow
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_workflow_statistics():
    """
    Get workflow statistics
    """
    try:
        stats = workflow_registry.get_workflow_statistics()
        return stats
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
