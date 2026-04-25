"""
Multi-Gate Quality Filtering Pipeline
Ensures only high-quality chunks are embedded and used for retrieval.

Three-gate system:
1. Content Validation: Length, encoding, language
2. Semantic Quality: No gibberish, coherence, diversity
3. Quality Ranking: Composite scoring and importance assessment
"""

import logging
import re
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Quality assessment report"""
    chunk_id: str
    passed: bool
    gate1_result: bool
    gate2_result: bool
    gate3_score: float
    issues: List[str]
    recommendations: List[str]
    confidence: float


class QualityFilteringPipeline:
    """
    Multi-stage quality filtering for chunks.
    
    Ensures consistency, removes garbage, identifies high-value chunks.
    """
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    # Gate 1: Content Validation Thresholds
    MIN_LENGTH = 50  # Minimum characters
    MAX_LENGTH = 10000  # Maximum characters
    MIN_LANGUAGE_CONFIDENCE = 0.5  # Language detection confidence
    
    # Gate 2: Semantic Quality Thresholds
    MIN_UNIQUE_WORDS = 5
    MAX_SPECIAL_CHAR_RATIO = 0.3  # Special characters
    MAX_REPEATED_CHAR_STREAK = 10  # e.g., "aaaaaaaaaa"
    MIN_COHERENCE_SCORE = 0.3
    MIN_QUALITY_SCORE = 0.4
    MAX_ENTROPY_RATIO = 0.9  # Too random = gibberish
    
    # Gate 3: Ranking Configuration
    QUALITY_WEIGHT = 0.40
    COHERENCE_WEIGHT = 0.30
    COMPLETENESS_WEIGHT = 0.20
    IMPORTANCE_WEIGHT = 0.10
    
    # Quality tiers
    EXCELLENT_THRESHOLD = 0.85
    GOOD_THRESHOLD = 0.70
    FAIR_THRESHOLD = 0.50
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize pipeline.
        
        Args:
            strict_mode: If True, use stricter thresholds
        """
        self.strict_mode = strict_mode
        
        if strict_mode:
            self.MIN_LENGTH = 100
            self.MIN_UNIQUE_WORDS = 10
            self.MIN_COHERENCE_SCORE = 0.5
            self.MIN_QUALITY_SCORE = 0.5
    
    # ========================================================================
    # MAIN FILTERING PIPELINE
    # ========================================================================
    
    def filter_chunks(
        self,
        chunks_with_metadata: List[Tuple[str, 'ChunkMetadata']],
        remove_failed: bool = True,
        flag_low_quality: bool = True,
    ) -> Tuple[List[Tuple[str, 'ChunkMetadata']], List[QualityReport]]:
        """
        Run quality filtering on chunks.
        
        Args:
            chunks_with_metadata: List of (text, metadata) tuples
            remove_failed: If True, remove chunks that fail Gate 1 & 2
            flag_low_quality: If True, flag chunks below quality thresholds
            
        Returns:
            (filtered_chunks, quality_reports)
        """
        reports = []
        filtered_chunks = []
        
        for chunk_text, metadata in chunks_with_metadata:
            report = self.assess_chunk_quality(chunk_text, metadata)
            reports.append(report)
            
            # Decide whether to keep chunk
            keep_chunk = True
            
            if remove_failed and not report.passed and report.gate1_result == False:
                keep_chunk = False  # Failed mandatory gate
            
            if keep_chunk:
                filtered_chunks.append((chunk_text, metadata))
        
        logger.info(
            f"Quality filtering complete: {len(chunks_with_metadata)} → "
            f"{len(filtered_chunks)} chunks retained"
        )
        
        return filtered_chunks, reports
    
    def assess_chunk_quality(
        self,
        chunk_text: str,
        metadata: 'ChunkMetadata',
    ) -> QualityReport:
        """
        Assess chunk quality through all gates.
        
        Args:
            chunk_text: Text content of chunk
            metadata: Chunk metadata object
            
        Returns:
            QualityReport with assessment results
        """
        issues = []
        recommendations = []
        
        # Gate 1: Content Validation
        gate1_result, gate1_issues, gate1_recs = self.gate1_content_validation(
            chunk_text, metadata
        )
        issues.extend(gate1_issues)
        recommendations.extend(gate1_recs)
        
        # Gate 2: Semantic Quality
        gate2_result, gate2_issues, gate2_recs = self.gate2_semantic_quality(
            chunk_text, metadata
        )
        issues.extend(gate2_issues)
        recommendations.extend(gate2_recs)
        
        # Gate 3: Quality Ranking
        gate3_score, gate3_issues = self.gate3_quality_ranking(chunk_text, metadata)
        issues.extend(gate3_issues)
        
        # Overall result
        passed = gate1_result  # Must pass Gate 1
        if gate2_result == False:
            passed = False  # Should pass Gate 2
        
        # Calculate confidence (based on scores and issues)
        confidence = 1.0 - (len(issues) * 0.1)  # Each issue reduces confidence
        confidence = max(0.0, min(1.0, confidence))
        
        return QualityReport(
            chunk_id=metadata.chunk_id,
            passed=passed,
            gate1_result=gate1_result,
            gate2_result=gate2_result,
            gate3_score=gate3_score,
            issues=issues,
            recommendations=recommendations,
            confidence=confidence,
        )
    
    # ========================================================================
    # GATE 1: CONTENT VALIDATION (MANDATORY)
    # ========================================================================
    
    def gate1_content_validation(
        self,
        chunk_text: str,
        metadata: 'ChunkMetadata',
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Gate 1: Basic content validation.
        Checks: length, encoding, language, information content
        
        Returns:
            (passed, issues, recommendations)
        """
        issues = []
        recommendations = []
        
        # 1. Length validation
        text_len = len(chunk_text)
        if text_len < self.MIN_LENGTH:
            issues.append(f"Too short: {text_len} < {self.MIN_LENGTH} chars")
            recommendations.append("Combine with adjacent chunks or increase chunk size")
        
        if text_len > self.MAX_LENGTH:
            issues.append(f"Too long: {text_len} > {self.MAX_LENGTH} chars")
            recommendations.append("Split into smaller chunks")
        
        # 2. Encoding validation
        try:
            chunk_text.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError:
            issues.append("Invalid UTF-8 encoding")
            recommendations.append("Re-extract with proper encoding handling")
        
        # 3. Language confidence
        if metadata.language_confidence < self.MIN_LANGUAGE_CONFIDENCE:
            issues.append(
                f"Low language confidence: {metadata.language_confidence:.2f} "
                f"< {self.MIN_LANGUAGE_CONFIDENCE}"
            )
            recommendations.append("May be OCR-extracted or corrupted text")
        
        # 4. Minimum information content
        if metadata.entity_count == 0 and not metadata.contains_numbers:
            if len(chunk_text.split()) < 10:
                issues.append("Minimal information content (no entities or numbers)")
                recommendations.append("Consider removing or combining with context")
        
        # 5. Character diversity (not all same character)
        if len(set(chunk_text)) < 5:
            issues.append("Very low character diversity")
            recommendations.append("Likely corrupted or placeholder text")
        
        # Determine pass/fail
        passed = len(issues) == 0
        
        return passed, issues, recommendations
    
    # ========================================================================
    # GATE 2: SEMANTIC QUALITY (IMPORTANT)
    # ========================================================================
    
    def gate2_semantic_quality(
        self,
        chunk_text: str,
        metadata: 'ChunkMetadata',
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Gate 2: Semantic quality checks.
        Checks: gibberish, coherence, diversity, readability
        
        Returns:
            (passed, issues, recommendations)
        """
        issues = []
        recommendations = []
        
        # 1. Gibberish detection (repeated characters)
        if re.search(rf'(.)\1{{{self.MAX_REPEATED_CHAR_STREAK},}}', chunk_text):
            issues.append(f"Excessive character repetition (>{self.MAX_REPEATED_CHAR_STREAK})")
            recommendations.append("Likely corrupted text")
        
        # 2. Special character ratio
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s.!?,\-\(\)\[\]]', chunk_text))
        special_ratio = special_chars / max(len(chunk_text), 1)
        
        if special_ratio > self.MAX_SPECIAL_CHAR_RATIO:
            issues.append(f"High special character ratio: {special_ratio:.1%}")
            recommendations.append("May be formatted/markup-heavy text")
        
        # 3. Minimum unique words
        unique_words = len(set(chunk_text.lower().split()))
        if unique_words < self.MIN_UNIQUE_WORDS:
            issues.append(f"Too few unique words: {unique_words} < {self.MIN_UNIQUE_WORDS}")
            recommendations.append("Limited information content")
        
        # 4. Coherence threshold
        if metadata.coherence_score < self.MIN_COHERENCE_SCORE:
            issues.append(f"Low coherence: {metadata.coherence_score:.2f}")
            recommendations.append("Text may be fragmented or poorly structured")
        
        # 5. Quality score threshold
        if metadata.quality_score < self.MIN_QUALITY_SCORE:
            issues.append(f"Low quality score: {metadata.quality_score:.2f}")
            recommendations.append("Consider removing or re-extracting")
        
        # 6. Entropy analysis (randomness detection)
        entropy = self._calculate_entropy(chunk_text)
        if entropy > self.MAX_ENTROPY_RATIO:
            issues.append(f"High entropy: {entropy:.2f} (possible gibberish)")
            recommendations.append("Text is too random, likely corrupted")
        
        # 7. Word repetition (spam detection)
        word_freq = {}
        words = chunk_text.lower().split()
        for word in words:
            if len(word) > 3:  # Only significant words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        repeated_words = sum(1 for freq in word_freq.values() if freq > 10)
        if repeated_words > 3:
            issues.append(f"High word repetition detected ({repeated_words} words)")
            recommendations.append("May be spam or machine-generated gibberish")
        
        # Determine pass/fail (stricter than Gate 1)
        passed = len(issues) == 0
        
        return passed, issues, recommendations
    
    # ========================================================================
    # GATE 3: QUALITY RANKING
    # ========================================================================
    
    def gate3_quality_ranking(
        self,
        chunk_text: str,
        metadata: 'ChunkMetadata',
    ) -> Tuple[float, List[str]]:
        """
        Gate 3: Rank chunk quality with composite score.
        
        Returns:
            (composite_score, issues)
        """
        issues = []
        
        # Calculate composite score
        composite_score = (
            metadata.quality_score * self.QUALITY_WEIGHT +
            metadata.coherence_score * self.COHERENCE_WEIGHT +
            metadata.completeness_score * self.COMPLETENESS_WEIGHT +
            metadata.importance_score * self.IMPORTANCE_WEIGHT
        )
        
        # Quality tier classification
        if composite_score >= self.EXCELLENT_THRESHOLD:
            tier = "EXCELLENT"
        elif composite_score >= self.GOOD_THRESHOLD:
            tier = "GOOD"
        elif composite_score >= self.FAIR_THRESHOLD:
            tier = "FAIR"
        else:
            tier = "POOR"
            issues.append(f"Poor quality tier: {composite_score:.2f}")
        
        # Normalize to 0-1
        normalized_score = min(1.0, composite_score)
        
        return normalized_score, issues
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy (randomness).
        
        Returns:
            Value between 0 (very structured) and 1 (very random)
        """
        if not text:
            return 0.0
        
        # Calculate character frequencies
        char_freq = {}
        for char in text:
            char_freq[char] = char_freq.get(char, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        text_len = len(text)
        for freq in char_freq.values():
            prob = freq / text_len
            entropy -= prob * (prob if prob == 0 else prob * (prob ** 0.5))
        
        # Normalize to 0-1
        max_entropy = 4.7  # Approximate maximum for typical text
        normalized_entropy = min(1.0, entropy / max_entropy)
        
        return normalized_entropy
    
    def get_quality_summary(self, reports: List[QualityReport]) -> Dict:
        """Generate summary statistics from quality reports"""
        if not reports:
            return {}
        
        passed = sum(1 for r in reports if r.passed)
        failed_gate1 = sum(1 for r in reports if not r.gate1_result)
        failed_gate2 = sum(1 for r in reports if not r.gate2_result)
        
        scores = [r.gate3_score for r in reports]
        
        return {
            "total_chunks": len(reports),
            "passed": passed,
            "pass_rate": passed / len(reports),
            "failed_gate1": failed_gate1,
            "failed_gate2": failed_gate2,
            "average_quality_score": statistics.mean(scores) if scores else 0,
            "median_quality_score": statistics.median(scores) if scores else 0,
            "max_quality_score": max(scores) if scores else 0,
            "min_quality_score": min(scores) if scores else 0,
        }
    
    def generate_report(self, reports: List[QualityReport]) -> str:
        """Generate human-readable quality report"""
        summary = self.get_quality_summary(reports)
        
        lines = [
            "=" * 80,
            "QUALITY FILTERING REPORT",
            "=" * 80,
            "",
            f"Total Chunks: {summary['total_chunks']}",
            f"Passed: {summary['passed']} ({summary['pass_rate']:.1%})",
            f"Failed Gate 1: {summary['failed_gate1']}",
            f"Failed Gate 2: {summary['failed_gate2']}",
            "",
            "Quality Score Statistics:",
            f"  Average: {summary['average_quality_score']:.3f}",
            f"  Median:  {summary['median_quality_score']:.3f}",
            f"  Range:   {summary['min_quality_score']:.3f} - {summary['max_quality_score']:.3f}",
            "",
            "Top Issues:",
        ]
        
        # Find most common issues
        all_issues = {}
        for report in reports:
            for issue in report.issues:
                all_issues[issue] = all_issues.get(issue, 0) + 1
        
        for issue, count in sorted(all_issues.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  - {issue}: {count} chunks")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


# ============================================================================
# QUALITY TIER CLASSIFIER
# ============================================================================

class QualityTierClassifier:
    """Classify chunks into quality tiers for different use cases"""
    
    @staticmethod
    def get_tier(score: float) -> str:
        """Get quality tier name"""
        if score >= 0.85:
            return "EXCELLENT"
        elif score >= 0.70:
            return "GOOD"
        elif score >= 0.50:
            return "FAIR"
        else:
            return "POOR"
    
    @staticmethod
    def should_embed(score: float, chunk_type: str = "general") -> bool:
        """Decide whether to embed chunk"""
        # High-quality chunks should always be embedded
        if score >= 0.70:
            return True
        
        # Medium quality might still be useful
        if score >= 0.50 and chunk_type in ["header", "summary"]:
            return True
        
        return False
    
    @staticmethod
    def should_retrieve(score: float) -> bool:
        """Decide whether to retrieve chunk for user queries"""
        # Only retrieve if reasonable quality
        return score >= 0.50
    
    @staticmethod
    def should_flag_for_review(score: float) -> bool:
        """Flag for human review"""
        return score < 0.50 and score > 0.0
