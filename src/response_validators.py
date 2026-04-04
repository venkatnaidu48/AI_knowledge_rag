"""
STEP 7: Response Validation & Quality Scoring
Implements 5 validators to check answer quality
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result from a single validator"""
    validator_name: str
    score: float  # 0.0-1.0
    max_points: int
    reasoning: str


@dataclass
class OverallQualityScore:
    """Complete validation report"""
    overall_score: float  # 0.0-1.0
    quality_level: str  # EXCELLENT, GOOD, FAIR, POOR
    individual_scores: Dict[str, float]
    breakdown: List[ValidationResult]
    is_hallucination_detected: bool
    hallucination_details: str
    recommendations: List[str]


class ResponseValidators:
    """Validates answer quality using 5 different metrics"""
    
    QUALITY_LEVELS = {
        (0.85, 1.0): "EXCELLENT",
        (0.70, 0.84): "GOOD",
        (0.50, 0.69): "FAIR",
        (0.0, 0.49): "POOR"
    }
    
    def __init__(self):
        """Initialize validators"""
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'that', 'this',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all',
            'each', 'every', 'both', 'few', 'more', 'most', 'some', 'such',
            'no', 'nor', 'not', 'as', 'if', 'than', 'then', 'by', 'from',
            'up', 'about', 'into', 'through', 'during', 'while', 'before',
            'after', 'above', 'below', 'between', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'so', 'because', 'just', 'only', 'very', 'too', 'also', 'now'
        }
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split and filter
        words = text.split()
        keywords = [w for w in words if w not in self.stopwords and len(w) > 2]
        
        return list(set(keywords))  # Remove duplicates
    
    # ==================== VALIDATOR 1: RELEVANCE ====================
    def validate_relevance(self, question: str, answer: str) -> ValidationResult:
        """
        VALIDATOR 1: Relevance (40 points max)
        Does the answer address the question?
        """
        question_keywords = self.extract_keywords(question)
        answer_keywords = self.extract_keywords(answer)
        
        # Score 1: Keywords overlap
        if question_keywords:
            overlap = len(set(question_keywords) & set(answer_keywords)) / len(question_keywords)
        else:
            overlap = 0.5
        
        # Score 2: Answer length (should respond to question depth)
        # Longer questions often need longer answers
        ideal_length = min(500, len(question) * 10)  # Scale with question
        actual_length = len(answer)
        
        if actual_length > 0:
            length_ratio = min(actual_length / ideal_length, 1.0) if ideal_length > 0 else 1.0
        else:
            length_ratio = 0
        
        # Score 3: Information density (unique words per total words)
        if len(answer.split()) > 0:
            density = len(set(answer.split())) / len(answer.split())
        else:
            density = 0
        
        # Combine: 50% keyword overlap, 30% length appropriateness, 20% density
        relevance_score = (0.5 * overlap) + (0.3 * length_ratio) + (0.2 * density)
        relevance_score = min(1.0, relevance_score)
        
        reasoning = (
            f"Keyword overlap: {overlap:.0%} | "
            f"Length fit: {length_ratio:.0%} | "
            f"Information density: {density:.0%}"
        )
        
        return ValidationResult(
            validator_name="Relevance",
            score=relevance_score,
            max_points=40,
            reasoning=reasoning
        )
    
    # ==================== VALIDATOR 2: COHERENCE ====================
    def validate_coherence(self, answer: str) -> ValidationResult:
        """
        VALIDATOR 2: Coherence (30 points max)
        Is the answer clear and logical?
        """
        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return ValidationResult(
                validator_name="Coherence",
                score=0.0,
                max_points=30,
                reasoning="No sentences found"
            )
        
        # Score 1: Average sentence length (ideal: 15-25 words)
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        
        # Penalize very long (>40 words) or very short (<5 words) sentences
        if 15 <= avg_length <= 25:
            length_score = 1.0
        elif 5 <= avg_length <= 40:
            length_score = 0.8
        else:
            length_score = 0.4
        
        # Score 2: Check for repetition (low repetition = good coherence)
        words = answer.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
        else:
            unique_ratio = 0
        
        # Penalize high repetition (ratio < 0.6)
        if unique_ratio > 0.7:
            repetition_score = 1.0
        elif unique_ratio > 0.5:
            repetition_score = 0.7
        else:
            repetition_score = 0.3
        
        # Score 3: Check for grammatical issues (simplified)
        # Look for basic patterns
        grammar_issues = 0
        
        # Check for multiple spaces
        if '  ' in answer:
            grammar_issues += 1
        
        # Check for balanced parentheses/quotes
        if answer.count('(') != answer.count(')'):
            grammar_issues += 1
        if answer.count('"') % 2 != 0:
            grammar_issues += 1
        
        grammar_score = max(0.5, 1.0 - (grammar_issues * 0.15))
        
        # Combine: 40% length, 35% uniqueness, 25% grammar
        coherence_score = (0.4 * length_score) + (0.35 * repetition_score) + (0.25 * grammar_score)
        coherence_score = min(1.0, coherence_score)
        
        reasoning = (
            f"Sentence length: {'GOOD' if length_score == 1.0 else 'FAIR'} ({avg_length:.1f} words) | "
            f"Uniqueness: {unique_ratio:.0%} | "
            f"Grammar: {grammar_score:.2f}"
        )
        
        return ValidationResult(
            validator_name="Coherence",
            score=coherence_score,
            max_points=30,
            reasoning=reasoning
        )
    
    # ==================== VALIDATOR 3: LENGTH ====================
    def validate_length(self, answer: str) -> ValidationResult:
        """
        VALIDATOR 3: Length (20 points max)
        Is answer appropriate length?
        """
        word_count = len(answer.split())
        
        # Define ranges
        if word_count < 30:
            score = 0.3
            category = "TOO SHORT"
        elif word_count < 50:
            score = 0.6
            category = "SHORT"
        elif word_count <= 300:
            score = 1.0
            category = "IDEAL"
        elif word_count <= 500:
            score = 0.8
            category = "LONG"
        else:
            score = 0.4
            category = "TOO LONG"
        
        reasoning = f"{category}: {word_count} words"
        
        return ValidationResult(
            validator_name="Length",
            score=score,
            max_points=20,
            reasoning=reasoning
        )
    
    # ==================== VALIDATOR 4: GROUNDING ====================
    def validate_grounding(self, answer: str, context: str) -> ValidationResult:
        """
        VALIDATOR 4: Grounding (25 points max)
        Is the answer based on the provided context?
        """
        # Extract key phrases (2-3 word combinations) from answer
        answer_lower = answer.lower()
        context_lower = context.lower()
        
        # Get meaningful phrases from answer
        words = re.findall(r'\b\w{4,}\b', answer_lower)  # Words > 3 chars
        phrases = []
        
        # Create 2-3 word phrases
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            phrases.append(phrase)
        
        if len(words) > 2:
            for i in range(len(words) - 2):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                phrases.append(phrase)
        
        # Check how many phrases are grounded in context
        grounded = 0
        hallucinated = []
        
        for phrase in phrases:
            if phrase in context_lower:
                grounded += 1
            else:
                # Check if individual words are in context
                phrase_words = phrase.split()
                words_found = sum(1 for w in phrase_words if w in context_lower)
                if words_found / len(phrase_words) < 0.5:  # < 50% words in context
                    hallucinated.append(phrase)
        
        # Calculate grounding percentage
        if len(phrases) > 0:
            grounding_ratio = grounded / len(phrases)
        else:
            grounding_ratio = 0.5 if context else 0
        
        # Detect hallucinations (many facts not in context)
        is_hallucinating = grounding_ratio < 0.5 and len(hallucinated) > 3
        
        reasoning = f"Grounding: {grounding_ratio:.0%} | Phrases checked: {len(phrases)}"
        if hallucinated and len(hallucinated) <= 5:
            reasoning += f" | Potential hallucinations: {', '.join(hallucinated[:3])}"
        
        return ValidationResult(
            validator_name="Grounding",
            score=min(1.0, grounding_ratio + 0.1),  # Add 0.1 for tolerance
            max_points=25,
            reasoning=reasoning
        )
    
    # ==================== VALIDATOR 5: COMPLETENESS ====================
    def validate_completeness(self, question: str, answer: str) -> ValidationResult:
        """
        VALIDATOR 5: Completeness (20 points max)
        Does answer fully address the question?
        """
        # Analyze question type
        question_lower = question.lower()
        
        # Question types
        is_what = any(q in question_lower for q in ['what is', 'what are', 'what does'])
        is_how = 'how' in question_lower
        is_why = 'why' in question_lower
        is_when = 'when' in question_lower
        is_who = 'who' in question_lower
        
        # Check if answer provides expected information
        answer_lower = answer.lower()
        score = 0.5  # Base score
        
        if is_what:
            # Should define or describe
            if len(answer) > 100:  # Adequate description
                score += 0.3
            if any(word in answer_lower for word in ['is', 'are', 'refers to', 'means', 'includes']):
                score += 0.2
        
        elif is_how:
            # Should explain steps or mechanism
            if any(word in answer_lower for word in ['step', 'process', 'method', 'first', 'then', 'finally']):
                score += 0.3
            if len(answer) > 120:
                score += 0.2
        
        elif is_why:
            # Should provide reasons
            if any(word in answer_lower for word in ['because', 'reason', 'cause', 'due to', 'result of']):
                score += 0.3
            if len(answer) > 100:
                score += 0.2
        
        elif is_when:
            # Should provide time/date
            if any(word in answer_lower for word in ['date', 'time', 'year', 'month', 'day', 'when']):
                score += 0.3
            if len(answer) > 50:
                score += 0.2
        
        elif is_who:
            # Should identify person/entity
            if any(word in answer_lower for word in ['person', 'company', 'organization', 'team', 'named']):
                score += 0.3
            if len(answer) > 60:
                score += 0.2
        
        else:
            # Generic question - check answer depth
            if len(answer) > 150:
                score += 0.3
            if answer.count('.') > 2:  # Multiple sentences
                score += 0.2
        
        score = min(1.0, score)
        
        reasoning = f"Question type: {['WHAT', 'HOW', 'WHY', 'WHEN', 'WHO', 'OTHER'][sum([is_what, is_how, is_why, is_when, is_who])]}"
        
        return ValidationResult(
            validator_name="Completeness",
            score=score,
            max_points=20,
            reasoning=reasoning
        )
    
    # ==================== MAIN VALIDATION METHOD ====================
    def validate_response(
        self,
        question: str,
        answer: str,
        context: str = ""
    ) -> OverallQualityScore:
        """
        Validate complete response using all 5 validators
        
        Args:
            question: Original user question
            answer: Generated answer
            context: Retrieved context from documents
        
        Returns:
            OverallQualityScore with all metrics
        """
        # Run all validators
        validators_results = [
            self.validate_relevance(question, answer),
            self.validate_coherence(answer),
            self.validate_length(answer),
            self.validate_grounding(answer, context),
            self.validate_completeness(question, answer),
        ]
        
        # Calculate overall score (weighted average)
        total_score = 0
        individual_scores = {}
        
        for result in validators_results:
            score = result.score
            individual_scores[result.validator_name] = score
            total_score += score
        
        overall_score = total_score / len(validators_results)
        
        # Determine quality level
        quality_level = "POOR"
        for (min_score, max_score), level in self.QUALITY_LEVELS.items():
            if min_score <= overall_score <= max_score:
                quality_level = level
                break
        
        # Detect hallucinations
        grounding_result = validators_results[3]
        is_hallucinating = grounding_result.score < 0.5
        
        # Generate recommendations
        recommendations = []
        for result in validators_results:
            if result.score < 0.7:
                if result.validator_name == "Relevance":
                    recommendations.append("🔴 Answer may not directly address the question")
                elif result.validator_name == "Coherence":
                    recommendations.append("🔴 Answer structure could be clearer")
                elif result.validator_name == "Length":
                    recommendations.append("🔴 Consider adjusting answer length")
                elif result.validator_name == "Grounding":
                    recommendations.append("🔴 ⚠️ HALLUCINATION DETECTED - Answer not grounded in context")
                elif result.validator_name == "Completeness":
                    recommendations.append("🔴 Answer may be incomplete")
        
        if not recommendations:
            recommendations.append("✅ All validations passed")
        
        return OverallQualityScore(
            overall_score=overall_score,
            quality_level=quality_level,
            individual_scores=individual_scores,
            breakdown=validators_results,
            is_hallucination_detected=is_hallucinating,
            hallucination_details=grounding_result.reasoning if is_hallucinating else "None detected",
            recommendations=recommendations
        )


# ==================== STANDALONE TESTING ====================
if __name__ == "__main__":
    validator = ResponseValidators()
    
    # Test case 1: Good answer
    question1 = "What is our company strategy?"
    answer1 = "Our company strategy focuses on sustainable growth through three main pillars: innovation, customer focus, and operational excellence. We invest heavily in R&D to develop cutting-edge solutions. Our team is committed to delivering value to customers while maintaining strong operational performance."
    context1 = "Our strategy is built on three pillars: innovation, customer focus, and operational excellence. We invest in R&D."
    
    print("\n" + "="*80)
    print("TEST 1: GOOD ANSWER")
    print("="*80)
    result1 = validator.validate_response(question1, answer1, context1)
    print(f"\nOverall Score: {result1.overall_score:.2f}")
    print(f"Quality Level: {result1.quality_level}")
    print(f"\nIndividual Scores:")
    for name, score in result1.individual_scores.items():
        print(f"  {name}: {score:.2f}")
    print(f"\nBreakdown:")
    for v in result1.breakdown:
        print(f"  {v.validator_name}: {v.reasoning}")
    print(f"\nRecommendations:")
    for rec in result1.recommendations:
        print(f"  {rec}")
    
    # Test case 2: Hallucinated answer
    question2 = "What is our strategy?"
    answer2 = "We use cutting-edge quantum computing and AI robots to automate everything. Our plan involves expanding to Mars and using blockchain for everything."
    context2 = "Our strategy focuses on growth through innovation."
    
    print("\n" + "="*80)
    print("TEST 2: HALLUCINATED ANSWER")
    print("="*80)
    result2 = validator.validate_response(question2, answer2, context2)
    print(f"\nOverall Score: {result2.overall_score:.2f}")
    print(f"Quality Level: {result2.quality_level}")
    print(f"Hallucination Detected: {result2.is_hallucination_detected}")
    print(f"\nRecommendations:")
    for rec in result2.recommendations:
        print(f"  {rec}")

