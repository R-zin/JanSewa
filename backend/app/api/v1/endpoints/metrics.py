"""
API endpoints for metrics and monitoring.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.metrics_service import get_metrics_collector


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    timestamp: str


class MetricsSummary(BaseModel):
    """Summary of all metrics"""
    timestamp: str
    endpoints: Dict[str, Any]
    database: Dict[str, Any]
    cache: Dict[str, Any]
    storage: Dict[str, Any]
    usage: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring tools.
    
    Returns:
        Health status
    """
    from datetime import datetime, timezone
    
    return HealthResponse(
        status="healthy",
        service="government-services-assistant",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/metrics", response_model=MetricsSummary)
async def get_metrics():
    """
    Get all metrics for monitoring.
    
    Returns comprehensive metrics including:
    - API endpoint performance
    - Error rates
    - Database performance
    - Cache hit rates
    - Storage operations
    - Privacy-preserving usage analytics
    
    Returns:
        All collected metrics
    """
    metrics = get_metrics_collector()
    return metrics.get_all_metrics()


@router.get("/metrics/endpoints")
async def get_endpoint_metrics(
    endpoint: Optional[str] = Query(None, description="Specific endpoint to get metrics for")
):
    """
    Get metrics for API endpoints.
    
    Args:
        endpoint: Optional specific endpoint path
        
    Returns:
        Endpoint performance metrics including:
        - Request counts
        - Response times (avg, p50, p95, p99)
        - Error rates
        - Requests per minute
    """
    metrics = get_metrics_collector()
    endpoint_metrics = metrics.get_endpoint_metrics(endpoint)
    
    if endpoint and not endpoint_metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for endpoint: {endpoint}")
    
    return {
        'endpoints': {k: v.__dict__ for k, v in endpoint_metrics.items()}
    }


@router.get("/metrics/database")
async def get_database_metrics():
    """
    Get database performance metrics.
    
    Returns:
        Database metrics including:
        - Total queries
        - Slow queries (>1000ms)
        - Average query time
        - Queries by table
    """
    metrics = get_metrics_collector()
    db_metrics = metrics.get_database_metrics()
    
    return {
        'database': db_metrics.__dict__
    }


@router.get("/metrics/cache")
async def get_cache_metrics():
    """
    Get cache performance metrics.
    
    Returns:
        Cache metrics including:
        - Hit/miss rates
        - Total requests
        - Average operation times
    """
    metrics = get_metrics_collector()
    cache_metrics = metrics.get_cache_metrics()
    
    return {
        'cache': cache_metrics.__dict__
    }


@router.get("/metrics/storage")
async def get_storage_metrics():
    """
    Get document storage metrics.
    
    Returns:
        Storage metrics including:
        - Upload/download counts
        - Operation times
        - Bytes transferred
        - Failed operations
    """
    metrics = get_metrics_collector()
    storage_metrics = metrics.get_storage_metrics()
    
    return {
        'storage': storage_metrics.__dict__
    }


@router.get("/metrics/usage")
async def get_usage_metrics():
    """
    Get privacy-preserving usage analytics.
    
    Returns aggregated usage metrics with NO PII:
    - Session counts
    - Service usage patterns
    - Language preferences
    - Automation usage
    - Document processing counts
    
    Returns:
        Usage analytics (privacy-preserving)
    """
    metrics = get_metrics_collector()
    usage_metrics = metrics.get_usage_metrics()
    
    return {
        'usage': usage_metrics.__dict__
    }


@router.post("/metrics/reset")
async def reset_metrics():
    """
    Reset all metrics.
    
    WARNING: This endpoint should be protected in production.
    Only use for testing or maintenance.
    
    Returns:
        Confirmation message
    """
    metrics = get_metrics_collector()
    metrics.reset_metrics()
    
    return {
        'status': 'success',
        'message': 'All metrics have been reset'
    }
