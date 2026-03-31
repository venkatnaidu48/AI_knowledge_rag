"""
Production configuration and utilities for STEP 8 deployment.

Provides production-ready settings, security configurations,
and deployment utilities.
"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from functools import lru_cache


class ProductionSettings(BaseSettings):
    """Production environment settings."""
    
    # Application
    APP_NAME: str = "RAG Application"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_TIMEOUT: int = 60
    
    # Database
    DATABASE_URL: str = "postgresql://raguser:ragpassword@localhost:5432/rag_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Vector Database
    VECTOR_DB_TYPE: str = "faiss"
    VECTOR_DB_PATH: str = "/data/vectors"
    VECTOR_DB_DIMENSION: int = 1536  # OpenAI default
    
    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_SIZE: int = 1536
    EMBEDDING_CACHE_ENABLED: bool = True
    EMBEDDING_CACHE_TTL: int = 86400  # 24 hours
    
    # LLM Providers
    MISTRAL_BASE_URL: str = "http://localhost:11434"
    MISTRAL_MODEL: str = "mistral:latest"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    HF_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    # Validation
    VALIDATION_THRESHOLD: float = 0.6
    VALIDATION_FAIL_ON_CRITICAL: bool = True
    VALIDATION_AUTO_REFINE: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "/logs/app.log"
    LOG_RETENTION_DAYS: int = 30
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Security
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Caching
    CACHE_ENABLED: bool = True
    CACHE_BACKEND: str = "redis"
    CACHE_TTL: int = 3600
    REDIS_URL: str = "redis://localhost:6379/0"
    
    class Config:
        case_sensitive = True
        env_file = ".env.production"


@lru_cache()
def get_production_settings() -> ProductionSettings:
    """Get production settings singleton."""
    return ProductionSettings()


class DeploymentChecklist:
    """Pre-deployment verification checklist."""
    
    @staticmethod
    def check_database_connectivity() -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from sqlalchemy import create_engine
            from config.settings import get_settings
            
            settings = get_settings()
            engine = create_engine(settings.DATABASE_URL)
            
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
                return {
                    "status": "ok",
                    "message": "Database connection successful",
                    "database_url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "N/A"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Database connection failed: {str(e)}",
                "error": str(e)
            }
    
    @staticmethod
    def check_vector_db() -> Dict[str, Any]:
        """Check vector database availability."""
        try:
            from src.vector_db.manager import get_vector_store_manager
            
            vdb = get_vector_store_manager()
            stats = vdb.get_index_stats()
            
            return {
                "status": "ok",
                "message": "Vector DB ready",
                "type": stats.get("index_type", "FAISS"),
                "chunks": stats.get("total_chunks", 0)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Vector DB check failed: {str(e)}",
                "error": str(e)
            }
    
    @staticmethod
    def check_embedding_provider() -> Dict[str, Any]:
        """Check embedding provider availability."""
        try:
            from src.embeddings.manager import get_embedding_manager
            
            manager = get_embedding_manager()
            return {
                "status": "ok",
                "message": "Embedding provider ready",
                "provider": manager.provider.get_provider_name(),
                "model": manager.provider.get_model_name()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Embedding provider check failed: {str(e)}",
                "error": str(e)
            }
    
    @staticmethod
    def check_llm_provider() -> Dict[str, Any]:
        """Check LLM provider availability."""
        try:
            from src.generation.manager import get_generation_manager
            
            manager = get_generation_manager()
            return {
                "status": "ok",
                "message": "LLM provider ready",
                "primary": manager.primary_provider.get_provider_name() if manager.primary_provider else "None",
                "fallback": manager.fallback_provider.get_provider_name() if manager.fallback_provider else "None"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"LLM provider check failed: {str(e)}",
                "error": str(e)
            }
    
    @staticmethod
    def check_validation_pipeline() -> Dict[str, Any]:
        """Check validation pipeline."""
        try:
            from src.validation.manager import get_validation_manager
            
            manager = get_validation_manager()
            return {
                "status": "ok",
                "message": "Validation pipeline ready",
                "validators": len(manager.validators),
                "threshold": manager.config.overall_threshold
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Validation pipeline check failed: {str(e)}",
                "error": str(e)
            }
    
    @classmethod
    def run_full_check(cls) -> Dict[str, Any]:
        """Run complete deployment checklist."""
        checks = {
            "database": cls.check_database_connectivity(),
            "vector_db": cls.check_vector_db(),
            "embeddings": cls.check_embedding_provider(),
            "llm": cls.check_llm_provider(),
            "validation": cls.check_validation_pipeline(),
        }
        
        all_ok = all(check.get("status") == "ok" for check in checks.values())
        
        return {
            "deployment_ready": all_ok,
            "timestamp": str(os.popen("date").read().strip()),
            "checks": checks
        }


def print_deployment_summary(checklist_result: Dict[str, Any]) -> None:
    """Print deployment checklist summary."""
    print("\n" + "="*70)
    print("DEPLOYMENT CHECKLIST")
    print("="*70)
    
    for check_name, check_result in checklist_result.get("checks", {}).items():
        status = check_result.get("status", "?")
        message = check_result.get("message", "")
        
        status_icon = "✓" if status == "ok" else "✗"
        print(f"\n{status_icon} {check_name.upper()}")
        print(f"  {message}")
        
        if status == "ok":
            for key, value in check_result.items():
                if key not in ["status", "message"]:
                    print(f"  - {key}: {value}")
        else:
            if "error" in check_result:
                print(f"  Error: {check_result['error']}")
    
    print("\n" + "="*70)
    if checklist_result.get("deployment_ready"):
        print("✓ DEPLOYMENT READY - All checks passed")
    else:
        print("✗ DEPLOYMENT NOT READY - Some checks failed")
    print("="*70 + "\n")


# Deployment utilities

def setup_production_logging():
    """Setup production-ready logging."""
    import logging
    import logging.handlers
    from pathlib import Path
    
    settings = get_production_settings()
    
    # Ensure logs directory exists
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # File handler with rotation
    fh = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    fh.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # JSON formatter
    if settings.LOG_FORMAT == "json":
        try:
            import pythonjsonlogger.jsonlogger as jsonlogger
            formatter = jsonlogger.JsonFormatter()
        except ImportError:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger


def setup_monitoring():
    """Setup monitoring and observability."""
    settings = get_production_settings()
    
    # Sentry integration
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                traces_sample_rate=0.1,
                environment=settings.ENVIRONMENT
            )
        except ImportError:
            print("Warning: sentry-sdk not installed, skipping Sentry setup")
    
    # Prometheus metrics
    if settings.PROMETHEUS_ENABLED:
        try:
            from prometheus_client import Counter, Histogram, Gauge
            
            # Define metrics
            http_requests_total = Counter(
                'http_requests_total',
                'Total HTTP requests',
                ['method', 'endpoint', 'status']
            )
            
            http_request_duration = Histogram(
                'http_request_duration_seconds',
                'HTTP request duration',
                ['method', 'endpoint']
            )
            
            return {
                "http_requests_total": http_requests_total,
                "http_request_duration": http_request_duration
            }
        except ImportError:
            print("Warning: prometheus-client not installed, skipping Prometheus setup")
    
    return None
