"""
DigiLocker Retry Logic

Implements exponential backoff and retry strategies for DigiLocker API calls.
"""

import asyncio
import time
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
import logging

from .digilocker_errors import (
    DigiLockerError,
    RateLimitError,
    ServiceUnavailableError,
    AuthenticationError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class RetryStrategy:
    """Implements retry logic with exponential backoff"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry strategy
        
        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """
        Calculate delay for next retry attempt
        
        Args:
            attempt: Current attempt number (0-indexed)
            retry_after: Explicit retry-after value from server
            
        Returns:
            Delay in seconds
        """
        # If server specifies retry-after, use that
        if retry_after is not None:
            return float(retry_after)
        
        # Calculate exponential backoff
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return delay
    
    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            DigiLockerError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.config.max_attempts):
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Log success if this was a retry
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}")
                
                return result
                
            except RateLimitError as e:
                last_error = e
                
                # For rate limits, always respect retry_after
                delay = self.calculate_delay(attempt, e.retry_after)
                
                logger.warning(
                    f"Rate limit exceeded. Retrying after {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self.config.max_attempts})"
                )
                
                # If this is the last attempt, don't wait
                if attempt < self.config.max_attempts - 1:
                    await asyncio.sleep(delay)
                
            except ServiceUnavailableError as e:
                last_error = e
                
                # For service unavailable, use exponential backoff
                delay = self.calculate_delay(attempt)
                
                logger.warning(
                    f"Service unavailable. Retrying after {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self.config.max_attempts})"
                )
                
                # If this is the last attempt, don't wait
                if attempt < self.config.max_attempts - 1:
                    await asyncio.sleep(delay)
                
            except AuthenticationError as e:
                # Don't retry authentication errors
                logger.error(f"Authentication failed: {e.message}")
                raise
                
            except DigiLockerError as e:
                # For other DigiLocker errors, retry with backoff
                last_error = e
                
                delay = self.calculate_delay(attempt)
                
                logger.warning(
                    f"DigiLocker error: {e.message}. Retrying after {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self.config.max_attempts})"
                )
                
                # If this is the last attempt, don't wait
                if attempt < self.config.max_attempts - 1:
                    await asyncio.sleep(delay)
        
        # All retries failed
        logger.error(f"All {self.config.max_attempts} retry attempts failed")
        raise last_error


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to async functions
    
    Args:
        config: Retry configuration
        
    Returns:
        Decorated function
    """
    strategy = RetryStrategy(config)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await strategy.execute_with_retry(func, *args, **kwargs)
        return wrapper
    
    return decorator


class RateLimiter:
    """Simple rate limiter to prevent exceeding API limits"""
    
    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: list[float] = []
    
    async def acquire(self):
        """
        Acquire permission to make a request
        
        Blocks if rate limit would be exceeded
        """
        now = time.time()
        
        # Remove old requests outside time window
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]
        
        # Check if we're at the limit
        if len(self.requests) >= self.max_requests:
            # Calculate how long to wait
            oldest_request = self.requests[0]
            wait_time = self.time_window - (now - oldest_request)
            
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                
                # Recursively try again
                return await self.acquire()
        
        # Record this request
        self.requests.append(now)
