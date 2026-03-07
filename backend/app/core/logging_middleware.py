"""
Logging middleware for FastAPI to add request context to logs.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context to logs and log all requests.
    
    Adds:
    - Request ID to all logs during request processing
    - Request/response logging with duration
    - Error logging for failed requests
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add logging context.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state for access in handlers
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Get user ID if available (from auth token)
        user_id = getattr(request.state, 'user_id', None)
        
        # Create context logger
        context_logger = get_logger(
            __name__,
            request_id=request_id,
            user_id=user_id
        )
        
        # Log request
        context_logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'operation': 'http_request',
                'extra_data': {
                    'method': request.method,
                    'path': request.url.path,
                    'query_params': dict(request.query_params),
                    'client_host': request.client.host if request.client else None,
                }
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log response
            context_logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    'operation': 'http_response',
                    'duration_ms': duration_ms,
                    'extra_data': {
                        'status_code': response.status_code,
                        'method': request.method,
                        'path': request.url.path,
                    }
                }
            )
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            context_logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                exc_info=True,
                extra={
                    'operation': 'http_error',
                    'duration_ms': duration_ms,
                    'extra_data': {
                        'method': request.method,
                        'path': request.url.path,
                        'error_type': type(e).__name__,
                    }
                }
            )
            
            # Re-raise exception to be handled by FastAPI
            raise


def get_request_logger(request: Request) -> logging.Logger:
    """
    Get a logger with request context.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Logger with request context (request_id, user_id)
    """
    request_id = getattr(request.state, 'request_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    context = {}
    if request_id:
        context['request_id'] = request_id
    if user_id:
        context['user_id'] = user_id
    
    return get_logger('api', **context)
