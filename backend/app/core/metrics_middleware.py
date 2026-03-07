"""
Metrics middleware for FastAPI to collect performance and usage metrics.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.metrics_service import get_metrics_collector


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect metrics for all requests.
    
    Collects:
    - Request duration
    - Status codes
    - Error types
    - Endpoint usage patterns
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = get_metrics_collector()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response
        """
        # Start timer
        start_time = time.time()
        
        # Extract endpoint path (remove query params and normalize)
        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method
        
        error_type = None
        status_code = 500  # Default to error
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            return response
            
        except Exception as e:
            # Capture error type
            error_type = type(e).__name__
            status_code = 500
            
            # Re-raise to be handled by FastAPI
            raise
            
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.metrics.record_request(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                error_type=error_type
            )
    
    @staticmethod
    def _normalize_endpoint(path: str) -> str:
        """
        Normalize endpoint path for metrics grouping.
        
        Replaces IDs and UUIDs with placeholders to group similar endpoints.
        
        Args:
            path: Original request path
            
        Returns:
            Normalized path
        """
        import re
        
        # Replace UUIDs with {id}
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        # Remove trailing slash
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]
        
        return path
