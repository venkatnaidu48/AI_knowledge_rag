"""
HALLUCINATION DETECTION & QUALITY ASSESSMENT MODULE
Comprehensive system to detect, assess, and score hallucinations and response quality
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HallucinationScore:
    """Hallucination detection result"""
    risk_level: str  # SAFE, LOW, MEDIUM, HIGH
    risk_percentage: float  # 0-100
    detected_issues: List[str]
    is_safe_to_use: bool
    explanation: str


@dataclass
class QualityScore:
    """Quality assessment result"""
    relevance_score: float  # 0-1
    coherence_score: float  # 0-1
    length_score: float  # 0-1
    grounding_score: float  # 0-1
    confidence_score: float  # 0-1
    overall_score: float  # 0-1
    quality_level: str  # EXCELLENT, GOOD, FAIR, POOR


class HallucinationDetector:
    """
    Detects hallucinations using multiple strategies:
    1. Grounding check (claims in context?)
    2. Keyword overlap analysis
    3. Semantic coherence
    4. Quality threshold comparison
    """
    
    def __init__(self):
        """Initialize hallucination detector"""
        self.hallucination_keywords = {
            "i believe", "i think", "probably", "likely", "might", "could",
            "supposedly", "allegedly", "it seems", "it appears", "possibly",
            "perhaps", "maybe", "somewhat", "kind of", "sort of"
        }
    
    def detect_hallucination(
        self,
        response: str,
        context: str,
        grounding_score: float = 0.0,
        quality_score: float = 0.0,
    ) -> HallucinationScore:
        """
        Comprehensive hallucination detection
        
        Args:
            response: Generated response to check
            context: Retrieved context chunks
            grounding_score: Score from grounding engine (0-1)
            quality_score: Overall quality score (0-1)
        
        Returns:
            HallucinationScore with risk assessment
        """
        issues = []
        risk_factors = []
        
        # Check 1: Grounding verification
        grounding_risk = self._check_grounding(response, context, grounding_score)
        if grounding_risk["risk"] > 0:
            issues.append(grounding_risk["issue"])
            risk_factors.append(grounding_risk["risk"])
        
        # Check 2: Uncertainty language detection
        uncertainty_risk = self._check_uncertainty_language(response)
        if uncertainty_risk["risk"] > 0:
            issues.append(uncertainty_risk["issue"])
            risk_factors.append(uncertainty_risk["risk"])
        
        # Check 3: Claim verification
        claim_risk = self._check_unverified_claims(response, context)
        if claim_risk["risk"] > 0:
            issues.append(claim_risk["issue"])
            risk_factors.append(claim_risk["risk"])
        
        # Check 4: Quality consistency
        quality_risk = self._check_quality(quality_score)
        if quality_risk["risk"] > 0:
            issues.append(quality_risk["issue"])
            risk_factors.append(quality_risk["risk"])
        
        # Calculate overall hallucination risk
        if risk_factors:
            avg_risk = sum(risk_factors) / len(risk_factors)
        else:
            avg_risk = 0.0
        
        # Determine risk level
        risk_level, risk_percentage = self._determine_risk_level(avg_risk)
        is_safe = risk_level in ["SAFE", "LOW"]
        
        explanation = self._build_explanation(risk_level, issues)
        
        logger.info(
            f"Hallucination assessment: {risk_level} "
            f"({risk_percentage:.0f}% risk, {len(issues)} issues detected)"
        )
        
        return HallucinationScore(
            risk_level=risk_level,
            risk_percentage=risk_percentage,
            detected_issues=issues,
            is_safe_to_use=is_safe,
            explanation=explanation,
        )
    
    def _check_grounding(
        self,
        response: str,
        context: str,
        grounding_score: float,
    ) -> Dict:
        """Check if response is grounded in context"""
        
        # If grounding engine already checked it
        if grounding_score >= 0.75:
            return {"risk": 0.0, "issue": ""}
        elif grounding_score >= 0.5:
            return {
                "risk": 0.3,
                "issue": f"Response only {grounding_score*100:.0f}% grounded in context (threshold: 75%)"
            }
        else:
            return {
                "risk": 0.7,
                "issue": f"Response poorly grounded in context ({grounding_score*100:.0f}% grounding)"
            }
    
    def _check_uncertainty_language(self, response: str) -> Dict:
        """Detect uncertainty language that may indicate hallucination"""
        
        response_lower = response.lower()
        uncertainty_count = 0
        
        for keyword in self.hallucination_keywords:
            uncertainty_count += response_lower.count(keyword)
        
        if uncertainty_count == 0:
            return {"risk": 0.0, "issue": ""}
        elif uncertainty_count <= 2:
            return {
                "risk": 0.2,
                "issue": f"Response contains {uncertainty_count} uncertainty phrases"
            }
        else:
            return {
                "risk": 0.5,
                "issue": f"Response contains {uncertainty_count} uncertainty phrases (likely unconfident)"
            }
    
    def _check_unverified_claims(self, response: str, context: str) -> Dict:
        """Check for claims not verified in context"""
        
        # Extract numbers and specific claims
        response_words = set(response.lower().split())
        context_words = set(context.lower().split())
        
        # Calculate keyword overlap
        overlap = len(response_words & context_words)
        total_response_words = len(response_words)
        
        if total_response_words == 0:
            return {"risk": 0.0, "issue": ""}
        
        overlap_ratio = overlap / total_response_words
        
        if overlap_ratio >= 0.6:
            return {"risk": 0.0, "issue": ""}
        elif overlap_ratio >= 0.4:
            return {
                "risk": 0.25,
                "issue": f"Only {overlap_ratio*100:.0f}% of response keywords found in context"
            }
        else:
            return {
                "risk": 0.6,
                "issue": f"Only {overlap_ratio*100:.0f}% of response keywords in context (potential hallucination)"
            }
    
    def _check_quality(self, quality_score: float) -> Dict:
        """Check quality consistency"""
        
        if quality_score >= 0.75:
            return {"risk": 0.0, "issue": ""}
        elif quality_score >= 0.60:
            return {
                "risk": 0.2,
                "issue": f"Low quality score ({quality_score:.2f}) may indicate poor grounding"
            }
        else:
            return {
                "risk": 0.4,
                "issue": f"Very low quality score ({quality_score:.2f}), high hallucination risk"
            }
    
    def _determine_risk_level(self, avg_risk: float) -> Tuple[str, float]:
        """Determine hallucination risk level"""
        
        risk_percentage = avg_risk * 100
        
        if avg_risk < 0.05:
            return "✅ SAFE", risk_percentage
        elif avg_risk < 0.25:
            return "🟢 LOW", risk_percentage
        elif avg_risk < 0.60:
            return "🟡 MEDIUM", risk_percentage
        else:
            return "🔴 HIGH", risk_percentage
    
    def _build_explanation(self, risk_level: str, issues: List[str]) -> str:
        """Build human-readable explanation"""
        
        if not issues:
            return "Response appears well-grounded in provided context with no detected hallucinations."
        
        explanation = f"Risk level: {risk_level}. "
        explanation += "Issues detected: " + "; ".join(issues)
        
        return explanation


class QualityAssessor:
    """
    Assesses response quality using validators
    Integrates with ResponseValidators to provide comprehensive scoring
    """
    
    def __init__(self):
        """Initialize quality assessor"""
        from src.response_validators import ResponseValidators
        self.validators = ResponseValidators()
    
    def assess_quality(
        self,
        query: str,
        response: str,
        context: str,
    ) -> QualityScore:
        """
        Assess response quality using all validators
        
        Args:
            query: Original user query
            response: Generated response
            context: Retrieved context
        
        Returns:
            QualityScore with all metrics
        """
        
        try:
            # Run all 5 validators
            relevance = self.validators.validate_relevance(query, response)
            coherence = self.validators.validate_coherence(response)
            length = self.validators.validate_length(response)
            grounding = self.validators.validate_grounding(response, context)
            confidence = self.validators.validate_confidence(response, context)
            
            # Extract scores (0-1)
            relevance_score = relevance.score
            coherence_score = coherence.score
            length_score = length.score
            grounding_score = grounding.score
            confidence_score = confidence.score
            
            # Calculate weighted overall score
            # Grounding is most important (40%), then relevance (30%), coherence (20%), others (10%)
            overall_score = (
                0.40 * grounding_score +
                0.30 * relevance_score +
                0.20 * coherence_score +
                0.05 * length_score +
                0.05 * confidence_score
            )
            
            overall_score = min(1.0, overall_score)
            
            # Determine quality level
            if overall_score >= 0.85:
                quality_level = "✅ EXCELLENT"
            elif overall_score >= 0.70:
                quality_level = "🟢 GOOD"
            elif overall_score >= 0.50:
                quality_level = "🟡 FAIR"
            else:
                quality_level = "🔴 POOR"
            
            logger.info(
                f"Quality assessment: {quality_level} "
                f"(overall: {overall_score:.2f}, "
                f"grounding: {grounding_score:.2f}, "
                f"relevance: {relevance_score:.2f})"
            )
            
            return QualityScore(
                relevance_score=relevance_score,
                coherence_score=coherence_score,
                length_score=length_score,
                grounding_score=grounding_score,
                confidence_score=confidence_score,
                overall_score=overall_score,
                quality_level=quality_level,
            )
        
        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}")
            # Return safe defaults
            return QualityScore(
                relevance_score=0.5,
                coherence_score=0.5,
                length_score=0.5,
                grounding_score=0.5,
                confidence_score=0.5,
                overall_score=0.5,
                quality_level="🟡 UNKNOWN",
            )


# Singleton instances
_detector = None
_assessor = None


def get_hallucination_detector() -> HallucinationDetector:
    """Get hallucination detector singleton"""
    global _detector
    if _detector is None:
        _detector = HallucinationDetector()
    return _detector


def get_quality_assessor() -> QualityAssessor:
    """Get quality assessor singleton"""
    global _assessor
    if _assessor is None:
        _assessor = QualityAssessor()
    return _assessor
