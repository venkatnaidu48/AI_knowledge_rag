"""
Vector Search API Routes
REST endpoints for semantic similarity search using FAISS.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_database_session
from src.vector_db.index_manager import get_faiss_manager, FAISSIndexManager
from src.vector_db.search_engine import get_search_engine, VectorSearchEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


# ==================== FastAPI Dependencies ====================
# Wrap singletons in async functions for FastAPI dependency injection

async def get_faiss_manager_dep() -> FAISSIndexManager:
    """FastAPI dependency for FAISS index manager."""
    return get_faiss_manager()


async def get_search_engine_dep() -> VectorSearchEngine:
    """FastAPI dependency for vector search engine."""
    return get_search_engine()


# ==================== Pydantic Models ====================

class InitializeIndexRequest(BaseModel):
    """Request to initialize vector index from database."""
    pass


class SearchRequest(BaseModel):
    """Request to search with embedding."""
    query_embedding: List[float] = Field(..., description="Query embedding vector (1536D or 384D)")
    k: int = Field(5, ge=1, le=50, description="Number of results to return")
    score_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity score (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "query_embedding": [0.1, 0.2, 0.3],  # In practice 1536 values
                "k": 5,
                "score_threshold": 0.3,
            }
        }


class SearchResult(BaseModel):
    """Single search result."""
    rank: int
    chunk_id: str
    document_id: str
    chunk_number: int
    text_preview: str
    distance: float
    similarity: float

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Response from search query."""
    success: bool
    results: List[SearchResult] = []
    count: int
    timestamp: Optional[str] = None

    class Config:
        from_attributes = True


class SearchByDocumentRequest(BaseModel):
    """Request to search within specific document."""
    query_embedding: List[float]
    document_id: str = Field(..., description="UUID of document to search")
    k: int = Field(5, ge=1, le=50)
    score_threshold: float = Field(0.3, ge=0.0, le=1.0)


class SearchByDepartmentRequest(BaseModel):
    """Request to search within department's documents."""
    query_embedding: List[float]
    department: str = Field(..., description="Department to search within")
    k: int = Field(5, ge=1, le=50)
    score_threshold: float = Field(0.3, ge=0.0, le=1.0)


class IndexStatsResponse(BaseModel):
    """Vector index statistics."""
    ntotal: int = Field(..., description="Total vectors in index")
    dimension: int = Field(..., description="Embedding dimension")
    embedding_count: int
    index_type: str


class SearchStatsResponse(BaseModel):
    """Search system statistics."""
    total_searches: int
    successful_searches: int
    failed_searches: int
    success_rate_percent: float
    total_results_returned: int
    avg_results_per_search: float
    index_stats: IndexStatsResponse


# ==================== API Endpoints ====================

@router.post("/initialize")
async def initialize_index(
    db: Session = Depends(get_database_session),
    index_manager: FAISSIndexManager = Depends(get_faiss_manager_dep),
):
    """
    Initialize FAISS index from all embeddings in database.
    
    **Important:** Run this after embedding all documents (STEP 3).
    
    **Features:**
    - Reads all ChunkEmbedding records from database
    - Builds FAISS index for L2 similarity search
    - Creates chunk ID → FAISS index mappings
    - Saves index to disk
    
    **Response:**
    - success: True/False
    - count: Number of embeddings indexed
    - dimension: Embedding dimension (1536 or 384)
    - timestamp: When index was created
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/search/initialize"
    ```
    """
    try:
        logger.info("Initializing vector index from database...")
        result = index_manager.create_index_from_db(db)
        
        if result["success"]:
            # Save to disk
            saved = index_manager.save_index()
            result["saved_to_disk"] = saved
            logger.info(f"✓ Index initialized with {result['count']} embeddings")
        
        return result
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search(
    request: SearchRequest,
    search_engine: VectorSearchEngine = Depends(get_search_engine_dep),
):
    """
    Semantic similarity search across all documents.
    
    **Features:**
    - Returns top-k most similar chunks
    - Filters by similarity threshold
    - Returns text preview and document info
    
    **Parameters:**
    - `query_embedding`: Query embedding vector (get from STEP 3 endpoint)
    - `k`: Number of results (1-50)
    - `score_threshold`: Minimum similarity score (0.0-1.0)
    
    **Response:**
    - results: List of SearchResult objects
    - count: Number of results returned
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/search/search" \
      -H "Content-Type: application/json" \
      -d '{"query_embedding": [0.1, -0.2, ...], "k": 5, "score_threshold": 0.3}'
    ```
    """
    try:
        result = search_engine.search(
            query_embedding=request.query_embedding,
            k=request.k,
            score_threshold=request.score_threshold,
        )
        return result
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-with-context")
async def search_with_context(
    request: SearchRequest,
    context_size: int = Query(1, ge=0, le=5, description="Surrounding chunks to include"),
    db: Session = Depends(get_database_session),
    search_engine: VectorSearchEngine = Depends(get_search_engine_dep),
):
    """
    Semantic search with expanded context (surrounding chunks).
    
    **Features:**
    - Returns top results with neighboring chunks
    - Useful for understanding chunk context
    - Combines multiple chunks for better grounding
    
    **Parameters:**
    - `query_embedding`: Query vector
    - `k`: Number of results
    - `score_threshold`: Minimum similarity
    - `context_size`: Number of neighboring chunks (0-5)
    
    **Response:**
    - Each result includes `context_text` (combined chunk text)
    - `context_chunks_count`: Number of chunks combined
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/search/search-with-context?context_size=2" \
      -H "Content-Type: application/json" \
      -d '{"query_embedding": [...], "k": 3}'
    ```
    """
    try:
        result = search_engine.search_with_context(
            query_embedding=request.query_embedding,
            db=db,
            k=request.k,
            context_size=context_size,
            score_threshold=request.score_threshold,
        )
        return result
    except Exception as e:
        logger.error(f"Context search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-document")
async def search_by_document(
    request: SearchByDocumentRequest,
    db: Session = Depends(get_database_session),
    search_engine: VectorSearchEngine = Depends(get_search_engine_dep),
):
    """
    Search within a specific document only.
    
    **Features:**
    - Restrict search to single document
    - Useful for document-specific Q&A
    - Faster than full corpus search
    
    **Parameters:**
    - `query_embedding`: Query vector
    - `document_id`: UUID of document to search
    - `k`: Number of results
    - `score_threshold`: Minimum similarity
    
    **Response:**
    - Results filtered to requested document only
    - Includes document name
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/search/search-document" \
      -H "Content-Type: application/json" \
      -d '{"query_embedding": [...], "document_id": "uuid-here", "k": 5}'
    ```
    """
    try:
        result = search_engine.search_by_document(
            query_embedding=request.query_embedding,
            document_id=request.document_id,
            db=db,
            k=request.k,
            score_threshold=request.score_threshold,
        )
        return result
    except Exception as e:
        logger.error(f"Document search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-department")
async def search_by_department(
    request: SearchByDepartmentRequest,
    db: Session = Depends(get_database_session),
    search_engine: VectorSearchEngine = Depends(get_search_engine_dep),
):
    """
    Search within documents of a specific department.
    
    **Features:**
    - Restrict search to department
    - Role-based search (e.g., Finance dept only)
    - Useful for scoped retrieval
    
    **Parameters:**
    - `query_embedding`: Query vector
    - `department`: Department name
    - `k`: Number of results
    - `score_threshold`: Minimum similarity
    
    **Response:**
    - Results from department's documents
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/search/search-department" \
      -H "Content-Type: application/json" \
      -d '{"query_embedding": [...], "department": "Finance", "k": 5}'
    ```
    """
    try:
        result = search_engine.search_by_department(
            query_embedding=request.query_embedding,
            department=request.department,
            db=db,
            k=request.k,
            score_threshold=request.score_threshold,
        )
        return result
    except Exception as e:
        logger.error(f"Department search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chunk/{chunk_id}")
async def get_chunk_details(
    chunk_id: str,
    db: Session = Depends(get_database_session),
    search_engine: VectorSearchEngine = Depends(get_search_engine_dep),
):
    """
    Get full details for a specific chunk.
    
    **Parameters:**
    - `chunk_id`: UUID of chunk
    
    **Response:**
    - Full chunk text
    - Document information
    - Metadata and scores
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/v1/search/chunk/uuid-here"
    ```
    """
    try:
        result = search_engine.get_chunk_details(chunk_id, db)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(
    search_engine: VectorSearchEngine = Depends(get_search_engine_dep),
):
    """
    Get vector search system statistics.
    
    **Returns:**
    - Total searches performed
    - Success/failure rates
    - Index statistics
    - Average results per search
    
    **Example Response:**
    ```json
    {
        "total_searches": 150,
        "successful_searches": 145,
        "failed_searches": 5,
        "success_rate_percent": 96.67,
        "total_results_returned": 725,
        "avg_results_per_search": 5.0,
        "index_stats": {
            "ntotal": 1250,
            "dimension": 1536,
            "embedding_count": 1250,
            "index_type": "IndexFlatL2"
        }
    }
    ```
    """
    try:
        stats = search_engine.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-stats")
async def reset_stats(
    search_engine: VectorSearchEngine = Depends(get_search_engine_dep),
):
    """
    Reset search statistics.
    
    **Used for:** Testing, debugging, or starting fresh tracking
    """
    try:
        search_engine.reset_stats()
        logger.info("Search stats reset via API")
        return {
            "success": True,
            "message": "Statistics reset successfully",
        }
    except Exception as e:
        logger.error(f"Error resetting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(
    index_manager: FAISSIndexManager = Depends(get_faiss_manager_dep),
):
    """
    Check vector database health.
    
    **Returns:**
    - Index status (initialized, empty, loaded)
    - Vector count
    - Index statistics
    """
    try:
        stats = index_manager.get_stats()
        return {
            "status": "healthy",
            "index": {
                "initialized": index_manager.index is not None,
                "vectors_indexed": stats["ntotal"],
                "dimension": stats["dimension"],
                "index_type": stats["index_type"],
            },
            "timestamp": stats["timestamp"],
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
