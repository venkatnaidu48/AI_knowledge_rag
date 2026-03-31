"""
REST API routes for response validation endpoints.

Provides endpoints for validating responses, ranking, confidence assessment,
and managing the validation pipeline.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from src.validation.manager import ValidationManager, get_validation_manager
from src.validation.base import (
    ResponseScoreModel,
    RankedResponseModel,
    ConfidenceAssessmentModel,
    ValidationIssueModel
)
from src.database import SessionLocal
from sqlalchemy.orm import Session


# Pydantic models for API requests/responses

class ValidationChunk(BaseModel):
    """Represents a context chunk."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk content")
    metadata: dict = Field(default_factory=dict, description="Chunk metadata")


class ValidateSingleRequest(BaseModel):
    """Request to validate a single response."""
    response_text: str = Field(..., description="Response to validate")
    query: str = Field(..., description="Original query")
    context_chunks: List[str] = Field(..., description="Context used for generation")


class ValidateSingleResponse(BaseModel):
    """Response from single validation."""
    success: bool = Field(True, description="Was validation successful")
    validation_result: ResponseScoreModel = Field(..., description="Validation result")
    timestamp: str = Field(..., description="ISO timestamp")


class ValidateMultipleRequest(BaseModel):
    """Request to validate multiple responses."""
    responses: List[str] = Field(..., description="List of responses to validate")
    query: str = Field(..., description="Original query")
    context_chunks: List[str] = Field(..., description="Context used for generation")


class ValidateMultipleResponse(BaseModel):
    """Response from multiple validation."""
    success: bool = Field(True, description="Was validation successful")
    validations: List[ResponseScoreModel] = Field(..., description="Validation results")
    total_validated: int = Field(..., description="Number of responses validated")
    passed: int = Field(..., description="Number passed validation")
    failed: int = Field(..., description="Number failed validation")
    pass_rate: float = Field(..., description="Pass rate (0-1)", ge=0, le=1)
    timestamp: str = Field(..., description="ISO timestamp")


class RankResponsesRequest(BaseModel):
    """Request to rank responses."""
    responses: List[str] = Field(..., description="Responses to rank")
    query: str = Field(..., description="Original query")
    context_chunks: List[str] = Field(..., description="Context used for generation")
    top_k: Optional[int] = Field(None, description="Return top K responses")


class RankResponsesResponse(BaseModel):
    """Response from ranking."""
    success: bool = Field(True, description="Was ranking successful")
    ranked_responses: List[RankedResponseModel] = Field(..., description="Ranked responses (best first)")
    best_response: Optional[str] = Field(None, description="Best response text if passed threshold")
    total_ranked: int = Field(..., description="Total responses ranked")
    timestamp: str = Field(..., description="ISO timestamp")


class SelectBestRequest(BaseModel):
    """Request to select best response."""
    responses: List[str] = Field(..., description="Responses to evaluate")
    query: str = Field(..., description="Original query")
    context_chunks: List[str] = Field(..., description="Context used for generation")


class SelectBestResponse(BaseModel):
    """Response from best selection."""
    success: bool = Field(True, description="Selection successful")
    best_response: Optional[str] = Field(None, description="Selected best response")
    best_rank: Optional[RankedResponseModel] = Field(None, description="Ranking info")
    alternative_responses: List[RankedResponseModel] = Field(default_factory=list)
    message: str = Field(..., description="Selection result message")
    timestamp: str = Field(..., description="ISO timestamp")


class ConfidenceRequest(BaseModel):
    """Request to get confidence assessment."""
    response_text: str = Field(..., description="Response to assess")
    query: str = Field(..., description="Original query")
    context_chunks: List[str] = Field(..., description="Context used for generation")


class ConfidenceResponse(BaseModel):
    """Response with confidence assessment."""
    success: bool = Field(True, description="Assessment successful")
    assessment: ConfidenceAssessmentModel = Field(..., description="Confidence assessment")
    timestamp: str = Field(..., description="ISO timestamp")


class CompareResponsesRequest(BaseModel):
    """Request to compare responses."""
    responses: List[str] = Field(..., description="Responses to compare")
    query: str = Field(..., description="Original query")
    context_chunks: List[str] = Field(..., description="Context used for generation")


class CompareResponsesResponse(BaseModel):
    """Response from comparison."""
    success: bool = Field(True, description="Comparison successful")
    comparison: dict = Field(..., description="Comparison analysis")
    timestamp: str = Field(..., description="ISO timestamp")


class StatsResponse(BaseModel):
    """Response with validation statistics."""
    success: bool = Field(True, description="Stats retrieved successfully")
    stats: dict = Field(..., description="Validation statistics")
    timestamp: str = Field(..., description="ISO timestamp")


class HealthCheckResponse(BaseModel):
    """Response from health check."""
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    validators_active: int = Field(..., description="Number of active validators")
    total_validations: int = Field(..., description="Total validations run")
    average_score: float = Field(..., description="Average validation score")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="ISO timestamp")


# Dependency injection

def get_validation_manager_dep() -> ValidationManager:
    """FastAPI dependency to get validation manager."""
    return get_validation_manager()


def get_database_session():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create router

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


# Endpoints


@router.post("/validate-single", response_model=ValidateSingleResponse)
async def validate_single_response(
    request: ValidateSingleRequest,
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Validate a single response.
    
    Checks the response against multiple validators including:
    - Relevance to query
    - Coherence and readability
    - Appropriate length
    - Grounding in context
    - Completeness
    
    Returns validation score (0-1) and any issues found.
    """
    try:
        from datetime import datetime
        
        result = await manager.validate_response(
            response_text=request.response_text,
            query=request.query,
            context_chunks=request.context_chunks
        )
        
        return ValidateSingleResponse(
            success=True,
            validation_result=result,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-multiple", response_model=ValidateMultipleResponse)
async def validate_multiple_responses(
    request: ValidateMultipleRequest,
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Validate multiple responses.
    
    Validates each response and provides summary statistics.
    
    Returns:
    - Individual validation results
    - Pass/fail counts
    - Overall pass rate
    """
    try:
        from datetime import datetime
        
        results = await manager.validate_responses(
            responses=request.responses,
            query=request.query,
            context_chunks=request.context_chunks
        )
        
        passed = sum(1 for r in results if r.passed_validation)
        total = len(results)
        pass_rate = passed / total if total > 0 else 0.0
        
        return ValidateMultipleResponse(
            success=True,
            validations=results,
            total_validated=total,
            passed=passed,
            failed=total - passed,
            pass_rate=pass_rate,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank-responses", response_model=RankResponsesResponse)
async def rank_responses(
    request: RankResponsesRequest,
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Rank responses by quality score.
    
    Scores and ranks responses from best to worst.
    
    Returns:
    - Ranked responses (best first)
    - Best response if it meets quality threshold
    - Scores and issue counts for each
    """
    try:
        from datetime import datetime
        
        ranked = await manager.rank_responses(
            responses=request.responses,
            query=request.query,
            context_chunks=request.context_chunks,
            top_k=request.top_k
        )
        
        best_response = None
        if ranked and ranked[0].score >= 0.6:
            best_response = ranked[0].response_text
        
        return RankResponsesResponse(
            success=True,
            ranked_responses=ranked,
            best_response=best_response,
            total_ranked=len(ranked),
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/select-best", response_model=SelectBestResponse)
async def select_best_response(
    request: SelectBestRequest,
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Select the best response.
    
    Evaluates responses and returns the best one if it meets quality threshold.
    
    Returns:
    - Selected best response (or None if none meet threshold)
    - Ranking info
    - Alternative responses
    """
    try:
        from datetime import datetime
        
        ranked = await manager.rank_responses(
            responses=request.responses,
            query=request.query,
            context_chunks=request.context_chunks
        )
        
        best = None
        alternatives = []
        message = "No response met quality threshold"
        
        if ranked:
            if ranked[0].score >= 0.6:
                best = ranked[0]
                message = f"Selected best response (score: {ranked[0].score:.1%})"
                alternatives = ranked[1:3] if len(ranked) > 1 else []
            else:
                alternatives = ranked[:3]
                message = f"Best response only scored {ranked[0].score:.1%} - below 60% threshold"
        
        return SelectBestResponse(
            success=True,
            best_response=best.response_text if best else None,
            best_rank=best,
            alternative_responses=alternatives,
            message=message,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confidence-assessment", response_model=ConfidenceResponse)
async def get_confidence_assessment(
    request: ConfidenceRequest,
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Get confidence assessment for a response.
    
    Calculates confidence level and provides recommendations.
    
    Returns:
    - Confidence score (0-1)
    - Confidence level (very_low to very_high)
    - Key factors affecting confidence
    - Recommendations
    - Should regenerate flag
    """
    try:
        from datetime import datetime
        
        assessment = await manager.get_confidence_assessment(
            response_text=request.response_text,
            query=request.query,
            context_chunks=request.context_chunks
        )
        
        return ConfidenceResponse(
            success=True,
            assessment=assessment,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-responses", response_model=CompareResponsesResponse)
async def compare_responses(
    request: CompareResponsesRequest,
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Compare multiple responses.
    
    Analyzes and compares responses, providing statistics and insights.
    
    Returns:
    - Score statistics (average, range, variance)
    - Consistency assessment
    - Recommendations
    """
    try:
        from datetime import datetime
        
        comparison = await manager.compare_responses(
            responses=request.responses,
            query=request.query,
            context_chunks=request.context_chunks
        )
        
        return CompareResponsesResponse(
            success=True,
            comparison=comparison,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_validation_stats(
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Get validation statistics.
    
    Returns overall validation pipeline statistics including:
    - Total validations run
    - Pass/fail counts and rates
    - Average scores
    - Critical issues found
    """
    try:
        from datetime import datetime
        
        stats = manager.get_stats()
        
        return StatsResponse(
            success=True,
            stats=stats,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-stats")
async def reset_stats(
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """Reset validation statistics."""
    try:
        from datetime import datetime
        
        result = manager.reset_stats()
        
        return {
            "success": True,
            "message": result.get("message", "Statistics reset"),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    manager: ValidationManager = Depends(get_validation_manager_dep),
    db: Session = Depends(get_database_session)
):
    """
    Health check for validation pipeline.
    
    Returns:
    - Overall health status
    - Number of active validators
    - Pipeline statistics
    """
    try:
        from datetime import datetime
        
        stats = manager.get_stats()
        
        # Determine health status
        if stats["total_validations"] == 0:
            status = "healthy"
        elif stats["pass_rate"] >= 0.7:
            status = "healthy"
        elif stats["pass_rate"] >= 0.5:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return HealthCheckResponse(
            status=status,
            validators_active=stats["validators_active"],
            total_validations=stats["total_validations"],
            average_score=stats["average_score"],
            message=f"Validation pipeline {status} - {stats['validators_active']} validators active",
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
