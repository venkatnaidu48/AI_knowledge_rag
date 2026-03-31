"""
API Middleware Package
Provides authentication, rate limiting, and monitoring middleware
"""

from .auth import (
    JWTHandler,
    TokenData,
    verify_bearer_token,
    get_current_user,
    require_role,
    APIKeyHandler,
    verify_api_key,
    jwt_handler,
    api_key_handler,
)

from .rate_limit import (
    RateLimiter,
    RateLimitMiddleware,
    rate_limit_by_user,
    EndpointLimiters,
    get_rate_limiter,
    general_limiter,
)

from .monitoring import (
    PrometheusMiddleware,
    track_rag_query,
    track_retrieval,
    track_db_query,
    track_cache_operation,
    set_hallucination_score,
    set_confidence_score,
    record_document_operation,
    record_chunk_generation,
    set_app_health,
    set_app_info,
    record_cache_eviction,
    # Metric objects
    http_requests_total,
    http_request_duration_seconds,
    rag_queries_total,
    rag_generation_time_seconds,
    rag_hallucination_score,
    rag_confidence_score,
    db_connections_total,
    errors_total,
    app_health,
)

__all__ = [
    # Auth
    "JWTHandler",
    "TokenData",
    "verify_bearer_token",
    "get_current_user",
    "require_role",
    "APIKeyHandler",
    "verify_api_key",
    "jwt_handler",
    "api_key_handler",
    # Rate limiting
    "RateLimiter",
    "RateLimitMiddleware",
    "rate_limit_by_user",
    "EndpointLimiters",
    "get_rate_limiter",
    "general_limiter",
    # Monitoring
    "PrometheusMiddleware",
    "track_rag_query",
    "track_retrieval",
    "track_db_query",
    "track_cache_operation",
    "set_hallucination_score",
    "set_confidence_score",
    "record_document_operation",
    "record_chunk_generation",
    "set_app_health",
    "set_app_info",
    "record_cache_eviction",
    # Metrics
    "http_requests_total",
    "http_request_duration_seconds",
    "rag_queries_total",
    "rag_generation_time_seconds",
    "rag_hallucination_score",
    "rag_confidence_score",
    "db_connections_total",
    "errors_total",
    "app_health",
]
