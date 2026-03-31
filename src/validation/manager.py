"""
Validation pipeline manager for orchestrating response validation.

This module manages the complete validation pipeline including validators,
scoring, ranking, and confidence assessment.
"""

from typing import List, Dict, Optional, Any
from src.validation.base import (
    ResponseValidator,
    ValidatorConfig,
    ValidationPipelineConfig,
    ResponseScoreModel,
    RankedResponseModel,
    ConfidenceAssessmentModel
)
from src.validation.validators import (
    RelevanceValidator,
    CoherenceValidator,
    LengthValidator,
    GroundingValidator,
    CompletenessValidator
)
from src.validation.scorer import (
    ResponseScorer,
    ResponseRanker,
    ConfidenceCalculator,
    ScoredResponse
)


class ValidationManager:
    """Orchestrates the response validation pipeline."""
    
    _instance: Optional['ValidationManager'] = None
    
    def __init__(
        self,
        validators: Optional[List[ResponseValidator]] = None,
        config: Optional[ValidationPipelineConfig] = None
    ):
        """
        Initialize validation manager.
        
        Args:
            validators: List of validators to use (uses defaults if None)
            config: Configuration for pipeline
        """
        # Initialize validators
        if validators:
            self.validators = validators
        else:
            self.validators = self._get_default_validators()
        
        # Store configuration
        self.config = config or ValidationPipelineConfig(
            validators=[
                ValidatorConfig(
                    name="relevance",
                    validator_type="relevance",
                    enabled=True,
                    weight=1.0,
                    threshold=0.5
                ),
                ValidatorConfig(
                    name="coherence",
                    validator_type="coherence",
                    enabled=True,
                    weight=0.8,
                    threshold=0.5
                ),
                ValidatorConfig(
                    name="length",
                    validator_type="length",
                    enabled=True,
                    weight=0.6,
                    threshold=0.5
                ),
                ValidatorConfig(
                    name="grounding",
                    validator_type="grounding",
                    enabled=True,
                    weight=1.2,
                    threshold=0.6
                ),
                ValidatorConfig(
                    name="completeness",
                    validator_type="completeness",
                    enabled=True,
                    weight=0.9,
                    threshold=0.5
                ),
            ],
            overall_threshold=0.6,
            fail_on_critical=True,
            auto_refine=False,
            ranking_enabled=True,
            confidence_calculation=True
        )
        
        # Initialize scorer
        weights = {
            v.get_validator_name(): v.get_weight()
            for v in self.validators
        }
        self.scorer = ResponseScorer(
            validators=self.validators,
            weights=weights,
            overall_threshold=self.config.overall_threshold
        )
        
        # Statistics
        self.stats = {
            "validations_run": 0,
            "responses_passed": 0,
            "responses_failed": 0,
            "avg_score": 0.0,
            "critical_issues_found": 0
        }
    
    @staticmethod
    def _get_default_validators() -> List[ResponseValidator]:
        """Get default validators."""
        return [
            RelevanceValidator(threshold=0.5),
            CoherenceValidator(threshold=0.5),
            LengthValidator(threshold=0.5),
            GroundingValidator(threshold=0.6),
            CompletenessValidator(threshold=0.5),
        ]
    
    async def validate_response(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str]
    ) -> ResponseScoreModel:
        """
        Validate a single response.
        
        Args:
            response_text: Response to validate
            query: Original query
            context_chunks: Context chunks used
            
        Returns:
            ResponseScoreModel with validation results
        """
        scored = await self.scorer.score_response(
            response_text=response_text,
            query=query,
            context_chunks=context_chunks
        )
        
        # Update statistics
        self.stats["validations_run"] += 1
        if scored.overall_score >= self.config.overall_threshold:
            self.stats["responses_passed"] += 1
        else:
            self.stats["responses_failed"] += 1
        
        if scored.critical_issues:
            self.stats["critical_issues_found"] += 1
        
        # Update average score
        prev_avg = self.stats["avg_score"]
        self.stats["avg_score"] = (
            (prev_avg * (self.stats["validations_run"] - 1) + scored.overall_score)
            / self.stats["validations_run"]
        )
        
        return scored.to_response_score_model()
    
    async def validate_responses(
        self,
        responses: List[str],
        query: str,
        context_chunks: List[str]
    ) -> List[ResponseScoreModel]:
        """
        Validate multiple responses.
        
        Args:
            responses: Responses to validate
            query: Original query
            context_chunks: Context chunks used
            
        Returns:
            List of ResponseScoreModel with validation results
        """
        scored_list = await self.scorer.score_responses(
            responses=responses,
            query=query,
            context_chunks=context_chunks
        )
        
        # Update statistics
        for scored in scored_list:
            self.stats["validations_run"] += 1
            if scored.overall_score >= self.config.overall_threshold:
                self.stats["responses_passed"] += 1
            else:
                self.stats["responses_failed"] += 1
            
            if scored.critical_issues:
                self.stats["critical_issues_found"] += 1
        
        # Update average
        total_score = sum(s.overall_score for s in scored_list)
        self.stats["avg_score"] = total_score / len(scored_list) if scored_list else 0.0
        
        return [s.to_response_score_model() for s in scored_list]
    
    async def rank_responses(
        self,
        responses: List[str],
        query: str,
        context_chunks: List[str],
        top_k: Optional[int] = None
    ) -> List[RankedResponseModel]:
        """
        Score and rank multiple responses.
        
        Args:
            responses: Responses to rank
            query: Original query
            context_chunks: Context chunks used
            top_k: Return only top K responses (None = all)
            
        Returns:
            Ranked responses (best first)
        """
        scored_list = await self.scorer.score_responses(
            responses=responses,
            query=query,
            context_chunks=context_chunks
        )
        
        ranked = ResponseRanker.rank_responses(
            scored_list,
            penalize_critical=self.config.fail_on_critical
        )
        
        if top_k:
            ranked = ranked[:top_k]
        
        return ranked
    
    async def select_best_response(
        self,
        responses: List[str],
        query: str,
        context_chunks: List[str]
    ) -> Optional[RankedResponseModel]:
        """
        Select the best response.
        
        Args:
            responses: Responses to evaluate
            query: Original query
            context_chunks: Context chunks used
            
        Returns:
            Best response if it meets threshold, else None
        """
        ranked = await self.rank_responses(
            responses=responses,
            query=query,
            context_chunks=context_chunks,
            top_k=1
        )
        
        if ranked:
            best = ranked[0]
            if best.score >= self.config.overall_threshold:
                return best
        
        return None
    
    async def get_confidence_assessment(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str]
    ) -> ConfidenceAssessmentModel:
        """
        Get confidence assessment for a response.
        
        Args:
            response_text: Response to assess
            query: Original query
            context_chunks: Context chunks used
            
        Returns:
            ConfidenceAssessmentModel with confidence details
        """
        scored = await self.scorer.score_response(
            response_text=response_text,
            query=query,
            context_chunks=context_chunks
        )
        
        return ConfidenceCalculator.calculate_confidence(scored)
    
    async def compare_responses(
        self,
        responses: List[str],
        query: str,
        context_chunks: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple responses.
        
        Args:
            responses: Responses to compare
            query: Original query
            context_chunks: Context chunks used
            
        Returns:
            Comparison analysis
        """
        scored_list = await self.scorer.score_responses(
            responses=responses,
            query=query,
            context_chunks=context_chunks
        )
        
        return ConfidenceCalculator.compare_responses(scored_list)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self.stats["validations_run"]
        passed = self.stats["responses_passed"]
        
        return {
            "total_validations": total,
            "passed": passed,
            "failed": self.stats["responses_failed"],
            "pass_rate": round(passed / total, 3) if total > 0 else 0.0,
            "average_score": round(self.stats["avg_score"], 3),
            "critical_issues_found": self.stats["critical_issues_found"],
            "validators_active": len(self.validators),
            "threshold": self.config.overall_threshold
        }
    
    def reset_stats(self) -> Dict[str, Any]:
        """Reset statistics."""
        self.stats = {
            "validations_run": 0,
            "responses_passed": 0,
            "responses_failed": 0,
            "avg_score": 0.0,
            "critical_issues_found": 0
        }
        return {"message": "Statistics reset"}
    
    @classmethod
    def get_instance(
        cls,
        validators: Optional[List[ResponseValidator]] = None,
        config: Optional[ValidationPipelineConfig] = None
    ) -> 'ValidationManager':
        """
        Get or create singleton instance.
        
        Args:
            validators: Validators to use (only for first call)
            config: Configuration (only for first call)
            
        Returns:
            ValidationManager singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(validators=validators, config=config)
        return cls._instance


def get_validation_manager(
    validators: Optional[List[ResponseValidator]] = None,
    config: Optional[ValidationPipelineConfig] = None
) -> ValidationManager:
    """
    Get validation manager singleton instance.
    
    Args:
        validators: Validators to use (only for first call)
        config: Configuration (only for first call)
        
    Returns:
        ValidationManager instance
    """
    return ValidationManager.get_instance(validators=validators, config=config)
