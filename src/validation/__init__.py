"""
Response validation module for RAG pipeline.

This package provides comprehensive response validation with multiple validators,
scoring, ranking, and confidence assessment capabilities.
"""

from src.validation.base import (
    ValidatorType,
    ValidationIssue,
    ValidationResult,
    ResponseValidator,
    ValidationIssueModel,
    ValidationResultModel,
    ResponseScoreModel,
    RankedResponseModel,
    ConfidenceAssessmentModel,
    ValidatorConfig,
    ValidationPipelineConfig
)

from src.validation.validators import (
    RelevanceValidator,
    CoherenceValidator,
    LengthValidator,
    GroundingValidator,
    CompletenessValidator
)

from src.validation.scorer import (
    ScoredResponse,
    ResponseScorer,
    ResponseRanker,
    ConfidenceCalculator
)

from src.validation.manager import (
    ValidationManager,
    get_validation_manager
)

__all__ = [
    # Base classes
    "ValidatorType",
    "ValidationIssue",
    "ValidationResult",
    "ResponseValidator",
    
    # Pydantic models
    "ValidationIssueModel",
    "ValidationResultModel",
    "ResponseScoreModel",
    "RankedResponseModel",
    "ConfidenceAssessmentModel",
    "ValidatorConfig",
    "ValidationPipelineConfig",
    
    # Validators
    "RelevanceValidator",
    "CoherenceValidator",
    "LengthValidator",
    "GroundingValidator",
    "CompletenessValidator",
    
    # Scoring and ranking
    "ScoredResponse",
    "ResponseScorer",
    "ResponseRanker",
    "ConfidenceCalculator",
    
    # Manager
    "ValidationManager",
    "get_validation_manager",
]
