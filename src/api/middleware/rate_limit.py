"""
Rate Limiting Middleware
Implements request rate limiting using sliding window or token bucket algorithm
"""

import time
from typing import Dict, Tuple
from functools import wraps
from collections import defaultdict, deque
import logging

from fastapi import HTTPException, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


class RateLimiter:
    """Implements sliding window rate limiting"""
    
    def __init__(self, requests: int, period: int):
        """
        Args:
            requests: Number of requests allowed
            period: Time period in seconds
        """
        self.requests = requests
        self.period = period
        self.clients: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if client is allowed to make request
        
        Args:
            client_id: Unique identifier for client
            
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        requests_deque = self.clients[client_id]
        
        # Remove old requests outside the time window
        while requests_deque and requests_deque[0] < now - self.period:
            requests_deque.popleft()
        
        # Check if limit exceeded
        if len(requests_deque) >= self.requests:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False
        
        # Add current request
        requests_deque.append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client"""
        requests_deque = self.clients[client_id]
        return max(0, self.requests - len(requests_deque))


# Global rate limiter instances
general_limiter = Limiter(key_func=get_remote_address)


class RateLimitMiddleware:
    """ASGI middleware for rate limiting"""
    
    def __init__(self, app, requests: int = 100, period: int = 60, exclude_paths: list = None):
        """
        Args:
            app: ASGI application
            requests: Max requests per period
            period: Time period in seconds
            exclude_paths: Paths to exclude from rate limiting
        """
        self.app = app
        self.limiter = RateLimiter(requests, period)
        self.exclude_paths = exclude_paths or ["/health", "/api/health", "/docs"]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get request path
        path = scope.get("path", "")
        
        # Skip rate limiting for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Get client IP
        client_host = scope.get("client", ["unknown"])[0]
        
        # Check rate limit
        if not self.limiter.is_allowed(client_host):
            # Send 429 Too Many Requests
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"retry-after", b"60"],
                ],
            })
            
            error_response = b'{"detail": "Rate limit exceeded. Too many requests."}'
            await send({
                "type": "http.response.body",
                "body": error_response,
            })
            return
        
        # Add rate limit headers to response
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                
                remaining = self.limiter.get_remaining(client_host)
                headers.append((b"x-ratelimit-limit", str(self.limiter.requests).encode()))
                headers.append((b"x-ratelimit-remaining", str(remaining).encode()))
                headers.append((b"x-ratelimit-reset", str(int(time.time()) + self.limiter.period).encode()))
                
                message["headers"] = headers
            
            await send(message)
        
        await self.app(scope, receive, send_with_headers)


def rate_limit_by_user(requests: int = 100, period: int = 3600):
    """
    Decorator for per-user rate limiting
    
    Args:
        requests: Max requests per period
        period: Time period in seconds
    """
    limiter = RateLimiter(requests, period)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            if not request:
                return await func(*args, **kwargs)
            
            # Get user ID from request (assuming it's in token)
            user_id = getattr(request.state, "user_id", None)
            
            if not user_id:
                user_id = request.client.host if request.client else "anonymous"
            
            if not limiter.is_allowed(user_id):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Limiter configuration for specific endpoints
class EndpointLimiters:
    """Manages rate limits for specific endpoints"""
    
    # General API endpoints
    search_limiter = RateLimiter(requests=100, period=60)  # 100 req/min
    
    # Query endpoints
    query_limiter = RateLimiter(requests=50, period=60)   # 50 req/min
    
    # Document operations
    document_limiter = RateLimiter(requests=20, period=60)  # 20 req/min
    
    # Admin endpoints
    admin_limiter = RateLimiter(requests=10, period=60)   # 10 req/min


def get_rate_limiter(endpoint_type: str = "general") -> RateLimiter:
    """Get appropriate rate limiter for endpoint type"""
    limiters = {
        "search": EndpointLimiters.search_limiter,
        "query": EndpointLimiters.query_limiter,
        "document": EndpointLimiters.document_limiter,
        "admin": EndpointLimiters.admin_limiter,
    }
    
    return limiters.get(endpoint_type, EndpointLimiters.search_limiter)
