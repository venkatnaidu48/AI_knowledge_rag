"""
Monitoring and Metrics Middleware
Exports Prometheus metrics and tracks application performance
"""

import time
import logging
from typing import Callable, Optional, Dict, Any
from functools import wraps
import random
import string

from prometheus_client import Counter, Histogram, Gauge
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ============================================================================
# PROMETHEUS METRICS DEFINITION
# ============================================================================

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint', 'status'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
)

http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint', 'status'],
)

# RAG Pipeline metrics
rag_documents_total = Counter(
    'rag_documents_total',
    'Total documents processed',
    ['operation'],  # ingestion, deletion, update
)

rag_chunks_total = Counter(
    'rag_chunks_total',
    'Total chunks generated',
)

rag_queries_total = Counter(
    'rag_queries_total',
    'Total queries processed',
    ['status'],  # success, error, timeout
)

rag_retrieval_time_seconds = Histogram(
    'rag_retrieval_time_seconds',
    'Time to retrieve relevant documents',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

rag_generation_time_seconds = Histogram(
    'rag_generation_time_seconds',
    'Time to generate LLM response',
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
)

rag_hallucination_score = Gauge(
    'rag_hallucination_score',
    'Current hallucination rate (0-1)',
)

rag_confidence_score = Gauge(
    'rag_confidence_score',
    'Average confidence score (0-1)',
)

# Database metrics
db_connections_total = Gauge(
    'db_connections_total',
    'Number of active database connections',
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query latency in seconds',
    ['operation'],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Cache hit count',
    ['cache_type'],  # redis, memory
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Cache miss count',
    ['cache_type'],
)

cache_evictions_total = Counter(
    'cache_evictions_total',
    'Cache eviction count',
    ['cache_type'],
)

# Error metrics
errors_total = Counter(
    'errors_total',
    'Total errors by type',
    ['error_type', 'endpoint'],
)

# Health metrics
app_health = Gauge(
    'app_health',
    'Application health status (1=healthy, 0=unhealthy)',
)

app_info = Gauge(
    'app_info',
    'Application information',
    ['app_name', 'version', 'environment'],
)


# ============================================================================
# MIDDLEWARE CLASSES
# ============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for Prometheus metrics collection"""
    
    def __init__(self, app, skip_paths: Optional[list] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Record request start time
        start_time = time.time()
        
        # Get endpoint name for cleaner metrics
        endpoint = request.url.path
        method = request.method
        
        try:
            # Call the actual endpoint
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            status_code = response.status_code
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code,
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status=status_code,
            ).observe(duration)
            
            # Add metrics headers to response
            response.headers["X-Process-Time"] = str(duration)
            
            return response
        
        except Exception as e:
            # Record error
            status_code = 500
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code,
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status=status_code,
            ).observe(duration)
            
            errors_total.labels(
                error_type=type(e).__name__,
                endpoint=endpoint,
            ).inc()
            
            raise


# ============================================================================
# DECORATOR FUNCTIONS FOR SPECIFIC METRICS
# ============================================================================

def track_rag_query(func):
    """Decorator to track RAG query metrics"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            duration = time.time() - start_time
            rag_queries_total.labels(status='success').inc()
            rag_generation_time_seconds.observe(duration)
            
            # If result has confidence, record it
            if isinstance(result, dict) and 'confidence' in result:
                rag_confidence_score.set(result['confidence'])
            
            return result
        
        except Exception as e:
            rag_queries_total.labels(status='error').inc()
            logger.error(f"RAG query error: {str(e)}")
            raise
    
    return wrapper


def track_retrieval(func):
    """Decorator to track document retrieval metrics"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        
        rag_retrieval_time_seconds.observe(duration)
        
        return result
    
    return wrapper


def track_db_query(operation: str):
    """Decorator to track database query metrics"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                db_query_duration_seconds.labels(operation=operation).observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                db_query_duration_seconds.labels(operation=operation).observe(duration)
                raise
        
        return wrapper
    
    return decorator


def track_cache_operation(cache_type: str):
    """Decorator to track cache operations"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(hit: bool = False, *args, **kwargs):
            if hit:
                cache_hits_total.labels(cache_type=cache_type).inc()
            else:
                cache_misses_total.labels(cache_type=cache_type).inc()
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def set_hallucination_score(score: float):
    """Update hallucination score metric"""
    if 0 <= score <= 1:
        rag_hallucination_score.set(score)
    else:
        logger.warning(f"Invalid hallucination score: {score}")


def set_confidence_score(score: float):
    """Update confidence score metric"""
    if 0 <= score <= 1:
        rag_confidence_score.set(score)
    else:
        logger.warning(f"Invalid confidence score: {score}")


def record_document_operation(operation: str, count: int = 1):
    """Record document operation"""
    rag_documents_total.labels(operation=operation).inc(count)


def record_chunk_generation(count: int = 1):
    """Record chunk generation"""
    rag_chunks_total.inc(count)


def set_app_health(healthy: bool):
    """Set application health status"""
    app_health.set(1 if healthy else 0)


def set_app_info(app_name: str, version: str, environment: str):
    """Set application info"""
    app_info.labels(
        app_name=app_name,
        version=version,
        environment=environment,
    ).set(1)


def record_cache_eviction(cache_type: str):
    """Record cache eviction"""
    cache_evictions_total.labels(cache_type=cache_type).inc()
