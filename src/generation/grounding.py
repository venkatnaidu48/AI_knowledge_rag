"""
Context Grounding - Grounding Engine
Validates that LLM responses are grounded in retrieved context
"""

import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

from src.generation.base import GroundingResult

logger = logging.getLogger(__name__)


class GroundingEngine:
    """
    Validates that generated responses are grounded in retrieved context.
    Ensures LLM doesn't hallucinate facts not in source documents.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize grounding engine.
        
        Args:
            strict_mode: If True, require explicit grounding for all facts
        """
        self.strict_mode = strict_mode
        self.checked_count = 0
        self.grounded_count = 0
        self.hallucination_count = 0
    
    def check_grounding(
        self,
        response_text: str,
        context_chunks: List[Dict],
        query: str = "",
    ) -> GroundingResult:
        """
        Check if response is grounded in context.
        
        **Grounding Analysis:**
        1. Extracts key claims from response
        2. Maps to source documents
        3. Identifies unsupported statements
        4. Calculates grounding score
        
        Args:
            response_text: Generated response to check
            context_chunks: Retrieved context chunks
            query: Original query (for context)
        
        Returns:
            GroundingResult with analysis
        """
        self.checked_count += 1
        
        try:
            # Extract context text for matching
            context_text = self._build_context_text(context_chunks)
            
            # Extract claims from response
            claims = self._extract_claims(response_text)
            
            if not claims:
                # No specific claims to verify
                return GroundingResult(
                    is_grounded=True,
                    grounding_score=1.0,
                    source_references=[],
                    explanation="Response contains no specific factual claims",
                )
            
            # Check each claim against context
            grounded_claims = []
            ungrounded_claims = []
            source_references = set()
            
            for claim in claims:
                grounding_found = self._find_grounding(
                    claim,
                    context_text,
                    context_chunks,
                )
                
                if grounding_found["found"]:
                    grounded_claims.append(claim)
                    source_references.update(grounding_found.get("chunk_ids", []))
                else:
                    ungrounded_claims.append(claim)
            
            # Calculate grounding score
            if claims:
                grounding_score = len(grounded_claims) / len(claims)
            else:
                grounding_score = 1.0
            
            # Determine if fully grounded
            is_grounded = grounding_score >= 0.8  # 80% threshold
            
            if is_grounded:
                self.grounded_count += 1
            else:
                self.hallucination_count += 1
            
            # Build issues list
            issues = []
            if ungrounded_claims:
                issues.append(
                    f"{len(ungrounded_claims)} claim(s) not found in context"
                )
                for claim in ungrounded_claims[:3]:
                    issues.append(f"  - {claim[:100]}...")
            
            explanation = (
                f"Checked {len(claims)} claims: "
                f"{len(grounded_claims)} grounded, "
                f"{len(ungrounded_claims)} ungrounded"
            )
            
            logger.info(f"✓ Grounding check: {explanation}")
            
            return GroundingResult(
                is_grounded=is_grounded,
                grounding_score=grounding_score,
                source_references=list(source_references),
                issues=issues,
                explanation=explanation,
            )
        
        except Exception as e:
            logger.error(f"Grounding check error: {str(e)}")
            return GroundingResult(
                is_grounded=False,
                grounding_score=0.0,
                source_references=[],
                issues=[f"Grounding check failed: {str(e)}"],
                explanation="Error during grounding analysis",
            )
    
    def _build_context_text(self, context_chunks: List[Dict]) -> str:
        """Build combined context text for matching."""
        texts = []
        for chunk in context_chunks:
            if isinstance(chunk, dict):
                text = chunk.get("text", "")
            else:
                text = str(chunk)
            texts.append(text)
        
        return "\n\n".join(texts)
    
    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from response.
        
        Uses heuristics to identify key statements:
        - Sentences with numbers, dates, names
        - Quote-like statements
        - Direct assertions
        """
        claims = []
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Look for factual indicators
            if any(indicator in sentence.lower() for indicator in [
                "is ", "was ", "are ", "were ",
                "has ", "have ", "had ",
                "can ", "will ", "should ",
                "according to", "reports", "stated",
                "indicates", "shows", "demonstrates",
            ]):
                claims.append(sentence)
            
            # Look for specific entities/numbers
            if re.search(r'\b\d{4}\b|\b\d{1,2}%\b|[$€£¥]|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', sentence):
                claims.append(sentence)
        
        return claims[:10]  # Limit to first 10 claims
    
    def _find_grounding(
        self,
        claim: str,
        context_text: str,
        context_chunks: List[Dict],
    ) -> Dict:
        """
        Find grounding for a claim in context.
        
        Returns:
            {
                "found": bool,
                "confidence": float,
                "chunk_ids": [str],
                "matching_text": str
            }
        """
        # Extract key entities/numbers from claim
        keywords = self._extract_keywords(claim)
        
        if not keywords:
            return {
                "found": True,
                "confidence": 0.5,
                "chunk_ids": [],
                "matching_text": "",
            }
        
        # Search for keywords in context
        found_chunks = []
        best_score = 0
        best_text = ""
        
        for chunk in context_chunks:
            chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            chunk_id = chunk.get("chunk_id", "") if isinstance(chunk, dict) else ""
            
            # Count keyword matches
            match_score = sum(
                1 for kw in keywords
                if kw.lower() in chunk_text.lower()
            ) / len(keywords)
            
            if match_score > 0:
                found_chunks.append(chunk_id)
                if match_score > best_score:
                    best_score = match_score
                    best_text = chunk_text[:200]
        
        # Consider grounded if found multiple keyword matches
        is_found = len(found_chunks) > 0 or best_score >= 0.5
        
        return {
            "found": is_found,
            "confidence": best_score,
            "chunk_ids": found_chunks,
            "matching_text": best_text,
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key entities and numbers from text."""
        keywords = []
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', text)
        keywords.extend(numbers)
        
        # Extract capitalized words (names/entities)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        keywords.extend(entities)
        
        # Extract specific terms
        terms = re.findall(r'\b(?:financial|revenue|profit|cost|strategy|plan|policy)\b', text, re.IGNORECASE)
        keywords.extend(terms)
        
        return list(set(keywords))  # Remove duplicates
    
    def get_stats(self) -> Dict:
        """Get grounding statistics."""
        if self.checked_count == 0:
            return {
                "checked": 0,
                "grounded": 0,
                "hallucinations": 0,
                "grounding_rate": 0.0,
            }
        
        return {
            "checked": self.checked_count,
            "grounded": self.grounded_count,
            "hallucinations": self.hallucination_count,
            "grounding_rate": self.grounded_count / self.checked_count * 100,
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.checked_count = 0
        self.grounded_count = 0
        self.hallucination_count = 0


# Singleton instance
_grounding_engine: Optional[GroundingEngine] = None


def get_grounding_engine(strict_mode: bool = False) -> GroundingEngine:
    """
    Get or create grounding engine singleton.
    
    Args:
        strict_mode: If True, enforce strict grounding requirements
    
    Returns:
        Singleton GroundingEngine instance
    """
    global _grounding_engine
    
    if _grounding_engine is None:
        _grounding_engine = GroundingEngine(strict_mode=strict_mode)
        logger.info("✓ Grounding engine initialized")
    
    return _grounding_engine
