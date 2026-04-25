"""
Enterprise Database Models for RAG System
Extended with rich metadata for production-grade chunking and retrieval
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Enum, JSON, Array
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class ChunkType(str, enum.Enum):
    """Types of chunks"""
    HEADER = "header"
    BODY = "body"
    TABLE = "table"
    LIST = "list"
    CODE = "code"
    FORMULA = "formula"
    IMAGE_CAPTION = "image_caption"
    FOOTER = "footer"
    UNKNOWN = "unknown"


class QualityGate(str, enum.Enum):
    """Quality assessment gate results"""
    PASSED = "passed"
    FAILED = "failed"
    FLAGGED = "flagged"


class DocumentType(str, enum.Enum):
    """Types of documents"""
    GENERAL_TEXT = "general_text"
    PDF_TEXT = "pdf_text"
    PDF_SCANNED = "pdf_scanned"
    TABLE_RICH = "table_rich"
    CODE = "code"
    STRUCTURED_DATA = "structured_data"
    LEGAL_CONTRACT = "legal_contract"
    SCIENTIFIC_PAPER = "scientific_paper"
    EMAIL = "email"
    FORM = "form"


# ============================================================================
# CORE MODELS (EXISTING - ENHANCED)
# ============================================================================

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
    
    # NEW: Document type (for chunking strategy selection)
    document_type = Column(
        Enum(DocumentType, name="document_type_enum"),
        default=DocumentType.GENERAL_TEXT
    )
    
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
    
    # NEW: Statistics
    total_chunks = Column(Integer, default=0)
    chunks_passed_qc = Column(Integer, default=0)
    quality_filtered = Column(Integer, default=0)
    average_chunk_quality = Column(Float, default=0.0)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Document(id={self.id}, name={self.name}, type={self.document_type})>"


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


# ============================================================================
# ENHANCED CHUNK MODEL
# ============================================================================

class DocumentChunk(Base):
    """
    Enhanced model for document chunks with rich metadata.
    
    Stores:
    - Chunk text content
    - Positional information (page, byte offset, position)
    - Structural metadata (hierarchy, section, type)
    - Quality metrics (quality_score, readability, coherence, etc.)
    - Content analysis (entities, keywords, language)
    - Relationships (previous/next chunks, cross-references)
    - Retrieval metadata (importance, confidence)
    """
    __tablename__ = "document_chunks"
    
    # ========================================================================
    # CORE IDENTIFICATION
    # ========================================================================
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    
    # Content
    chunk_text = Column(Text, nullable=False)
    chunk_number = Column(Integer, nullable=False)  # Sequential number in document
    
    # ========================================================================
    # POSITIONAL METADATA
    # ========================================================================
    page_number = Column(Integer, nullable=True, index=True)  # For PDF reference
    position_in_document = Column(Integer, default=0)  # Byte offset
    start_char = Column(Integer, default=0)  # Character position in text
    end_char = Column(Integer, default=0)  # End character position
    
    # ========================================================================
    # STRUCTURAL METADATA
    # ========================================================================
    section_id = Column(String, nullable=True, index=True)  # e.g., "section-1"
    section_title = Column(String, nullable=True, index=True)  # e.g., "Introduction"
    section_path = Column(String, nullable=True)  # Hierarchical path: "1.2.3.4"
    
    hierarchy_level = Column(Integer, default=0)  # 0=body, 1=H1, 2=H2, 3=H3, 4=H4, 5=H5
    nesting_level = Column(Integer, default=0)  # For lists, nested structures
    
    # Chunk type classification
    chunk_type = Column(
        Enum(ChunkType, name="chunk_type_enum"),
        default=ChunkType.UNKNOWN
    )
    is_header = Column(Boolean, default=False)
    is_footer = Column(Boolean, default=False)
    
    # ========================================================================
    # QUALITY METRICS (COMPREHENSIVE)
    # ========================================================================
    quality_score = Column(Float, default=0.5)  # Overall quality (0-1)
    completeness_score = Column(Float, default=0.5)  # Information completeness (0-1)
    coherence_score = Column(Float, default=0.5)  # Text coherence (0-1)
    
    # Readability metrics
    readability_score = Column(Float, default=50.0)  # Flesch-Kincaid (0-100)
    average_sentence_length = Column(Float, default=0.0)  # Words per sentence
    
    # Confidence scores
    language_confidence = Column(Float, default=0.95)  # Language detection confidence (0-1)
    technical_score = Column(Float, default=0.0)  # Presence of code/formulas (0-1)
    confidence = Column(Float, default=1.0)  # Extraction confidence (0-1)
    
    # Quality gate result
    quality_gate_result = Column(
        Enum(QualityGate, name="quality_gate_enum"),
        default=QualityGate.PASSED
    )
    quality_issues = Column(JSON, default=[])  # List of issues found
    
    # ========================================================================
    # IMPORTANCE & RELEVANCE
    # ========================================================================
    importance_score = Column(Float, default=0.5)  # Domain importance (0-1)
    entity_count = Column(Integer, default=0)  # Named entities count
    keyword_density = Column(Float, default=0.0)  # Keyword density (0-1)
    
    # ========================================================================
    # CONTENT ANALYSIS
    # ========================================================================
    token_count = Column(Integer, default=0)  # Approximate token count
    character_count = Column(Integer, default=0)  # Character count
    sentence_count = Column(Integer, default=0)  # Number of sentences
    
    # Content flags
    contains_code = Column(Boolean, default=False)
    contains_numbers = Column(Boolean, default=False)
    contains_url = Column(Boolean, default=False)
    
    # Language
    language = Column(String, default="en")
    
    # ========================================================================
    # CONTENT SUMMARY & EXTRACTION
    # ========================================================================
    key_points = Column(JSON, default=[])  # List of key points (3-5)
    entities = Column(JSON, default={})  # Named entities: {"PERSON": [...], "ORG": [...]}
    summary = Column(Text, nullable=True)  # Short summary (optional)
    
    # Extraction method
    extraction_method = Column(String, default="text_extraction")  # "text_extraction", "ocr", etc.
    
    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================
    previous_chunk_id = Column(String, nullable=True)  # ID of previous chunk
    next_chunk_id = Column(String, nullable=True)  # ID of next chunk
    related_chunk_ids = Column(JSON, default=[])  # List of related chunk IDs
    
    # ========================================================================
    # EMBEDDING STATUS
    # ========================================================================
    embedding_generated = Column(Boolean, default=False)
    embedding_timestamp = Column(DateTime, nullable=True)
    embedding_model = Column(String, nullable=True)
    
    # Backup embedding (local model)
    backup_embedding_generated = Column(Boolean, default=False)
    backup_embedding_model = Column(String, nullable=True)
    
    # ========================================================================
    # TIMESTAMPS
    # ========================================================================
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================
    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, chunk_number={self.chunk_number}, quality={self.quality_score:.2f})>"


# ============================================================================
# EMBEDDING MODEL (EXISTING - ENHANCED)
# ============================================================================

class ChunkEmbedding(Base):
    """Model for storing chunk embeddings (vector representations)"""
    __tablename__ = "chunk_embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String, ForeignKey("document_chunks.id"), nullable=False, unique=True, index=True)
    
    # Primary embedding (OpenAI or other)
    embedding_vector = Column(JSON)  # Store as JSON array
    embedding_model = Column(String, default="text-embedding-3-small")
    embedding_dimension = Column(Integer, default=1536)  # NEW: Dimension info
    embedding_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Backup embedding (local model like all-MiniLM-L6-v2)
    backup_embedding_vector = Column(JSON, nullable=True)
    backup_embedding_model = Column(String, nullable=True)
    backup_embedding_dimension = Column(Integer, nullable=True)
    
    # Normalization info
    vector_norm = Column(Float, nullable=True)  # L2 norm for similarity calculations
    is_normalized = Column(Boolean, default=False)
    
    # Quality metadata
    generation_method = Column(String, default="api")  # "api", "local", "offline"
    generation_time_ms = Column(Integer, nullable=True)  # Time taken to generate
    
    # NEW: Versioning
    embedding_version = Column(String, default="1.0")
    regeneration_needed = Column(Boolean, default=False)  # Flag for re-embedding
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chunk = relationship("DocumentChunk", back_populates="embeddings")
    
    def __repr__(self):
        return f"<ChunkEmbedding(chunk_id={self.chunk_id}, model={self.embedding_model})>"


# ============================================================================
# NEW: CHUNK QUALITY AUDIT MODEL
# ============================================================================

class ChunkQualityAudit(Base):
    """Track quality assessment history for chunks"""
    __tablename__ = "chunk_quality_audit"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String, ForeignKey("document_chunks.id"), nullable=False, index=True)
    
    # Assessment details
    assessment_date = Column(DateTime, default=datetime.utcnow)
    assessor = Column(String, nullable=True)  # Who/what assessed (system/user)
    
    # Scores
    quality_score_before = Column(Float)
    quality_score_after = Column(Float)
    
    # Issues found and fixed
    issues_found = Column(JSON)  # List of quality issues
    actions_taken = Column(JSON)  # List of corrective actions
    
    # Notes
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ChunkQualityAudit(chunk_id={self.chunk_id}, date={self.assessment_date})>"


# ============================================================================
# NEW: BATCH PROCESSING LOG
# ============================================================================

class BatchProcessingLog(Base):
    """Track batch processing statistics and performance"""
    __tablename__ = "batch_processing_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Batch info
    batch_id = Column(String, unique=True, index=True)
    document_ids = Column(JSON)  # List of processed documents
    batch_size = Column(Integer)
    
    # Processing metrics
    total_documents = Column(Integer)
    total_chunks_created = Column(Integer)
    chunks_passed_qc = Column(Integer)
    chunks_failed_qc = Column(Integer)
    
    # Performance
    total_processing_time_seconds = Column(Float)
    average_chunk_size = Column(Float)
    chunks_per_second = Column(Float)
    
    # Quality metrics
    average_quality_score = Column(Float)
    average_readability = Column(Float)
    language_distribution = Column(JSON)  # e.g., {"en": 95, "es": 5}
    
    # Status
    status = Column(String, default="completed")  # "running", "completed", "failed"
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<BatchProcessingLog(batch_id={self.batch_id}, status={self.status})>"


# ============================================================================
# NEW: CHUNK RETRIEVAL METRICS
# ============================================================================

class ChunkRetrievalMetrics(Base):
    """Track how often chunks are retrieved and their usefulness"""
    __tablename__ = "chunk_retrieval_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String, ForeignKey("document_chunks.id"), nullable=False, index=True)
    
    # Retrieval statistics
    retrieval_count = Column(Integer, default=0)  # Times retrieved in queries
    useful_count = Column(Integer, default=0)  # Times marked as useful
    not_useful_count = Column(Integer, default=0)  # Times marked as not useful
    
    # Performance metrics
    average_relevance_score = Column(Float, default=0.0)  # From queries
    average_retrieval_rank = Column(Float, default=0.0)  # Average position in results
    
    # Quality metrics from user feedback
    user_rating = Column(Float, nullable=True)  # 1-5 stars from user feedback
    user_feedback_count = Column(Integer, default=0)
    
    # Engagement
    time_viewed_seconds = Column(Integer, default=0)  # Total view time
    viewed_in_responses = Column(Integer, default=0)  # Used in LLM responses
    
    last_retrieved = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ChunkRetrievalMetrics(chunk_id={self.chunk_id}, retrieval_count={self.retrieval_count})>"


# ============================================================================
# INDEXES FOR PERFORMANCE
# ============================================================================

"""
Database indexes for optimal query performance:

Indexes created in models:
- documents.name (unique)
- documents.hash_md5 (unique, duplicate detection)
- documents.department (organization filtering)
- documents.category (content filtering)
- document_chunks.document_id (chunk retrieval)
- document_chunks.page_number (PDF reference)
- document_chunks.section_title (section search)
- document_chunks.chunk_type (type-specific queries)
- document_chunks.quality_gate_result (QC filtering)
- chunk_embeddings.chunk_id (embedding lookup)
- chunk_quality_audit.chunk_id (audit trails)
- batch_processing_log.batch_id (batch tracking)
- chunk_retrieval_metrics.chunk_id (usage analytics)

Recommended composite indexes:
- (document_id, chunk_number) - chunk sequencing
- (document_id, quality_gate_result) - QC filtering
- (section_id, hierarchy_level) - hierarchy queries
- (chunk_type, quality_score) - type + quality filtering
"""

