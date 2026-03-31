"""
Database Models for RAG Application
Defines SQLAlchemy ORM models for all entities
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()


class Document(Base):
    """Model for storing document metadata"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False, index=True)
    version = Column(String, default="1.0")
    
    # Metadata
    upload_date = Column(DateTime, default=datetime.utcnow)
    effective_date = Column(DateTime, nullable=True)
    expires_date = Column(DateTime, nullable=True)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Organization
    department = Column(String, index=True, nullable=True)
    owner_email = Column(String, nullable=True)
    
    # Classification
    sensitivity = Column(
        Enum("public", "internal", "confidential", name="sensitivity_enum"),
        default="internal"
    )
    category = Column(String, index=True, nullable=True)
    
    # File info
    storage_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    hash_md5 = Column(String, unique=True, nullable=False, index=True)
    
    # Status
    status = Column(
        Enum("active", "archived", "deprecated", name="doc_status_enum"),
        default="active"
    )
    processing_status = Column(
        Enum("pending", "indexed", "failed", name="proc_status_enum"),
        default="pending"
    )
    
    error_message = Column(Text, nullable=True)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Document(id={self.id}, name={self.name}, version={self.version})>"


class DocumentVersion(Base):
    """Track document versions for rollback capability"""
    __tablename__ = "document_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    version = Column(String, nullable=False)
    
    chunks_count = Column(Integer)
    embeddings_count = Column(Integer)
    file_hash = Column(String)
    storage_path = Column(String)
    
    status = Column(
        Enum("active", "archived", "deprecated", name="vers_status_enum"),
        default="active"
    )
    rollback_available = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    created_timestamp = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="versions")
    
    def __repr__(self):
        return f"<DocumentVersion(id={self.id}, version={self.version})>"


class DocumentChunk(Base):
    """Model for document chunks (text segments)"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    
    # Content
    chunk_text = Column(Text, nullable=False)
    chunk_number = Column(Integer)
    tokens_count = Column(Integer)
    
    # Metadata
    section_title = Column(String, nullable=True)
    hierarchy_level = Column(Integer, default=0)
    importance_score = Column(Float, default=0.5)
    quality_score = Column(Float, default=0.5)
    
    context_before = Column(Text, nullable=True)
    context_after = Column(Text, nullable=True)
    
    language = Column(String, default="en")
    
    # Embedding status
    embedding_generated = Column(Boolean, default=False)
    embedding_timestamp = Column(DateTime, nullable=True)
    embedding_model = Column(String, nullable=True)
    
    # Backup embedding (local model)
    backup_embedding_generated = Column(Boolean, default=False)
    backup_embedding_model = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, chunk_number={self.chunk_number})>"


class ChunkEmbedding(Base):
    """Model for storing chunk embeddings"""
    __tablename__ = "chunk_embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String, ForeignKey("document_chunks.id"), nullable=False, unique=True, index=True)
    
    # Primary embedding (OpenAI)
    embedding_vector = Column(JSON)  # Store as JSON array to avoid pgvector dependency initially
    embedding_model = Column(String, default="text-embedding-3-small")
    embedding_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Backup embedding (local model)
    backup_embedding_vector = Column(JSON, nullable=True)
    backup_embedding_model = Column(String, nullable=True)
    
    status = Column(
        Enum("ready", "processing", "failed", name="embedding_status_enum"),
        default="ready"
    )
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chunk = relationship("DocumentChunk", back_populates="embeddings")
    
    def __repr__(self):
        return f"<ChunkEmbedding(id={self.id}, chunk_id={self.chunk_id})>"


class EmbeddingCache(Base):
    """Cache for embeddings to avoid recomputation"""
    __tablename__ = "embedding_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_hash = Column(String, unique=True, nullable=False, index=True)
    chunk_text = Column(Text)
    
    embedding_model = Column(String, nullable=False)
    embedding_vector = Column(JSON, nullable=False)
    
    embedding_timestamp = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ttl_expires = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmbeddingCache(id={self.id}, model={self.embedding_model})>"


class Query(Base):
    """Model for storing query history and analytics"""
    __tablename__ = "queries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Query content
    query_text = Column(Text, nullable=False)
    query_embedding = Column(JSON, nullable=True)
    
    # User info
    user_id = Column(String, nullable=True, index=True)
    user_email = Column(String, nullable=True)
    
    # Response info
    answer = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    hallucination_rate = Column(Float, nullable=True)
    source_verification_rate = Column(Float, nullable=True)
    
    # LLM info
    llm_model_used = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    response_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    
    # Processing
    processing_time_ms = Column(Integer, nullable=True)
    retrieval_time_ms = Column(Integer, nullable=True)
    llm_time_ms = Column(Integer, nullable=True)
    
    # Status
    status = Column(
        Enum("success", "partial", "failed", name="query_status_enum"),
        default="success"
    )
    error_message = Column(Text, nullable=True)
    
    # Feedback
    user_feedback = Column(
        Enum("thumbs_up", "thumbs_down", "none", name="feedback_enum"),
        default="none"
    )
    user_feedback_text = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Query(id={self.id}, status={self.status})>"


class QueryResult(Base):
    """Model for retrieved documents in a query response"""
    __tablename__ = "query_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query_id = Column(String, ForeignKey("queries.id"), nullable=False, index=True)
    chunk_id = Column(String, ForeignKey("document_chunks.id"), nullable=False, index=True)
    
    # Relevance scores
    semantic_score = Column(Float)
    keyword_score = Column(Float)
    combined_score = Column(Float, nullable=True)
    rank = Column(Integer)
    
    # Inclusion status
    included_in_context = Column(Boolean, default=True)
    used_in_answer = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<QueryResult(query_id={self.query_id}, rank={self.rank})>"


class SystemMetric(Base):
    """Model for system-level metrics and monitoring"""
    __tablename__ = "system_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Metric type
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    
    # Breakdown
    metric_type = Column(String)  # query_time, hallucination_rate, etc.
    dimension = Column(String, nullable=True)  # department, date, etc.
    
    # Time
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemMetric(name={self.metric_name}, value={self.metric_value})>"
