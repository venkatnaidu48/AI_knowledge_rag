"""
Result Ranking and Filtering Module

Ranks and filters retrieved documents based on relevance,
diversity, and quality metrics.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RankedResult:
    """Ranked document result with scoring"""
    chunk_id: int
    text: str
    source: str
    similarity_score: float
    rank_score: float  # Combined ranking score
    rank_position: int


class ResultRanker:
    """
    Ranks and filters retrieved documents.
    
    Ranking factors:
    - Similarity score (main factor)
    - Source diversity (avoid duplicates)
    - Text quality (length, coherence)
    """
    
    def __init__(
        self,
        similarity_weight: float = 0.7,
        diversity_weight: float = 0.2,
        quality_weight: float = 0.1,
        min_rank_score: float = 0.3,
        enforce_diversity: bool = True,
    ):
        """
        Initialize ranker.
        
        Args:
            similarity_weight: Weight for similarity score
            diversity_weight: Weight for source diversity
            quality_weight: Weight for text quality
            min_rank_score: Minimum ranking score to include
            enforce_diversity: Avoid retrieving from same source multiple times
        """
        self.similarity_weight = similarity_weight
        self.diversity_weight = diversity_weight
        self.quality_weight = quality_weight
        self.min_rank_score = min_rank_score
        self.enforce_diversity = enforce_diversity
        
        # Normalize weights
        total_weight = similarity_weight + diversity_weight + quality_weight
        self.similarity_weight /= total_weight
        self.diversity_weight /= total_weight
        self.quality_weight /= total_weight
    
    def rank(self, results: List) -> List[RankedResult]:
        """
        Rank retrieved documents.
        
        Args:
            results: List of RetrievedDocument
            
        Returns:
            List of RankedResult sorted by rank score
        """
        if not results:
            return []
        
        ranked_results = []
        seen_sources = set()
        
        for result in results:
            # Check source diversity
            if self.enforce_diversity and result.source in seen_sources:
                logger.debug(f"Skipping duplicate source: {result.source}")
                continue
            
            # Calculate component scores
            sim_score = result.similarity_score
            div_score = self._calculate_diversity_score(result.source, seen_sources)
            qual_score = self._calculate_quality_score(result.text)
            
            # Calculate combined rank score
            rank_score = (
                self.similarity_weight * sim_score +
                self.diversity_weight * div_score +
                self.quality_weight * qual_score
            )
            
            # Filter by minimum score
            if rank_score < self.min_rank_score:
                logger.debug(
                    f"Filtered result (score={rank_score:.3f}): "
                    f"{result.source[:50]}..."
                )
                continue
            
            ranked_result = RankedResult(
                chunk_id=result.chunk_id,
                text=result.text,
                source=result.source,
                similarity_score=result.similarity_score,
                rank_score=rank_score,
                rank_position=len(ranked_results) + 1,
            )
            ranked_results.append(ranked_result)
            seen_sources.add(result.source)
        
        logger.info(
            f"Ranked {len(ranked_results)} results "
            f"(input: {len(results)}, filtered: {len(results) - len(ranked_results)})"
        )
        
        return ranked_results
    
    def _calculate_diversity_score(
        self,
        source: str,
        seen_sources: set,
    ) -> float:
        """
        Calculate diversity score (1.0 if source not seen, 0.0 if seen).
        
        Args:
            source: Document source
            seen_sources: Set of already selected sources
            
        Returns:
            Diversity score (0.0-1.0)
        """
        if source not in seen_sources:
            return 1.0
        return 0.0
    
    def _calculate_quality_score(self, text: str) -> float:
        """
        Calculate text quality score based on length and structure.
        
        Heuristics:
        - Ideal length: 200-500 characters
        - Too short: likely not meaningful
        - Too long: likely noise or multiple topics
        
        Args:
            text: Document text
            
        Returns:
            Quality score (0.0-1.0)
        """
        text_len = len(text.strip())
        
        # Too short
        if text_len < 50:
            return 0.1
        
        # Too long
        if text_len > 1000:
            return 0.7
        
        # Ideal range
        if 200 <= text_len <= 500:
            return 1.0
        
        # Linear interpolation for other ranges
        if text_len < 200:
            return 0.5 + (text_len - 50) / 300 * 0.5
        else:  # 500 < text_len < 1000
            return 1.0 - (text_len - 500) / 500 * 0.3
    
    def rerank_by_relevance(
        self,
        results: List[RankedResult],
        query: str,
        relevance_calculator=None,
    ) -> List[RankedResult]:
        """
        Re-rank results based on additional relevance calculation.
        
        Args:
            results: List of RankedResult
            query: Original query (for context)
            relevance_calculator: Optional callable for custom relevance scoring
            
        Returns:
            Re-ranked results
        """
        if not results or not relevance_calculator:
            return results
        
        try:
            # Calculate additional relevance scores
            for result in results:
                additional_score = relevance_calculator(query, result.text)
                result.rank_score = (result.rank_score * 0.7) + (additional_score * 0.3)
            
            # Re-sort by new rank score
            results.sort(key=lambda x: x.rank_score, reverse=True)
            
            # Update rank positions
            for i, result in enumerate(results, 1):
                result.rank_position = i
            
            logger.info("Re-ranked results based on custom relevance")
            return results
            
        except Exception as e:
            logger.error(f"Error in re-ranking: {e}")
            return results
    
    def get_top_k(self, results: List[RankedResult], k: int = 5) -> List[RankedResult]:
        """
        Get top K results.
        
        Args:
            results: Ranked results
            k: Number of top results
            
        Returns:
            Top K results
        """
        return results[:k]
    
    def filter_by_threshold(
        self,
        results: List[RankedResult],
        threshold: float,
    ) -> List[RankedResult]:
        """
        Filter results by score threshold.
        
        Args:
            results: Ranked results
            threshold: Minimum rank score
            
        Returns:
            Filtered results
        """
        filtered = [r for r in results if r.rank_score >= threshold]
        logger.info(
            f"Filtered by threshold {threshold}: {len(filtered)}/{len(results)} results"
        )
        return filtered
    
    @staticmethod
    def get_ranking_stats(results: List[RankedResult]) -> Dict:
        """Get statistics about ranking results."""
        if not results:
            return {}
        
        scores = [r.rank_score for r in results]
        return {
            "total_results": len(results),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "unique_sources": len(set(r.source for r in results)),
        }
