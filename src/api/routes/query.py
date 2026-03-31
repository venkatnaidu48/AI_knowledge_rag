"""
Query Pipeline API Routes
REST endpoints for query processing and prompt building
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_database_session
from src.query_pipeline.query_processor import QueryProcessor, get_query_processor
from src.query_pipeline.prompt_builder import PromptBuilder, PromptTemplate, get_prompt_builder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/query", tags=["Query Pipeline"])


# ==================== FastAPI Dependencies ====================
# Wrap singletons in async functions for FastAPI dependency injection

async def get_query_processor_dep() -> QueryProcessor:
    """FastAPI dependency for query processor."""
    return get_query_processor()


async def get_prompt_builder_dep() -> PromptBuilder:
    """FastAPI dependency for prompt builder."""
    return get_prompt_builder()


# ==================== Pydantic Models ====================

class QueryRequest(BaseModel):
    """User query request."""
    query: str = Field(..., min_length=2, max_length=1000, description="User question")
    k: int = Field(5, ge=1, le=20, description="Number of results to retrieve")
    score_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity threshold")
    include_context: bool = Field(True, description="Include surrounding chunks")
    context_size: int = Field(1, ge=0, le=5, description="Surrounding chunks to include")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the company's financial strategy?",
                "k": 5,
                "score_threshold": 0.3,
                "include_context": True,
                "context_size": 1,
            }
        }


class DocumentQueryRequest(BaseModel):
    """Query restricted to specific document."""
    query: str = Field(..., min_length=2, max_length=1000)
    document_id: str = Field(..., description="Document UUID")
    k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.3, ge=0.0, le=1.0)


class DepartmentQueryRequest(BaseModel):
    """Query restricted to department's documents."""
    query: str = Field(..., min_length=2, max_length=1000)
    department: str = Field(..., min_length=1, max_length=100, description="Department name")
    k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.3, ge=0.0, le=1.0)


class PromptBuildRequest(BaseModel):
    """Request to build prompt from query results."""
    query: str = Field(..., min_length=2, max_length=1000)
    search_results: List[dict] = Field(..., description="Results from query/search")
    template: Optional[str] = Field(None, description="Prompt template (basic/detailed/context_first/qa_structured/summarization)")
    include_sources: bool = Field(True, description="Include document sources")
    include_metadata: bool = Field(True, description="Include chunk metadata")


class ChunkMetadata(BaseModel):
    """Metadata for a single chunk."""
    rank: int
    chunk_id: str
    chunk_number: int
    similarity_score: float
    tokens: Optional[int] = None


class QueryResultChunk(BaseModel):
    """Single chunk in query results."""
    rank: int
    chunk_id: str
    document_id: str
    document_title: str
    document_department: Optional[str] = None
    chunk_number: int
    similarity_score: float
    text: str
    tokens: Optional[int] = None
    created_at: Optional[str] = None
    context_chunks: Optional[List[dict]] = None


class QueryResponse(BaseModel):
    """Response from query processing."""
    success: bool
    query: str
    query_embedding_dimension: int
    search_results: List[QueryResultChunk]
    result_count: int
    processing_time_ms: float
    timestamp: str


class PromptResponse(BaseModel):
    """Response with built prompt."""
    success: bool
    prompt: str
    context: str
    system_prompt: str
    context_tokens: int
    template_used: str
    chunks_included: int
    query: str


class StatsResponse(BaseModel):
    """Statistics response."""
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float


# ==================== Query Endpoints ====================

@router.post("/process", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    db: Session = Depends(get_database_session),
    processor: QueryProcessor = Depends(get_query_processor_dep),
):
    """
    Process user query end-to-end.
    
    **Pipeline:**
    1. Generate embedding for query
    2. Semantic search in vector space
    3. Retrieve full chunk details
    4. Aggregate with metadata
    
    **Return includes:**
    - Top-k similar chunks
    - Similarity scores
    - Document metadata
    - Optional surrounding context
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/query/process" \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "What is the company strategy?",
        "k": 5,
        "score_threshold": 0.3,
        "include_context": true
      }'
    ```
    
    **Response fields:**
    - `query`: Original user query
    - `search_results`: Array of chunks with metadata
    - `result_count`: Number of results returned
    - `processing_time_ms`: Query latency
    """
    try:
        result = await processor.process_query(
            query=request.query,
            db=db,
            k=request.k,
            score_threshold=request.score_threshold,
            include_context=request.include_context,
            context_size=request.context_size,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-document")
async def process_query_document(
    request: DocumentQueryRequest,
    db: Session = Depends(get_database_session),
    processor: QueryProcessor = Depends(get_query_processor_dep),
):
    """
    Process query restricted to specific document.
    
    **Use cases:**
    - Search within single document
    - Document-specific Q&A
    - Focused retrieval
    
    **Parameters:**
    - `query`: Search query
    - `document_id`: Target document UUID
    - `k`: Number of results from that document
    
    **Response:**
    Similar to `/process` but limited to the document
    """
    try:
        result = await processor.process_query_by_document(
            query=request.query,
            document_id=request.document_id,
            db=db,
            k=request.k,
            score_threshold=request.score_threshold,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-department")
async def process_query_department(
    request: DepartmentQueryRequest,
    db: Session = Depends(get_database_session),
    processor: QueryProcessor = Depends(get_query_processor_dep),
):
    """
    Process query restricted to department's documents.
    
    **Use cases:**
    - Department-specific knowledge base
    - Role-based access
    - Scoped retrieval
    
    **Parameters:**
    - `query`: Search query
    - `department`: Department name
    - `k`: Number of results from department
    
    **Response:**
    Results limited to department's documents
    """
    try:
        result = await processor.process_query_by_department(
            query=request.query,
            department=request.department,
            db=db,
            k=request.k,
            score_threshold=request.score_threshold,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Department query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Prompt Building Endpoints ====================

@router.post("/build-prompt", response_model=PromptResponse)
async def build_prompt(
    request: PromptBuildRequest,
    prompt_builder: PromptBuilder = Depends(get_prompt_builder_dep),
):
    """
    Build LLM prompt from query + search results.
    
    **Features:**
    - Multiple prompt templates
    - Include/exclude sources and metadata
    - Token estimation
    
    **Templates available:**
    - `basic`: Simple context + question
    - `detailed`: Comprehensive with instructions (default)
    - `context_first`: Emphasizes context analysis
    - `qa_structured`: Structured Q&A with evidence
    - `summarization`: Optimized for summaries
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/query/build-prompt" \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "What is the strategy?",
        "search_results": [...],
        "template": "detailed",
        "include_sources": true
      }'
    ```
    
    **Response includes:**
    - `prompt`: Complete formatted prompt for LLM
    - `context`: Context section only
    - `system_prompt`: System instructions
    - `context_tokens`: Estimated token count
    """
    try:
        template = None
        if request.template:
            template = PromptTemplate(request.template)
        
        result = prompt_builder.build_prompt(
            query=request.query,
            search_results=request.search_results,
            template=template,
            include_sources=request.include_sources,
            include_metadata=request.include_metadata,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid template: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt building failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_templates(prompt_builder: PromptBuilder = Depends(get_prompt_builder_dep)):
    """
    List available prompt templates.
    
    **Returns:**
    - Array of template names
    - Template descriptions and use cases
    """
    templates = []
    for template_name in prompt_builder.get_available_templates():
        info = prompt_builder.get_template_info(template_name)
        templates.append({
            "name": template_name,
            **info,
        })
    
    return {
        "success": True,
        "templates": templates,
        "total": len(templates),
    }


# ==================== Statistics & Management ====================

@router.get("/stats", response_model=StatsResponse)
async def get_stats(processor: QueryProcessor = Depends(get_query_processor_dep)):
    """
    Get query processing statistics.
    
    **Returns:**
    - Total queries processed
    - Successful/failed queries
    - Success rate percentage
    """
    return processor.get_stats()


@router.post("/reset-stats")
async def reset_stats(processor: QueryProcessor = Depends(get_query_processor_dep)):
    """Reset query processing statistics."""
    processor.reset_stats()
    logger.info("Query stats reset via API")
    return {
        "success": True,
        "message": "Statistics reset successfully",
    }


@router.get("/health")
async def health_check(
    processor: QueryProcessor = Depends(get_query_processor_dep),
    prompt_builder: PromptBuilder = Depends(get_prompt_builder_dep),
):
    """
    Check query pipeline health.
    
    **Returns:**
    - Component status
    - Configuration info
    - Statistics summary
    """
    stats = processor.get_stats()
    
    return {
        "success": True,
        "status": "operational",
        "components": {
            "query_processor": "ready",
            "prompt_builder": "ready",
        },
        "query_statistics": stats,
        "available_templates": prompt_builder.get_available_templates(),
    }
