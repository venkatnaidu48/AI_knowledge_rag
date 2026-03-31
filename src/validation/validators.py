"""
Concrete response validators for assessing response quality.

This module implements various validators for checking response relevance,
coherence, grounding, completeness, and other quality metrics.
"""

import re
from typing import List, Dict, Any
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
import string

from src.validation.base import (
    ResponseValidator,
    ValidationResult,
    ValidationIssue,
    ValidatorType
)


class RelevanceValidator(ResponseValidator):
    """Validates that response is relevant to the query."""
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.min_overlap = 0.2  # Minimum 20% keyword overlap
    
    async def validate(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str],
        **kwargs
    ) -> ValidationResult:
        """Check if response is relevant to the query."""
        try:
            # Extract keywords from query (exclude stopwords)
            stop_words = set(stopwords.words('english'))
            query_words = set(
                word.lower() for word in query.split()
                if word.lower() not in stop_words and len(word) > 3
            )
            
            # Extract keywords from response
            response_words = set(
                word.lower() for word in response_text.split()
                if word.lower() not in stop_words and len(word) > 3
            )
            
            # Calculate overlap
            if query_words:
                overlap = len(query_words & response_words) / len(query_words)
            else:
                overlap = 0.0
            
            # Check if response mentions key entities from query
            query_entities = self._extract_entities(query)
            response_entities = self._extract_entities(response_text)
            entity_overlap = 0.0
            if query_entities:
                entity_overlap = len(set(query_entities) & set(response_entities)) / len(query_entities)
            
            # Combined score
            score = (overlap * 0.6 + entity_overlap * 0.4)
            
            issues = []
            if overlap < self.min_overlap:
                issues.append(ValidationIssue(
                    validator="RelevanceValidator",
                    severity="high",
                    message=f"Low keyword overlap with query ({overlap:.1%})",
                    suggestion="Response may not directly address the query",
                    score_impact=0.2
                ))
            
            is_valid = score >= self.threshold
            
            return ValidationResult(
                is_valid=is_valid,
                score=score,
                issues=issues,
                validator_name="RelevanceValidator",
                details={
                    "keyword_overlap": round(overlap, 3),
                    "entity_overlap": round(entity_overlap, 3),
                    "query_keywords": len(query_words),
                    "response_keywords": len(response_words),
                    "matching_keywords": len(query_words & response_words)
                }
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                issues=[ValidationIssue(
                    validator="RelevanceValidator",
                    severity="medium",
                    message=f"Error checking relevance: {str(e)}"
                )],
                validator_name="RelevanceValidator"
            )
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract capitalized words (potential entities)."""
        words = text.split()
        entities = [w for w in words if w and w[0].isupper() and len(w) > 2]
        return entities
    
    def get_validator_name(self) -> str:
        return "Relevance Validator"
    
    def get_validator_type(self) -> ValidatorType:
        return ValidatorType.RELEVANCE
    
    def get_weight(self) -> float:
        return 1.0


class CoherenceValidator(ResponseValidator):
    """Validates response coherence and readability."""
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
    
    async def validate(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str],
        **kwargs
    ) -> ValidationResult:
        """Check response coherence."""
        try:
            issues = []
            
            # Check 1: Sentence structure
            sentences = sent_tokenize(response_text)
            if len(sentences) == 0:
                return ValidationResult(
                    is_valid=False,
                    score=0.0,
                    issues=[ValidationIssue(
                        validator="CoherenceValidator",
                        severity="critical",
                        message="Response contains no sentences"
                    )],
                    validator_name="CoherenceValidator"
                )
            
            avg_sentence_length = len(response_text.split()) / len(sentences)
            
            if avg_sentence_length < 5:
                issues.append(ValidationIssue(
                    validator="CoherenceValidator",
                    severity="medium",
                    message="Sentences too short (poor coherence)",
                    suggestion="Use more complete sentences",
                    score_impact=0.15
                ))
            
            # Check 2: Spelling and grammar indicators
            # Check for common patterns indicating poor quality
            poor_patterns = [
                (r'\b([a-z])\1{2,}\b', "Repeated characters"),
                (r'\s+', "Multiple spaces"),
                (r'[!?]{2,}', "Multiple punctuation marks"),
            ]
            
            pattern_matches = 0
            for pattern, desc in poor_patterns:
                if re.search(pattern, response_text.lower()):
                    pattern_matches += 1
            
            if pattern_matches > 0:
                issues.append(ValidationIssue(
                    validator="CoherenceValidator",
                    severity="low",
                    message=f"Found {pattern_matches} coherence issues",
                    score_impact=0.1
                ))
            
            # Check 3: Paragraph structure
            paragraphs = response_text.split('\n\n')
            has_structure = len(paragraphs) > 1 or len(response_text) > 200
            
            # Calculate score
            score = 1.0
            score -= 0.1 if not has_structure and len(response_text) > 100 else 0
            score -= pattern_matches * 0.05
            score = max(0.0, score)
            
            is_valid = score >= self.threshold
            
            return ValidationResult(
                is_valid=is_valid,
                score=score,
                issues=issues,
                validator_name="CoherenceValidator",
                details={
                    "sentence_count": len(sentences),
                    "avg_sentence_length": round(avg_sentence_length, 1),
                    "paragraph_count": len(paragraphs),
                    "has_structure": has_structure,
                    "pattern_issues": pattern_matches
                }
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                score=0.5,
                issues=[ValidationIssue(
                    validator="CoherenceValidator",
                    severity="medium",
                    message=f"Error checking coherence: {str(e)}"
                )],
                validator_name="CoherenceValidator"
            )
    
    def get_validator_name(self) -> str:
        return "Coherence Validator"
    
    def get_validator_type(self) -> ValidatorType:
        return ValidatorType.COHERENCE
    
    def get_weight(self) -> float:
        return 0.8


class LengthValidator(ResponseValidator):
    """Validates that response length is appropriate."""
    
    def __init__(self, min_words: int = 20, max_words: int = 1000, threshold: float = 0.5):
        self.min_words = min_words
        self.max_words = max_words
        self.threshold = threshold
    
    async def validate(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str],
        **kwargs
    ) -> ValidationResult:
        """Check response length."""
        try:
            word_count = len(response_text.split())
            issues = []
            
            if word_count < self.min_words:
                issues.append(ValidationIssue(
                    validator="LengthValidator",
                    severity="high",
                    message=f"Response too short ({word_count} words < {self.min_words} minimum)",
                    suggestion="Provide a more detailed response",
                    score_impact=0.3
                ))
            
            if word_count > self.max_words:
                issues.append(ValidationIssue(
                    validator="LengthValidator",
                    severity="medium",
                    message=f"Response too long ({word_count} words > {self.max_words} maximum)",
                    suggestion="Condense the response",
                    score_impact=0.2
                ))
            
            # Calculate score based on optimal range
            optimal_min = self.min_words
            optimal_max = self.max_words * 0.8
            
            if optimal_min <= word_count <= optimal_max:
                score = 1.0
            elif word_count < optimal_min:
                score = max(0.0, word_count / optimal_min)
            else:
                score = max(0.0, 1.0 - (word_count - optimal_max) / (self.max_words - optimal_max))
            
            is_valid = score >= self.threshold and len(issues) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                score=score,
                issues=issues,
                validator_name="LengthValidator",
                details={
                    "word_count": word_count,
                    "character_count": len(response_text),
                    "min_words": self.min_words,
                    "max_words": self.max_words,
                    "in_optimal_range": optimal_min <= word_count <= optimal_max
                }
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                issues=[ValidationIssue(
                    validator="LengthValidator",
                    severity="medium",
                    message=f"Error checking length: {str(e)}"
                )],
                validator_name="LengthValidator"
            )
    
    def get_validator_name(self) -> str:
        return "Length Validator"
    
    def get_validator_type(self) -> ValidatorType:
        return ValidatorType.LENGTH
    
    def get_weight(self) -> float:
        return 0.6


class GroundingValidator(ResponseValidator):
    """Validates that response is grounded in provided context."""
    
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
    
    async def validate(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str],
        **kwargs
    ) -> ValidationResult:
        """Check if response is grounded in context."""
        try:
            if not context_chunks:
                return ValidationResult(
                    is_valid=True,  # Can't verify without context
                    score=0.8,
                    validator_name="GroundingValidator",
                    details={"no_context": True}
                )
            
            issues = []
            
            # Extract key factual claims from response
            response_sentences = sent_tokenize(response_text)
            context_text = " ".join(context_chunks).lower()
            
            grounded_sentences = 0
            suspicious_claims = []
            
            for sentence in response_sentences:
                # Extract key terms (non-stopwords, length > 3)
                stop_words = set(stopwords.words('english'))
                key_terms = [
                    w.lower() for w in sentence.split()
                    if w.lower() not in stop_words and len(w) > 3
                ]
                
                # Check if key terms appear in context
                matches = sum(1 for term in key_terms if term in context_text)
                
                if key_terms and matches / len(key_terms) >= 0.3:
                    grounded_sentences += 1
                elif key_terms and matches / len(key_terms) < 0.2:
                    suspicious_claims.append(sentence[:100])
            
            # Calculate grounding score
            if len(response_sentences) > 0:
                score = grounded_sentences / len(response_sentences)
            else:
                score = 0.0
            
            if suspicious_claims:
                issues.append(ValidationIssue(
                    validator="GroundingValidator",
                    severity="high",
                    message=f"Found {len(suspicious_claims)} potentially ungrounded claims",
                    suggestion="Verify claims are supported by context",
                    score_impact=0.25
                ))
            
            is_valid = score >= self.threshold
            
            return ValidationResult(
                is_valid=is_valid,
                score=score,
                issues=issues,
                validator_name="GroundingValidator",
                details={
                    "grounded_sentences": grounded_sentences,
                    "total_sentences": len(response_sentences),
                    "grounding_ratio": round(score, 3),
                    "ungrounded_claims": len(suspicious_claims)
                }
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                issues=[ValidationIssue(
                    validator="GroundingValidator",
                    severity="medium",
                    message=f"Error checking grounding: {str(e)}"
                )],
                validator_name="GroundingValidator"
            )
    
    def get_validator_name(self) -> str:
        return "Grounding Validator"
    
    def get_validator_type(self) -> ValidatorType:
        return ValidatorType.GROUNDING
    
    def get_weight(self) -> float:
        return 1.2  # Higher weight for grounding


class CompletenessValidator(ResponseValidator):
    """Validates that response answers all aspects of the query."""
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
    
    async def validate(
        self,
        response_text: str,
        query: str,
        context_chunks: List[str],
        **kwargs
    ) -> ValidationResult:
        """Check if response is complete."""
        try:
            issues = []
            
            # Extract question aspects from query
            # Look for question words: what, why, how, when, where, who
            question_indicators = ['what', 'why', 'how', 'when', 'where', 'who', 'which']
            query_lower = query.lower()
            
            aspects = []
            for indicator in question_indicators:
                if indicator in query_lower:
                    aspects.append(indicator)
            
            if not aspects:
                # Not a specific question, assume completeness
                return ValidationResult(
                    is_valid=True,
                    score=0.9,
                    validator_name="CompletenessValidator",
                    details={"not_a_question": True}
                )
            
            # Check if response addresses each aspect
            response_lower = response_text.lower()
            addressed_aspects = []
            
            aspect_keywords = {
                'what': ['what', 'is', 'are', 'definition'],
                'why': ['because', 'reason', 'cause', 'due to'],
                'how': ['how', 'process', 'steps', 'method'],
                'when': ['when', 'time', 'date', 'year'],
                'where': ['where', 'location', 'place', 'site'],
                'who': ['who', 'person', 'organization', 'company']
            }
            
            for aspect in aspects:
                keywords = aspect_keywords.get(aspect, [aspect])
                if any(kw in response_lower for kw in keywords):
                    addressed_aspects.append(aspect)
            
            # Calculate completeness score
            if len(aspects) > 0:
                score = len(addressed_aspects) / len(aspects)
            else:
                score = 0.5
            
            if len(addressed_aspects) < len(aspects):
                missing = [a for a in aspects if a not in addressed_aspects]
                issues.append(ValidationIssue(
                    validator="CompletenessValidator",
                    severity="medium",
                    message=f"Response may not address all aspects: {', '.join(missing)}",
                    suggestion="Ensure response covers all question aspects",
                    score_impact=0.15
                ))
            
            is_valid = score >= self.threshold
            
            return ValidationResult(
                is_valid=is_valid,
                score=score,
                issues=issues,
                validator_name="CompletenessValidator",
                details={
                    "question_aspects": aspects,
                    "addressed_aspects": addressed_aspects,
                    "completeness_ratio": round(score, 3)
                }
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                score=0.5,
                issues=[ValidationIssue(
                    validator="CompletenessValidator",
                    severity="medium",
                    message=f"Error checking completeness: {str(e)}"
                )],
                validator_name="CompletenessValidator"
            )
    
    def get_validator_name(self) -> str:
        return "Completeness Validator"
    
    def get_validator_type(self) -> ValidatorType:
        return ValidatorType.COMPLETENESS
    
    def get_weight(self) -> float:
        return 0.9
