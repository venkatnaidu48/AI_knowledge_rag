"""
Configuration settings for RAG Application
Loads from environment variables with sensible defaults
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from typing import Optional


class Settings(BaseSettings):
    """Application Settings"""
    
    # ============ Basic Settings ============
    APP_NAME: str = "RAG-Knowledge-Worker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # ============ API Settings ============
    API_TITLE: str = "RAG Query API"
    API_DESCRIPTION: str = "Enterprise RAG System for Company Document Q&A"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_LOG_LEVEL: str = "info"
    
    # ============ Database Settings ============
    DATABASE_URL: str = f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rag_dev.db')}"
    # PostgreSQL alternative: "postgresql://postgres:password@localhost:5432/rag_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # ============ Redis Settings ============
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL: int = 3600
    REDIS_MAX_CONNECTIONS: int = 50
    
    # ============ OpenAI Settings ============
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT: int = 30
    
    # ============ Mistral Settings (Ollama Local) ============
    MISTRAL_BASE_URL: str = "http://localhost:11434/v1"
    MISTRAL_MODEL: str = "mistral"
    
    # ============ Anthropic Settings ============
    ANTHROPIC_API_KEY: str = ""
    
    # ============ LLM Configuration ============
    LLM_PROVIDER: str = "mistral"  # mistral, openai, or anthropic
    PRIMARY_LLM_MODEL: str = "mistral"
    FALLBACK_LLM_MODEL: str = "mistral"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # LLM Parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000
    LLM_TOP_P: float = 0.95
    
    # ============ Vector Database Settings ============
    FAISS_INDEX_PATH: str = "./data/vector_index/faiss.index"
    FAISS_METADATA_PATH: str = "./data/vector_index/faiss_metadata.pkl"
    FAISS_BACKUP_PATH: str = "./backups/"
    VECTOR_DIMENSION: int = 1536
    
    # ============ Document Processing Settings ============
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 100
    MIN_CHUNK_SIZE: int = 100
    MAX_CHUNK_SIZE: int = 800
    CHUNK_QUALITY_THRESHOLD: float = 0.5
    
    # File upload settings
    MAX_UPLOAD_SIZE_MB: int = 100
    UPLOAD_DIR: str = "./data/uploads/"
    
    # ============ Query Settings ============
    QUERY_TOP_K: int = 5
    QUERY_MIN_LENGTH: int = 3
    QUERY_MAX_LENGTH: int = 1000
    QUERY_TIMEOUT: int = 30
    CONFIDENCE_THRESHOLD: float = 0.5
    HALLUCINATION_THRESHOLD: float = 0.2
    
    # ============ Embedding Caching Settings ============
    EMBEDDING_CACHE_TTL: int = 2592000  # 30 days
    EMBEDDING_BATCH_SIZE: int = 32
    ENABLE_EMBEDDING_CACHE: bool = True
    
    # ============ Authentication Settings ============
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 1
    JWT_REFRESH_EXPIRATION_DAYS: int = 7
    
    # ============ Rate Limiting Settings ============
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_QUERIES_PER_MINUTE: int = 30
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 1000
    
    # ============ Monitoring & Logging Settings ============
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/rag_app.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ============ Monitoring Settings ============
    ENABLE_PROMETHEUS: bool = True
    PROMETHEUS_PORT: int = 8001
    
    # ============ Document Storage Settings ============
    STORAGE_TYPE: str = "local"  # local or s3
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = "us-east-1"
    
    # ============ Local Storage Settings ============
    DATA_DIR: str = "./data/"
    BACKUP_DIR: str = "./backups/"
    
    # ============ Batch Processing Settings ============
    BATCH_PROCESSING_ENABLED: bool = True
    BATCH_PROCESSING_SCHEDULE: str = "0 2 * * *"  # 2 AM daily
    
    # ============ Demo/Testing Settings ============
    DEMO_MODE: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Alias for convenience
settings = get_settings()
