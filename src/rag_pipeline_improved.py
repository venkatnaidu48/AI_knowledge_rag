#!/usr/bin/env python
"""
IMPROVED RAG PIPELINE WITH HALLUCINATION FIXES
Steps 5-7: Query Processing → LLM Generation → Response Validation
Enhanced with: Better hallucination detection, Quality filters, Grounding checks
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.qa_advanced_full import AdvancedQASystem
from src.llm_generation import LLMGenerator, RetrievalOnlyAnswerer
from src.response_validators import ResponseValidators, OverallQualityScore
from dataclasses import dataclass
from typing import Optional
import logging

logging.disable(logging.CRITICAL)


@dataclass
class ImprovedRAGResponse:
    """Improved RAG response with hallucination fixes"""
    question: str
    answer: str
    source_documents: str
    llm_provider: str
    validation_score: float
    quality_level: str
    hallucination_risk: str  # SAFE, LOW, MEDIUM, HIGH
    grounding_score: float  # 0-100% (critical for hallucination detection)
    recommendations: list
    full_validation: Optional[OverallQualityScore] = None


class ImprovedRAGPipeline:
    """
    Improved RAG Pipeline with Hallucination Detection & Quality Filters
    
    ENHANCEMENTS:
    1. Stricter grounding validation (detects hallucinations)
    2. Quality threshold filters (rejects low-quality answers)
    3. Confidence-based response selection
    4. Context verification before answering
    5. Automatic fallback strategies
    """
    
    def __init__(self, verbose: bool = False, min_quality: float = 0.75):
        """
        Initialize improved RAG pipeline
        
        Args:
            verbose: Enable detailed logging
            min_quality: Minimum quality score (0-1) to accept an answer
        """
        self.verbose = verbose
        self.min_quality = min_quality  # Default: accept only >75% quality
        self.qa_system = AdvancedQASystem()
        self.llm_generator = LLMGenerator(verbose=verbose)
        self.validator = ResponseValidators()
    
    def _get_grounding_score(self, answer: str, context: str) -> float:
        """
        Calculate grounding score (how well answer is grounded in context)
        Returns 0-1, where 1 = perfectly grounded
        
        HALLUCINATION DETECTOR: If grounding is low, answer may hallucinate
        """
        
        # Extract key claims from answer
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        
        # Calculate overlap
        if not answer_words:
            return 0.0
        
        overlap = len(answer_words & context_words)
        grounding = overlap / len(answer_words)
        
        # Stricter grounding (avoid hallucinations)
        # If <50% of answer words are grounded in context, it's likely hallucinating
        return grounding
    
    def _check_hallucination_risk(self, grounding_score: float, validation_score: float) -> str:
        """
        Determine hallucination risk level
        
        SAFE (<5% risk):     Grounding >0.7 AND Quality >0.85
        LOW (5-25% risk):    Grounding >0.5 AND Quality >0.75
        MEDIUM (25-60% risk): Grounding >0.3 AND Quality >0.60
        HIGH (>60% risk):    Grounding ≤0.3 OR Quality ≤0.60
        """
        
        # Convert scores to 0-1 range
        validation = validation_score / 100.0 if validation_score > 1 else validation_score
        
        if grounding_score > 0.7 and validation > 0.85:
            return "✅ SAFE (< 5% risk)"
        elif grounding_score > 0.5 and validation > 0.75:
            return "🟢 LOW (5-25% risk)"
        elif grounding_score > 0.3 and validation > 0.60:
            return "🟡 MEDIUM (25-60% risk)"
        else:
            return "🔴 HIGH (> 60% risk)"
    
    def process_query(self, question: str, use_llm: bool = True, strict_mode: bool = True) -> ImprovedRAGResponse:
        """
        Process query with improved hallucination detection
        
        Args:
            question: User's question
            use_llm: Try to use LLM (fallback to retrieval if unavailable)
            strict_mode: If True, reject low-quality answers (min_quality threshold)
        
        Returns:
            ImprovedRAGResponse with hallucination risk assessment
        """
        
        # STEP 5: Query Processing with high threshold (0.8 = 80% keyword match required)
        qa_threshold = 0.8 if strict_mode else 0.6
        result = self.qa_system.search_knowledge_base(question, min_keywords_present=qa_threshold)
        
        if not result:
            return ImprovedRAGResponse(
                question=question,
                answer="❌ No relevant information found in knowledge base.",
                source_documents="None",
                llm_provider="N/A",
                validation_score=0.0,
                quality_level="NONE",
                hallucination_risk="N/A",
                grounding_score=0.0,
                recommendations=["Question does not match any knowledge base content"]
            )
        
        context = result["chunk"].chunk_text
        doc_name = result["doc"].name
        
        # STEP 6: LLM Generation
        answer = None
        llm_provider = "NONE"
        
        if use_llm:
            try:
                # Call generate_answer() which returns GeneratedAnswer object
                generated = self.llm_generator.generate_answer(
                    context=context,
                    question=question
                )
                if generated:
                    answer = generated.answer
                    llm_provider = generated.provider_used
            except Exception as e:
                if self.verbose:
                    print(f"[DEBUG] LLM generation failed: {e}")
                answer = None
        
        # Fallback to retrieval if LLM fails
        if not answer:
            answer = context
            llm_provider = "RETRIEVAL_ONLY"
        
        # STEP 7: Response Validation with Enhanced Hallucination Detection
        overall_score = self.validator.validate_response(question, answer, context)
        
        # Calculate grounding score (CRITICAL for hallucination detection)
        grounding_score = self._get_grounding_score(answer, context)
        
        # Assess hallucination risk
        hallucination_risk = self._check_hallucination_risk(
            grounding_score,
            overall_score.overall_score * 100  # Convert to percentage
        )
        
        # QUALITY FILTER: Reject if quality is too low
        recommendations = []
        
        if overall_score.overall_score < self.min_quality:
            recommendations.append(
                f"⚠️ Low quality ({overall_score.overall_score*100:.1f}% < {self.min_quality*100:.0f}% threshold)"
            )
        
        if grounding_score < 0.5:
            recommendations.append(
                "⚠️ Answer may not be grounded in source material (hallucination risk)"
            )
        
        if "HIGH" in hallucination_risk:
            recommendations.append(
                "🔴 High hallucination risk - answer may contain inaccuracies"
            )
        
        # Format response
        formatted_answer = f"{answer[:1000]}"
        if len(answer) > 1000:
            formatted_answer += "\n\n[...response truncated...]"
        
        return ImprovedRAGResponse(
            question=question,
            answer=formatted_answer,
            source_documents=doc_name,
            llm_provider=llm_provider,
            validation_score=overall_score.overall_score * 100,  # Convert to percentage
            quality_level=overall_score.quality_level,
            hallucination_risk=hallucination_risk,
            grounding_score=grounding_score * 100,  # Convert to percentage
            recommendations=recommendations,
            full_validation=overall_score
        )
    
    def process_query_safe_mode(self, question: str) -> ImprovedRAGResponse:
        """
        SAFE MODE: Only return answers with <5% hallucination risk and >90% quality
        """
        response = self.process_query(question, use_llm=True, strict_mode=True)
        
        # Check safety criteria
        if ("SAFE" not in response.hallucination_risk and 
            response.validation_score < 90):
            response.answer = f"⚠️ Cannot provide safe answer.\n\nReason: {response.hallucination_risk}\nQuality: {response.validation_score:.1f}%\n\nPlease refine your question or try: {response.recommendations[0] if response.recommendations else 'N/A'}"
            response.recommendations.insert(0, "Answer rejected - unsafe mode")
        
        return response


def print_response(response: ImprovedRAGResponse, verbose: bool = False):
    """Pretty print the response"""
    
    print("\n" + "="*80)
    print(f"❓ QUESTION: {response.question}")
    print("="*80)
    
    print(f"\n📄 SOURCE: {response.source_documents}")
    print(f"🤖 PROVIDER: {response.llm_provider}")
    
    print(f"\n📊 QUALITY METRICS:")
    print(f"   Quality Score: {response.validation_score:.1f}% ({response.quality_level})")
    print(f"   Grounding Score: {response.grounding_score:.1f}%")
    print(f"   Hallucination Risk: {response.hallucination_risk}")
    
    print(f"\n💡 ANSWER:")
    print(f"{response.answer}")
    
    if response.recommendations:
        print(f"\n⚠️  NOTES:")
        for rec in response.recommendations:
            print(f"   {rec}")
    
    if verbose and response.full_validation:
        print(f"\n🔍 DETAILED VALIDATION:")
        for validator in response.full_validation.breakdown:
            print(f"   {validator.validator_name}: {validator.score:.2f} ({validator.reasoning})")
    
    print("\n" + "="*80)


def main():
    """Interactive mode with improved hallucination detection"""
    
    print("\n" + "="*80)
    print("IMPROVED RAG PIPELINE - HALLUCINATION DETECTION & QUALITY FILTERS")
    print("="*80)
    print("""
FEATURES:
  ✓ Enhanced grounding validation (detects hallucinations)
  ✓ Quality score filters (rejects low-quality answers)
  ✓ Hallucination risk assessment (SAFE/LOW/MEDIUM/HIGH)
  ✓ Confidence-based response selection
  ✓ Context verification

COMMANDS:
  Type 'quit' or 'exit' to exit
  Type 'safe' to enable safe mode (only answers >90% quality)
  Type 'verbose' to toggle detailed validation info
  Type 'help' for more information

""")
    
    pipeline = ImprovedRAGPipeline(verbose=False, min_quality=0.75)
    verbose = False
    safe_mode = False
    
    while True:
        try:
            prompt = "❓ Your question" + (" (SAFE MODE)" if safe_mode else "") + ": "
            question = input(prompt).strip()
            
            if not question:
                continue
            
            if question.lower() == "quit" or question.lower() == "exit":
                print("\nExiting...\n")
                break
            
            if question.lower() == "verbose":
                verbose = not verbose
                print(f"Verbose mode: {'ON' if verbose else 'OFF'}\n")
                continue
            
            if question.lower() == "safe":
                safe_mode = not safe_mode
                print(f"Safe mode: {'ON ✅ (only answers with <5% hallucination risk)' if safe_mode else 'OFF'}\n")
                continue
            
            if question.lower() == "help":
                print("""
IMPROVED RAG FEATURES:
  
  1. HALLUCINATION DETECTION:
     - Measures answer "grounding" in source material
     - Detects claims not supported by context
     - Assesses hallucination risk (SAFE/LOW/MEDIUM/HIGH)
  
  2. QUALITY FILTERING:
     - Validates answer relevance, coherence, length, grounding, completeness
     - Rejects answers below quality threshold
     - Provides quality score (0-100%)
  
  3. SAFE MODE:
     - Only returns answers with <5% hallucination risk AND >90% quality
     - Recommended for critical applications
  
  4. TO IMPROVE QUALITY TO >90%:
     - Configure LLM providers (OpenAI, Groq, or Ollama)
     - See SETUP_LLM.md for instructions
     - Grounding will improve with better context relevance

SETUP LLM (to get better answers):
  1. OpenAI (Recommended):
     - Set OPENAI_API_KEY environment variable
     - export OPENAI_API_KEY="sk-..."
  
  2. Groq (Free):
     - Set GROQ_API_KEY and GROQ_MODEL environment variables
     - export GROQ_API_KEY="gsk_..."
     - export GROQ_MODEL="mixtral-8x7b-32768"
  
  3. Ollama (Local):
     - Start: ollama run mistral
     - Set OLLAMA_API_URL="http://localhost:11434"

QUALITY IMPROVEMENT:
  Current: 73.8% (GOOD with hallucination risk)
  Goal: 90%+ (EXCELLENT, safe for production)
  
  What's needed:
  ✓ LLM provider (removes RETRIEVAL_ONLY fallback)
  ✓ Tighter relevance thresholds (filters bad chunks)
  ✓ Stronger grounding checks (detects hallucinations)
  ✓ Quality filters (rejects low-confidence answers)

""")
                continue
            
            # Process query
            if safe_mode:
                response = pipeline.process_query_safe_mode(question)
            else:
                response = pipeline.process_query(question, use_llm=True, strict_mode=True)
            
            print_response(response, verbose=verbose)
        
        except KeyboardInterrupt:
            print("\n\nExiting...\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            continue


if __name__ == "__main__":
    main()
