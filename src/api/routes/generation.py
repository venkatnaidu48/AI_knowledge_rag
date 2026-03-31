"""
Generation API Routes
REST endpoints for LLM generation with context grounding
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_database_session
from src.generation.manager import GenerationManager, get_generation_manager
from src.generation.base import GenerationRequest as GenRequest, LLMProviderType
from src.generation.grounding import get_grounding_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generation", tags=["Generation"])


# ==================== FastAPI Dependencies ====================

async def get_generation_manager_dep() -> GenerationManager:
    """FastAPI dependency for generation manager."""
    return get_generation_manager()


# ==================== Pydantic Models ====================

class GenerateRequest(BaseModel):
    """Request to generate response."""
    query: str = Field(..., min_length=2, max_length=1000, description="Original user query")
    context_chunks: List[dict] = Field(..., description="Retrieved context chunks")
    prompt: str = Field(..., min_length=10, description="Formatted prompt for LLM")
    provider: Optional[str] = Field(None, description="LLM provider (mistral/openai/huggingface/groq)")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(1000, ge=100, le=4000, description="Max response tokens")
    require_grounding: bool = Field(True, description="Require grounding validation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is our financial strategy?",
                "context_chunks": [{"text": "Our strategy focuses on..."}],
                "prompt": "Based on context...",
                "provider": "mistral",
                "temperature": 0.7,
                "max_tokens": 1000,
            }
        }


class GroundingCheckRequest(BaseModel):
    """Request to check grounding of response."""
    response_text: str = Field(..., description="Generated response to check")
    context_chunks: List[dict] = Field(..., description="Retrieved context")
    query: Optional[str] = Field(None, description="Original query for context")


class GenerationChunk(BaseModel):
    """Output chunk in generation response."""
    rank: Optional[int] = None
    chunk_id: Optional[str] = None
    text: str
    similarity_score: Optional[float] = None


class GroundingInfo(BaseModel):
    """Grounding analysis result."""
    is_grounded: bool
    grounding_score: float
    source_references: List[str]
    issues: List[str]
    explanation: str


class GenerateResponse(BaseModel):
    """Response from generation endpoint."""
    success: bool
    response: str
    provider_used: str
    model_used: str
    grounding: Optional[GroundingInfo] = None
    tokens_used: Optional[dict] = None
    latency_ms: float
    query: str


class StatsResponse(BaseModel):
    """Statistics response."""
    total_generations: int
    successful: int
    failed: int
    success_rate: float
    fallback_used: int
    grounded_responses: int
    hallucinations: int
    grounding_rate: float


class ProviderInfo(BaseModel):
    """Information about LLM provider."""
    name: str
    provider_type: str
    available: bool
    model_name: Optional[str] = None


class ProvidersResponse(BaseModel):
    """Response listing available providers."""
    providers: List[ProviderInfo]


# ==================== Generation Endpoints ====================

@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    manager: GenerationManager = Depends(get_generation_manager_dep),
):
    """
    Generate response with context grounding.
    
    **Process:**
    1. Select LLM provider (Mistral/OpenAI/HuggingFace/Groq)
    2. Generate response from prompt
    3. Validate grounding in context (optional)
    4. Return response with metadata
    
    **Features:**
    - Multiple LLM providers (paid & free)
    - Automatic fallback if primary fails
    - Grounding validation to detect hallucinations
    - Provider selection/override
    
    **Providers:**
    - `mistral`: Free local (Ollama)
    - `openai`: Paid GPT models
    - `huggingface`: Free cloud
    - `groq`: Fast free inference
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/generation/generate" \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "What is our strategy?",
        "context_chunks": [...],
        "prompt": "Based on context...",
        "provider": "mistral",
        "temperature": 0.7,
        "require_grounding": true
      }'
    ```
    
    **Response includes:**
    - `response`: Generated text
    - `provider_used`: Which provider generated it
    - `grounding`: Grounding analysis (if enabled)
    - `latency_ms`: Generation latency
    """
    try:
        # Create generation request
        gen_request = GenRequest(
            query=request.query,
            context_chunks=request.context_chunks,
            prompt=request.prompt,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            require_grounding=request.require_grounding,
        )
        
        # Generate response
        gen_response = await manager.generate(gen_request)
        
        if not gen_response.response_text:
            raise HTTPException(
                status_code=500,
                detail="Generation failed - no response produced"
            )
        
        # Build response
        grounding_info = None
        if gen_response.grounding_result:
            grounding_info = GroundingInfo(
                is_grounded=gen_response.grounding_result.is_grounded,
                grounding_score=gen_response.grounding_result.grounding_score,
                source_references=gen_response.grounding_result.source_references,
                issues=gen_response.grounding_result.issues,
                explanation=gen_response.grounding_result.explanation,
            )
        
        return GenerateResponse(
            success=True,
            response=gen_response.response_text,
            provider_used=gen_response.provider_used,
            model_used=gen_response.model_used,
            grounding=grounding_info,
            tokens_used=gen_response.tokens_used,
            latency_ms=gen_response.latency_ms,
            query=request.query,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-grounding")
async def check_grounding(
    request: GroundingCheckRequest,
):
    """
    Check if response is grounded in context.
    
    **Analysis:**
    - Extracts claims from response
    - Maps to source documents
    - Identifies hallucinations
    - Returns grounding score
    
    **Parameters:**
    - `response_text`: Generated response to validate
    - `context_chunks`: Retrieved source documents
    - `query`: Original query (optional, for context)
    
    **Response:**
    - `is_grounded`: Whether response is grounded (≥80%)
    - `grounding_score`: Percentage of claims grounded (0.0-1.0)
    - `source_references`: Source chunks used
    - `issues`: Ungrounded claims detected
    - `explanation`: Analysis summary
    """
    try:
        grounding_engine = get_grounding_engine()
        
        result = grounding_engine.check_grounding(
            response_text=request.response_text,
            context_chunks=request.context_chunks,
            query=request.query or "",
        )
        
        return {
            "success": True,
            **result.to_dict(),
        }
    
    except Exception as e:
        logger.error(f"Grounding check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Provider Management ====================

@router.get("/providers", response_model=ProvidersResponse)
async def list_providers(
    manager: GenerationManager = Depends(get_generation_manager_dep),
):
    """
    List available LLM providers.
    
    **Providers:**
    1. **Mistral (Free Local)**
       - Runs locally via Ollama
       - No internet needed
       - Completely free
       - Good for development
    
    2. **OpenAI (Paid Cloud)**
       - GPT-3.5 and GPT-4
       - Highest quality
       - Requires API key and credits
    
    3. **HuggingFace (Free Cloud)**
       - Multiple open-source models
       - Free tier available
       - Cloud-hosted
    
    4. **Groq (Free/Fast)**
       - Extremely fast inference
       - Free tier available
       - Cloud-hosted
    
    **Setup Instructions:**
    ```bash
    # Mistral (local):
    ollama pull mistral
    ollama serve
    
    # OpenAI (add API key):
    export OPENAI_API_KEY="sk-..."
    
    # HuggingFace (add token):
    export HF_API_KEY="hf_..."
    
    # Groq (add API key):
    export GROQ_API_KEY="..."
    ```
    """
    from src.generation.providers import (
        MistralProvider, OpenAIProvider,
        HuggingFaceProvider, GroqProvider
    )
    
    providers_data = []
    
    # Check each provider
    mistral = MistralProvider()
    providers_data.append(ProviderInfo(
        name=mistral.get_provider_name(),
        provider_type="mistral",
        available=mistral.is_available(),
        model_name=mistral.get_model_name(),
    ))
    
    openai = OpenAIProvider()
    providers_data.append(ProviderInfo(
        name=openai.get_provider_name(),
        provider_type="openai",
        available=openai.is_available(),
        model_name=openai.get_model_name(),
    ))
    
    hf = HuggingFaceProvider()
    providers_data.append(ProviderInfo(
        name=hf.get_provider_name(),
        provider_type="huggingface",
        available=hf.is_available(),
        model_name=hf.get_model_name(),
    ))
    
    groq = GroqProvider()
    providers_data.append(ProviderInfo(
        name=groq.get_provider_name(),
        provider_type="groq",
        available=groq.is_available(),
        model_name=groq.get_model_name(),
    ))
    
    return ProvidersResponse(providers=providers_data)


# ==================== Statistics & Management ====================

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    manager: GenerationManager = Depends(get_generation_manager_dep),
):
    """
    Get generation statistics.
    
    **Metrics:**
    - Total generations processed
    - Success/failure rates
    - Fallback usage count
    - Grounding validation results
    """
    return manager.get_stats()


@router.post("/reset-stats")
async def reset_stats(
    manager: GenerationManager = Depends(get_generation_manager_dep),
):
    """Reset generation statistics."""
    manager.reset_stats()
    logger.info("Generation stats reset via API")
    return {
        "success": True,
        "message": "Statistics reset successfully",
    }


@router.get("/health")
async def health_check(
    manager: GenerationManager = Depends(get_generation_manager_dep),
):
    """
    Check generation pipeline health.
    
    **Returns:**
    - Provider availability
    - Grounding engine status
    - Statistics summary
    - Configuration info
    """
    stats = manager.get_stats()
    grounding_stats = manager.grounding_engine.get_stats()
    
    return {
        "success": True,
        "status": "operational",
        "generation_stats": stats,
        "grounding_stats": grounding_stats,
        "primary_provider": (
            manager.primary_provider.get_provider_name()
            if manager.primary_provider else "None"
        ),
        "fallback_provider": (
            manager.fallback_provider.get_provider_name()
            if manager.fallback_provider else "None"
        ),
    }
