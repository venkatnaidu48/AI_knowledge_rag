"""
Base classes and interfaces for response validation.

This module defines abstract validators and data models for validating
and scoring LLM-generated responses in the RAG pipeline.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class ValidatorType(str, Enum):
    """Enumeration of validator types."""
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    LENGTH = "length"
    GROUNDING = "grounding"
    COMPLETENESS = "completeness"
    TOXICITY = "toxicity"
    CUSTOM = "custom"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a response."""
    validator: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    suggestion: Optional[str] = None
    score_impact: float = 0.0  # How much this impacts overall score (0.0-1.0)


@dataclass
class ValidationResult:
    """Result of validating a response."""
    is_valid: bool
    score: float  # 0.0-1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    validator_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure score is between 0 and 1."""
        self.score = max(0.0, min(1.0, self.score))


class ResponseValidator(ABC):
    """Abstract base class for response validators."""
    
    @abstractmethod
    async def validate(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str],
        **kwargs
    ) -> ValidationResult:
        """
        Validate a response.
        
        Args:
            response_text: The response text to validate
            query: The original user query
            context_chunks: The context chunks used to generate response
            **kwargs: Additional validation parameters
            
        Returns:
            ValidationResult with score and issues
        """
        pass
    
    @abstractmethod
    def get_validator_name(self) -> str:
        """Return the name of this validator."""
        pass
    
    @abstractmethod
    def get_validator_type(self) -> ValidatorType:
        """Return the type of this validator."""
        pass
    
    @abstractmethod
    def get_weight(self) -> float:
        """
        Return the weight of this validator in overall scoring.
        
        Returns:
            Weight as float (0.0-1.0). Will be normalized with other weights.
        """
        pass


# Pydantic models for API


class ValidationIssueModel(BaseModel):
    """Pydantic model for validation issues."""
    validator: str = Field(..., description="Name of validator that found issue")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    message: str = Field(..., description="Description of the issue")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing")
    score_impact: float = Field(0.0, description="Impact on overall score (0-1)")


class ValidationResultModel(BaseModel):
    """Pydantic model for validation results."""
    is_valid: bool = Field(..., description="Is response valid")
    score: float = Field(..., description="Overall validation score (0-1)", ge=0, le=1)
    validator_name: str = Field("", description="Name of validator")
    issues: List[ValidationIssueModel] = Field(default_factory=list, description="List of issues")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class ResponseScoreModel(BaseModel):
    """Pydantic model for response scores."""
    response_text: str = Field(..., description="The response being scored")
    query: str = Field(..., description="The original query")
    overall_score: float = Field(..., description="Overall score (0-1)", ge=0, le=1)
    relevance_score: float = Field(0.0, description="Relevance to query", ge=0, le=1)
    coherence_score: float = Field(0.0, description="Response coherence", ge=0, le=1)
    grounding_score: float = Field(0.0, description="Grounding in context", ge=0, le=1)
    completeness_score: float = Field(0.0, description="Question completeness", ge=0, le=1)
    length_appropriate: bool = Field(True, description="Is length appropriate")
    validation_issues: List[ValidationIssueModel] = Field(default_factory=list)
    passed_validation: bool = Field(True, description="Did response pass all validators")


class RankedResponseModel(BaseModel):
    """Pydantic model for ranked response."""
    rank: int = Field(..., description="Rank position (1 = best)")
    score: float = Field(..., description="Overall score (0-1)", ge=0, le=1)
    response_text: str = Field(..., description="The response text")
    issues_count: int = Field(0, description="Number of validation issues")
    critical_issues: bool = Field(False, description="Has critical issues")
    details: Dict[str, Any] = Field(default_factory=dict)


class ConfidenceAssessmentModel(BaseModel):
    """Pydantic model for confidence assessment."""
    confidence_score: float = Field(..., description="Overall confidence (0-1)", ge=0, le=1)
    confidence_level: str = Field(..., description="Level: very_low, low, medium, high, very_high")
    key_factors: List[str] = Field(default_factory=list, description="Factors affecting confidence")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    should_regenerate: bool = Field(False, description="Should regenerate response")
    estimated_accuracy: float = Field(0.0, description="Estimated accuracy (0-1)", ge=0, le=1)


# Configuration models


class ValidatorConfig(BaseModel):
    """Configuration for validators."""
    name: str = Field(..., description="Validator name")
    validator_type: ValidatorType = Field(..., description="Type of validator")
    enabled: bool = Field(True, description="Is validator enabled")
    weight: float = Field(1.0, description="Weight in overall scoring")
    threshold: float = Field(0.5, description="Minimum acceptable score")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Validator-specific parameters")


class ValidationPipelineConfig(BaseModel):
    """Configuration for the validation pipeline."""
    validators: List[ValidatorConfig] = Field(..., description="List of validators")
    overall_threshold: float = Field(0.6, description="Overall validation threshold")
    fail_on_critical: bool = Field(True, description="Fail if critical issues found")
    auto_refine: bool = Field(False, description="Auto-refine low-scoring responses")
    ranking_enabled: bool = Field(True, description="Enable response ranking")
    confidence_calculation: bool = Field(True, description="Calculate confidence scores")
