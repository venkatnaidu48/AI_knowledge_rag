"""
Response scoring and ranking system for the validation pipeline.

This module combines multiple validators to produce comprehensive scores
and ranks responses based on quality metrics.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import math

from src.validation.base import (
    ResponseValidator,
    ValidationResult,
    ValidatorConfig,
    ValidationIssueModel,
    ResponseScoreModel,
    RankedResponseModel,
    ConfidenceAssessmentModel
)


@dataclass
class ScoredResponse:
    """Response with computed scores."""
    response_text: str
    query: str
    overall_score: float
    individual_scores: Dict[str, float] = field(default_factory=dict)
    validation_results: List[ValidationResult] = field(default_factory=list)
    issues: List[ValidationIssueModel] = field(default_factory=list)
    critical_issues: bool = False
    
    def to_response_score_model(self) -> ResponseScoreModel:
        """Convert to Pydantic model."""
        return ResponseScoreModel(
            response_text=self.response_text,
            query=self.query,
            overall_score=round(self.overall_score, 3),
            relevance_score=round(self.individual_scores.get('relevance', 0.0), 3),
            coherence_score=round(self.individual_scores.get('coherence', 0.0), 3),
            grounding_score=round(self.individual_scores.get('grounding', 0.0), 3),
            completeness_score=round(self.individual_scores.get('completeness', 0.0), 3),
            length_appropriate=self.individual_scores.get('length', 1.0) > 0.7,
            validation_issues=self.issues,
            passed_validation=not self.critical_issues and self.overall_score >= 0.6
        )


class ResponseScorer:
    """Scores responses using multiple validators."""
    
    def __init__(
        self,
        validators: List[ResponseValidator],
        weights: Optional[Dict[str, float]] = None,
        overall_threshold: float = 0.6
    ):
        """
        Initialize scorer.
        
        Args:
            validators: List of validators to use
            weights: Optional custom weights for validators
            overall_threshold: Minimum acceptable overall score
        """
        self.validators = validators
        self.overall_threshold = overall_threshold
        
        # Compute weights
        if weights:
            self.weights = weights
        else:
            # Use validator's get_weight() method
            self.weights = {
                v.get_validator_name(): v.get_weight()
                for v in validators
            }
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {
                k: v / total_weight
                for k, v in self.weights.items()
            }
    
    async def score_response(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str]
    ) -> ScoredResponse:
        """
        Score a single response.
        
        Args:
            response_text: Response to score
            query: Original query
            context_chunks: Context used for generation
            
        Returns:
            ScoredResponse with scores and issues
        """
        individual_scores = {}
        validation_results = []
        all_issues = []
        critical_issues = False
        
        # Run all validators
        for validator in self.validators:
            try:
                result = await validator.validate(
                    response_text=response_text,
                    query=query,
                    context_chunks=context_chunks
                )
                validation_results.append(result)
                
                validator_name = validator.get_validator_name()
                individual_scores[validator_name.lower().replace(' ', '_')] = result.score
                
                # Collect issues
                for issue in result.issues:
                    all_issues.append(ValidationIssueModel(
                        validator=issue.validator,
                        severity=issue.severity,
                        message=issue.message,
                        suggestion=issue.suggestion,
                        score_impact=issue.score_impact
                    ))
                    
                    if issue.severity == "critical":
                        critical_issues = True
                
            except Exception as e:
                print(f"Error running validator {validator.get_validator_name()}: {e}")
        
        # Calculate overall score
        overall_score = 0.0
        for validator in self.validators:
            validator_name = validator.get_validator_name()
            weight = self.weights.get(validator_name, 0.0)
            score = individual_scores.get(validator_name.lower().replace(' ', '_'), 0.0)
            overall_score += score * weight
        
        return ScoredResponse(
            response_text=response_text,
            query=query,
            overall_score=overall_score,
            individual_scores=individual_scores,
            validation_results=validation_results,
            issues=all_issues,
            critical_issues=critical_issues
        )
    
    async def score_responses(
        self,
        responses: List[str],
        query: str,
        context_chunks: List[str]
    ) -> List[ScoredResponse]:
        """
        Score multiple responses.
        
        Args:
            responses: List of responses to score
            query: Original query
            context_chunks: Context used for generation
            
        Returns:
            List of ScoredResponse objects
        """
        scored_responses = []
        for response in responses:
            scored = await self.score_response(response, query, context_chunks)
            scored_responses.append(scored)
        
        return scored_responses


class ResponseRanker:
    """Ranks responses by quality score."""
    
    @staticmethod
    def rank_responses(
        scored_responses: List[ScoredResponse],
        penalize_critical: bool = True
    ) -> List[RankedResponseModel]:
        """
        Rank responses by score.
        
        Args:
            scored_responses: Scored responses to rank
            penalize_critical: Penalize responses with critical issues
            
        Returns:
            List of ranked responses (best first)
        """
        # Sort by score (descending)
        sorted_responses = sorted(
            scored_responses,
            key=lambda r: r.overall_score,
            reverse=True
        )
        
        # Add penalties for critical issues
        if penalize_critical:
            sorted_responses = sorted(
                sorted_responses,
                key=lambda r: (not r.critical_issues, r.overall_score),
                reverse=True
            )
        
        # Create ranked models
        ranked = []
        for rank, scored in enumerate(sorted_responses, 1):
            ranked.append(RankedResponseModel(
                rank=rank,
                score=round(scored.overall_score, 3),
                response_text=scored.response_text,
                issues_count=len(scored.issues),
                critical_issues=scored.critical_issues,
                details={
                    "validator_scores": {
                        k: round(v, 3)
                        for k, v in scored.individual_scores.items()
                    }
                }
            ))
        
        return ranked
    
    @staticmethod
    def select_best_response(
        ranked_responses: List[RankedResponseModel],
        threshold: float = 0.6
    ) -> Optional[RankedResponseModel]:
        """
        Select the best response that meets threshold.
        
        Args:
            ranked_responses: Ranked response list (best first)
            threshold: Minimum acceptable score
            
        Returns:
            Best response if it meets threshold, else None
        """
        if not ranked_responses:
            return None
        
        best = ranked_responses[0]
        if best.score >= threshold:
            return best
        
        return None


class ConfidenceCalculator:
    """Calculates confidence scores for responses."""
    
    @staticmethod
    def calculate_confidence(
        scored_response: ScoredResponse,
        comparison_score: Optional[float] = None
    ) -> ConfidenceAssessmentModel:
        """
        Calculate confidence in response quality.
        
        Args:
            scored_response: Scored response to assess
            comparison_score: Score of alternative for comparison
            
        Returns:
            ConfidenceAssessmentModel with assessment
        """
        overall_score = scored_response.overall_score
        
        # Determine confidence level
        if overall_score >= 0.85:
            confidence_level = "very_high"
            conf_score = 0.95
        elif overall_score >= 0.75:
            confidence_level = "high"
            conf_score = 0.80
        elif overall_score >= 0.65:
            confidence_level = "medium"
            conf_score = 0.65
        elif overall_score >= 0.50:
            confidence_level = "low"
            conf_score = 0.50
        else:
            confidence_level = "very_low"
            conf_score = 0.25
        
        # Key factors
        key_factors = []
        for name, score in scored_response.individual_scores.items():
            if score >= 0.8:
                key_factors.append(f"Strong {name}: {score:.1%}")
            elif score < 0.5:
                key_factors.append(f"Weak {name}: {score:.1%}")
        
        # Critical issues reduce confidence
        if scored_response.critical_issues:
            conf_score *= 0.6
            confidence_level = "very_low"
            key_factors.append("Critical validation issues detected")
        
        # Recommendations
        recommendations = []
        
        if scored_response.overall_score < 0.6:
            recommendations.append("Response failed validation - consider regenerating")
        
        # Low scores on specific validators
        low_validators = {
            name: score
            for name, score in scored_response.individual_scores.items()
            if score < 0.5
        }
        
        if low_validators:
            recommendations.append(
                f"Address low-scoring areas: {', '.join(low_validators.keys())}"
            )
        
        if len(scored_response.issues) > 3:
            recommendations.append("Address validation issues before use")
        
        # Should regenerate?
        should_regenerate = (
            scored_response.overall_score < 0.5
            or scored_response.critical_issues
            or len([i for i in scored_response.issues if i.severity == "critical"]) > 0
        )
        
        # Estimated accuracy based on grounding
        estimated_accuracy = scored_response.individual_scores.get(
            'grounding_score', overall_score
        )
        
        return ConfidenceAssessmentModel(
            confidence_score=round(min(1.0, conf_score), 3),
            confidence_level=confidence_level,
            key_factors=key_factors,
            recommendations=recommendations,
            should_regenerate=should_regenerate,
            estimated_accuracy=round(estimated_accuracy, 3)
        )
    
    @staticmethod
    def compare_responses(
        scored_responses: List[ScoredResponse]
    ) -> Dict[str, Any]:
        """
        Compare multiple responses and provide insights.
        
        Args:
            scored_responses: List of scored responses
            
        Returns:
            Comparison analysis
        """
        if not scored_responses:
            return {}
        
        scores = [r.overall_score for r in scored_responses]
        avg_score = sum(scores) / len(scores)
        best_score = max(scores)
        worst_score = min(scores)
        
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        std_dev = math.sqrt(variance)
        
        return {
            "response_count": len(scored_responses),
            "average_score": round(avg_score, 3),
            "best_score": round(best_score, 3),
            "worst_score": round(worst_score, 3),
            "score_variance": round(variance, 3),
            "score_std_dev": round(std_dev, 3),
            "score_range": round(best_score - worst_score, 3),
            "recommendation": (
                "Responses are consistent" if std_dev < 0.1
                else "Responses vary significantly - select carefully"
            )
        }
