"""
Embedding API Routes
REST endpoints for generating, caching, and managing embeddings.
"""

import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_database_session
from src.database.models import Document, DocumentChunk
from src.embedding.processor import get_embedding_processor, EmbeddingProcessor
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/embeddings", tags=["Embeddings"])


# ==================== Pydantic Models ====================

class EmbedChunkRequest(BaseModel):
    """Request to embed a single chunk."""
    chunk_text: str = Field(..., min_length=10, max_length=10000)
    use_secondary: bool = Field(False, description="Use local model instead of OpenAI")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_text": "This is a document chunk that needs embedding.",
                "use_secondary": False,
            }
        }


class EmbedChunkResponse(BaseModel):
    """Response from single chunk embedding."""
    success: bool
    embedding: Optional[List[float]] = None
    dimension: Optional[int] = None
    source: str = Field(..., description="Where embedding came from: cache, openai, local_model")
    model: Optional[str] = None
    error: Optional[str] = None


class EmbedBatchRequest(BaseModel):
    """Request to embed multiple chunks."""
    chunk_texts: List[str] = Field(..., min_items=1, max_items=100)
    use_secondary: bool = Field(False, description="Use local model instead of OpenAI")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_texts": [
                    "First document chunk text.",
                    "Second document chunk text.",
                ],
                "use_secondary": False,
            }
        }


class EmbedBatchResponse(BaseModel):
    """Response from batch embedding."""
    success: bool
    embeddings: Optional[List[List[float]]] = None
    count: int
    from_cache: int
    newly_generated: int
    source: Optional[str] = None
    errors: List[str] = []


class EmbedDocumentRequest(BaseModel):
    """Request to embed all chunks of a document."""
    use_secondary: bool = Field(False, description="Use local model instead of OpenAI")
    chunk_ids: Optional[List[str]] = Field(None, description="Specific chunks to embed (null = all)")

    class Config:
        json_schema_extra = {
            "example": {
                "use_secondary": False,
                "chunk_ids": None,
            }
        }


class EmbedDocumentResponse(BaseModel):
    """Response from document embedding."""
    success: bool
    document_id: Optional[str] = None
    embedded_count: int
    from_cache: int
    newly_generated: int
    source: Optional[str] = None
    error: Optional[str] = None


class EmbeddingStatsResponse(BaseModel):
    """Embedding system statistics."""
    total_chunks_processed: int
    cached_hits: int
    openai_generated: int
    local_generated: int
    total_tokens_used: int
    total_cost_usd: float
    cache_hit_rate_percent: float
    errors: int


# ==================== API Endpoints ====================

@router.post("/chunk", response_model=EmbedChunkResponse)
async def embed_chunk(
    request: EmbedChunkRequest,
    processor: EmbeddingProcessor = Depends(get_embedding_processor),
) -> dict:
    """
    Generate embedding for a single text chunk.
    
    **Features:**
    - Automatic cache checking
    - OpenAI API integration with fallback
    - Local model fallback
    
    **Parameters:**
    - `chunk_text`: Text to embed (10-10000 characters)
    - `use_secondary`: Force use of local model (true/false)
    
    **Returns:**
    - Embedding vector (1536-D for OpenAI, 384-D for local)
    - Source: cache, openai, local_model, or local_model_fallback
    - Model used
    """
    try:
        result = await processor.embed_chunk(
            request.chunk_text,
            use_secondary=request.use_secondary,
        )
        return result
    except Exception as e:
        logger.error(f"Error embedding chunk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=EmbedBatchResponse)
async def embed_batch(
    request: EmbedBatchRequest,
    processor: EmbeddingProcessor = Depends(get_embedding_processor),
) -> dict:
    """
    Generate embeddings for multiple text chunks with intelligent batching.
    
    **Features:**
    - Parallel processing (up to 32 at a time)
    - Smart caching (retrieves cached, generates missing)
    - Cost tracking
    - Intelligent fallback
    
    **Parameters:**
    - `chunk_texts`: List of texts to embed (1-100 items)
    - `use_secondary`: Force use of local model
    
    **Returns:**
    - Embeddings list (parallel to input)
    - Cache hit/miss counts
    - Generation source
    - Any errors encountered
    
    **Example:**
    ```
    {
        "chunk_texts": ["Text 1", "Text 2"],
        "use_secondary": false
    }
    ```
    """
    try:
        result = await processor.embed_batch(
            request.chunk_texts,
            use_secondary=request.use_secondary,
        )
        return result
    except Exception as e:
        logger.error(f"Error embedding batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document/{document_id}", response_model=EmbedDocumentResponse)
async def embed_document(
    document_id: str,
    request: EmbedDocumentRequest,
    db: Session = Depends(get_database_session),
    processor: EmbeddingProcessor = Depends(get_embedding_processor),
) -> dict:
    """
    Generate embeddings for all chunks of a specific document.
    
    **Features:**
    - Automatic chunk retrieval from database
    - Batch processing optimization
    - Database persistence
    - Atomic transactions (all-or-nothing)
    
    **Path Parameters:**
    - `document_id`: UUID of document
    
    **Query Parameters:**
    - `use_secondary`: Force local model (default: false)
    - `chunk_ids`: Comma-separated chunk IDs (default: all)
    
    **Returns:**
    - Count of embeddings created/updated
    - Cache hit ratio
    - Source of embeddings
    - Any errors
    
    **Example:**
    `POST /api/v1/embeddings/document/a1b2c3d4-e5f6-7890-abcd-ef1234567890?use_secondary=false`
    """
    try:
        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Call processor
        result = processor.embed_chunks_for_document(
            db=db,
            document_id=document_id,
            chunk_ids=request.chunk_ids,
            use_secondary=request.use_secondary,
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error embedding document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=EmbeddingStatsResponse)
async def get_stats(
    processor: EmbeddingProcessor = Depends(get_embedding_processor),
) -> dict:
    """
    Get embedding system statistics.
    
    **Returns:**
    - Total chunks processed
    - Cache hits and generation counts
    - API tokens used and costs
    - Error counts
    - Cache performance metrics
    
    **Example Response:**
    ```json
    {
        "total_chunks_processed": 1250,
        "cached_hits": 890,
        "openai_generated": 310,
        "local_generated": 50,
        "total_tokens_used": 125000,
        "total_cost_usd": 2.50,
        "cache_hit_rate_percent": 71.2,
        "errors": 5
    }
    ```
    """
    try:
        stats = processor.get_stats()
        cache_stats = stats.get("cache_stats", {})
        
        return {
            "total_chunks_processed": stats["total_chunks_processed"],
            "cached_hits": cache_stats.get("hits", 0),
            "openai_generated": stats["openai_generated"],
            "local_generated": stats["local_generated"],
            "total_tokens_used": stats["total_tokens_used"],
            "total_cost_usd": stats["total_cost_usd"],
            "cache_hit_rate_percent": cache_stats.get("hit_rate_percent", 0),
            "errors": stats["errors"],
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-stats")
async def reset_stats(
    processor: EmbeddingProcessor = Depends(get_embedding_processor),
) -> dict:
    """
    Reset all embedding statistics counters.
    
    **Used for:** Testing, debugging, or starting fresh tracking
    
    **Returns:** Confirmation message
    """
    try:
        processor.reset_stats()
        logger.info("Embedding statistics reset via API")
        return {
            "success": True,
            "message": "Statistics reset successfully",
        }
    except Exception as e:
        logger.error(f"Error resetting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check ====================

@router.get("/health")
async def health_check(
    processor: EmbeddingProcessor = Depends(get_embedding_processor),
) -> dict:
    """
    Check embedding system health.
    
    **Returns:**
    - OpenAI API availability
    - Local model availability
    - Redis cache availability
    - Overall system status
    """
    try:
        cache = processor.cache
        locl_emb = processor.local_embedder
        
        return {
            "status": "healthy",
            "components": {
                "openai_api": "available" if settings.OPENAI_API_KEY else "not_configured",
                "local_model": "available" if locl_emb else "error",
                "redis_cache": "available" if cache.is_available() else "unavailable",
            },
            "timestamp": "2026-03-02T00:00:00Z",
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
