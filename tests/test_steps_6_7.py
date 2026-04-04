#!/usr/bin/env python
"""Direct test of Steps 6 & 7: LLM Generation and Validation"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.disable(logging.CRITICAL)

from llm_generation import LLMGenerator, RetrievalOnlyAnswerer
from response_validators import ResponseValidators

print("\n" + "="*90)
print("STEP 6: LLM GENERATION TEST")
print("="*90)

# Test LLM generation
generator = LLMGenerator(verbose=False)
context = """
Our company strategy focuses on three main pillars:
1. Innovation: We invest heavily in R&D to develop cutting-edge solutions
2. Customer Focus: We prioritize customer satisfaction and feedback
3. Operational Excellence: We maintain high standards in all operations
"""

question = "What is your company strategy?"
answer = generator.generate_answer(context, question)

if answer:
    print(f"✅ LLM Generated Answer (using: {answer.provider_used})")
    print(f"   Time: {answer.generation_time_ms:.0f}ms")
    print(f"   Answer: {answer.answer[:100]}...")
else:
    print("⚠️ No LLM available - using retrieval only")
    answer_text = RetrievalOnlyAnswerer.format_answer([{"text": context}], question)
    print(f"✅ Retrieval-only answer: {answer_text[:100]}...")

print("\n" + "="*90)
print("STEP 7: RESPONSE VALIDATION TEST")
print("="*90)

# Test response validation
validator = ResponseValidators()

# Test case 1: Good answer
print("\n[TEST 1] GOOD ANSWER from knowledge base")
print("-" * 90)
good_q = "What is our strategy?"
good_a = "Our strategy focuses on three main pillars: innovation, customer focus, and operational excellence."
good_ctx = "Our strategy has three pillars: innovation, customer focus, and operational excellence."

result1 = validator.validate_response(good_q, good_a, good_ctx)
print(f"📊 Overall Score: {result1.overall_score:.3f} ({result1.quality_level})")
print(f"   Relevance:    {result1.individual_scores['Relevance']:.3f}")
print(f"   Coherence:    {result1.individual_scores['Coherence']:.3f}")
print(f"   Length:       {result1.individual_scores['Length']:.3f}")
print(f"   Grounding:    {result1.individual_scores['Grounding']:.3f}")
print(f"   Completeness: {result1.individual_scores['Completeness']:.3f}")
print(f"🔍 Hallucination: {result1.is_hallucination_detected}")

# Test case 2: Hallucinated answer
print("\n[TEST 2] HALLUCINATED ANSWER (not in knowledge base)")
print("-" * 90)
bad_q = "What is your strategy?"
bad_a = "We use quantum computers and AI to revolutionize the entire industry with blockchain."
bad_ctx = "Our strategy focuses on growth."

result2 = validator.validate_response(bad_q, bad_a, bad_ctx)
print(f"📊 Overall Score: {result2.overall_score:.3f} ({result2.quality_level})")
print(f"🔍 Hallucination: {result2.is_hallucination_detected}")
if result2.is_hallucination_detected:
    print(f"⚠️  ALERT: Potential hallucination detected!")
    for rec in result2.recommendations:
        if "HALLUCINATION" in rec:
            print(f"   {rec}")

# Test case 3: Unrelated query
print("\n[TEST 3] UNRELATED QUERY (should be caught)")
print("-" * 90)
unrelated_q = "What is the recipe for pizza?"
unrelated_a = "Answer not found in knowledge base."
unrelated_ctx = ""

result3 = validator.validate_response(unrelated_q, unrelated_a, unrelated_ctx)
print(f"📊 Overall Score: {result3.overall_score:.3f} ({result3.quality_level})")
print(f"🔍 Hallucination: {result3.is_hallucination_detected}")

print("\n" + "="*90)
print("STEP 6 & 7 SUMMARY")
print("="*90)
print("""
✅ STEP 6: LLM Generation
   • Multi-provider support (OpenAI, Mistral, Groq, HuggingFace)
   • Automatic fallback strategy
   • Retrieval-only mode when LLM unavailable

✅ STEP 7: Response Validation
   • 5 validators: Relevance, Coherence, Length, Grounding, Completeness
   • Hallucination detection
   • Quality scoring (0-100%)
   • Actionable recommendations

Combined Systems Form Complete RAG Pipeline
""")

