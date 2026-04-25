"""
GETTING STARTED: Complete RAG Pipeline (Steps 1-7)

Your RAG system is now FULLY FUNCTIONAL for:
- Document ingestion and search
- LLM-powered answer generation
- Response validation with quality scoring
- Hallucination detection

This file explains how to use your system.
"""

# ==========================================
# 1. SIMPLE USAGE - Retrieval Only (No LLM)
# ==========================================

print("""
Option 1: RETRIEVAL-ONLY (No LLM needed, works immediately)
============================================================

This is the simplest and fastest way to use your system.
No LLM providers needed, just searches knowledge base.

Code:
""")

example1 = """
from qa_advanced_full import AdvancedQASystem

qa_system = AdvancedQASystem()

answer = qa_system.get_answer(
    "What is our company strategy?",
    threshold=0.5  # 50% keyword match required
)

print(answer)
qa_system.close()
"""

print(example1)

print("""
To run:
    python -c 'from qa_advanced_full import *; q = AdvancedQASystem(); print(q.get_answer("strategy"))'

Or interactively:
    python -i qa_advanced_full.py
    >>> system = AdvancedQASystem()
    >>> print(system.get_answer("What is our company strategy?"))
""")


# ==========================================
# 2. INTERMEDIATE: With Validation Only
# ==========================================

print("\n" + "="*70)
print("""
Option 2: RETRIEVAL + VALIDATION (Quality scoring, hallucination detection)
==========================================================================

Add response validation to know quality of answers.
Still no LLM, so completely free and private.

Code:
""")

example2 = """
from qa_advanced_full import AdvancedQASystem
from response_validators import ResponseValidators

qa_system = AdvancedQASystem()
validator = ResponseValidators()

# Get answer from knowledge base
answer = qa_system.get_answer("What is our company strategy?")

# Validate quality
validation = validator.validate_response(
    question="What is our company strategy?",
    answer=answer,
    context=answer  # Use the retrieved answer as context
)

print(f"Answer: {answer}")
print(f"Quality: {validation.overall_score:.1%} - {validation.quality_level}")
print(f"Hallucination Risk: {validation.is_hallucination_detected}")

qa_system.close()
"""

print(example2)


# ==========================================
# 3. ADVANCED: Complete Pipeline (All Steps)
# ==========================================

print("\n" + "="*70)
print("""
Option 3: COMPLETE PIPELINE (Retrieval + LLM + Validation)
===========================================================

Use all 7 steps for maximum power.
Optional: Add LLM providers for enhanced answers.

Setup (Optional - choose ONE):
1. OpenAI (best quality)
   set OPENAI_API_KEY=sk-...

2. Local Mistral (free, private - need Ollama)
   Download: ollama.ai
   Run: ollama serve
   Pull: ollama pull mistral:7b

3. Groq (fast, free tier)
   get API: groq.com
   set GROQ_API_KEY=gsk_...

4. HuggingFace (free, rate-limited)
   get API: huggingface.co
   set HUGGINGFACE_API_KEY=hf_...

Code:
""")

example3 = """
from rag_complete_pipeline import RAGPipeline

# Create pipeline (will auto-detect available LLM providers)
pipeline = RAGPipeline(verbose=True)

# Process query through ALL STEPS
response = pipeline.process_query(
    question="What is our company strategy?",
    retrieval_threshold=0.5,      # STEP 5: Query processing
    generation_temperature=0.1,    # STEP 6: LLM generation
    use_llm=True                   # Try LLM, fallback to retrieval
)

# Get results with quality score
print(f"Answer: {response.answer}")
print(f"Source: {response.source_documents}")
print(f"Provider: {response.llm_provider}")  # Which provider was used
print(f"Quality: {response.quality_level} ({response.validation_score:.1%})")
print(f"Hallucination Risk: {response.hallucination_detected}")

for rec in response.recommendations:
    print(f"  {rec}")

pipeline.close()
"""

print(example3)


# ==========================================
# 4. INTERACTIVE MODE
# ==========================================

print("\n" + "="*70)
print("""
Option 4: INTERACTIVE MODE (Best for exploration)
=================================================

Start an interactive Q&A session:

    python rag_complete_pipeline.py

Then ask questions like:
    ❓ Your question: What is our company strategy?
    ❓ Your question: What are our 2024 revenue targets?
    ❓ Your question: How do we ensure data security?
    
Type 'verbose' to toggle detailed output
Type 'quit' to exit
""")


# ==========================================
# 5. BATCH TESTING
# ==========================================

print("\n" + "="*70)
print("""
Option 5: BATCH TESTING (Test multiple questions)
==================================================

Run predefined tests:

    python rag_complete_pipeline.py batch

Shows:
    • Question
    • Found documents
    • Quality score
    • Hallucination risk
    • Answer preview
""")


# ==========================================
# 6. PERFORMANCE TUNING
# ==========================================

print("\n" + "="*70)
print("""
Performance Tuning Options
===========================

Threshold Levels (STEP 5 - Query Processing):
-----------
threshold=0.5  -> 50% keyword match (High Recall, may have false positives)
threshold=0.7  -> 70% keyword match (Balanced)
threshold=0.8  -> 80% keyword match (Default, Precision-focused)
threshold=1.0  -> 100% keyword match (All keywords required, no false positives)

LLM Temperature (STEP 6 - Generation):
-----------
temperature=0.0  -> Deterministic, always same answer
temperature=0.5  -> Balanced (recommended)
temperature=1.0  -> Creative, more varied answers

Max Tokens (STEP 6 - Generation):
-----------
max_tokens=100  -> Very short answers
max_tokens=300  -> Medium answers (default)
max_tokens=500  -> Long, detailed answers

Use LLM (STEP 6 - Generation):
-----------
use_llm=False  -> Fast, retrieval-only (no LLM wait time)
use_llm=True   -> Better quality, but slower if LLM available

Example: Faster responses
""")

example_tuning = """
response = pipeline.process_query(
    question="What is our strategy?",
    retrieval_threshold=0.7,       # Moderate precision
    generation_temperature=0.0,    # Consistent answers
    use_llm=False                  # Speed priority, skip LLM
)
"""

print(example_tuning)


# ==========================================
# 7. QUALITY LEVELS EXPLAINED
# ==========================================

print("\n" + "="*70)
print("""
Understanding Quality Scores (STEP 7 - Validation)
====================================================

Quality Levels:
    
    85-100%  -> EXCELLENT ✅
             (Can confidently use this answer)
    
    70-84%   -> GOOD ✅
             (Good quality, mostly reliable)
    
    50-69%   -> FAIR ⚠️
             (Acceptable but may need review)
    
    0-49%    -> POOR ❌
             (Don't rely on this answer)

What the Score Measures:
    1. Relevance (40%):    Does it answer the question?
    2. Coherence (30%):    Is it clear and logical?
    3. Length (20%):       Is it appropriate length?
    4. Grounding (25%):    Based on your documents?
    5. Completeness (20%): Fully addresses question?

Hallucination Detection:
    ⚠️ Shown when: Answer makes claims not in your knowledge base
    Example: "We use quantum computers" (but not in your documents)
    Action: Review the answer, may need clarification
""")


# ==========================================
# 8. HANDLING EDGE CASES
# ==========================================

print("\n" + "="*70)
print("""
Edge Cases & How System Handles Them
=====================================

1. Question not in knowledge base
   -> Returns "Answer not found in knowledge base." ✅

2. Multiple documents match
   -> Returns the best match based on keyword overlap ✅

3. LLM timeout/unavailable
   -> Automatically falls back to retrieval-only ✅

4. Hallucination detected
   -> Flags in recommendations, shows low score ✅

5. Very short or very long answers
   -> Penalized in Length validator, quality score adjusted ✅

6. Unclear/grammatically incorrect text
   -> Caught by Coherence validator ✅
""")


# ==========================================
# 9. REAL WORLD EXAMPLES
# ==========================================

print("\n" + "="*70)
print("""
Real World Examples
===================

Query: "What is our company strategy?"
Expected: Company strategy document → Strategy info
Result: ✅ Works - returns relevant portions

Query: "net zero emission 2039"
Expected: Sustainability report → 2039 targets
Result: ✅ Works - returns Project Circular data

Query: "Who is the CEO?"
Expected: Org chart or employee database → CEO name
Result: May return "Answer not found" if not in KB
       (Add CEO info to knowledge base if needed)

Query: "pizza recipe"
Expected: Not in company documents → "Answer not found"
Result: ✅ Works - correctly returns "Answer not found"

Query: "What about competitors?"
Expected: If not in documents → "Answer not found"
       If in documents → Returns competitor analysis
Result: ✅ Depends on your knowledge base content
""")


# ==========================================
# 10. TROUBLESHOOTING
# ==========================================

print("\n" + "="*70)
print("""
Troubleshooting Guide
======================

Problem: Getting "Answer not found" but should find something
Solution:
    1. Lower the threshold: use threshold=0.5 instead of 0.8
    2. Check if document is in knowledge base
    3. Verify keywords are in the document
    4. Run: python load_all_knowledge_base.py again

Problem: LLM is slow
Solution:
    1. Set use_llm=False to skip LLM, use retrieval only
    2. Use Groq provider (fastest)
    3. Set max_tokens=100 for shorter responses
    4. Set generation_temperature=0.0 (no creativity = faster)

Problem: Low quality scores
Solution:
    1. Check if answer is grounded (hallucination detection)
    2. Try longer answer: max_tokens=500
    3. Improve context: lower threshold to find more docs
    4. Use different LLM provider

Problem: Hallucination detected
Solution:
    1. Review the answer manually
    2. Consider adding more source documents
    3. Verify answer facts against knowledge base
    4. This is normal - system is working correctly

Problem: Can't connect to LLM provider
Solution:
    1. Check API key is set correctly
    2. Verify internet connection
    3. Try fallback: system will use retrieval-only
    4. Check provider status page (OpenAI, Groq, etc.)
""")


# ==========================================
# 11. QUICK START SCRIPT
# ==========================================

print("\n" + "="*70)
print("QUICK START")
print("="*70)
print("""
Step 1: Load knowledge base (if not done already)
    python load_all_knowledge_base.py

Step 2: Start interactive session
    python rag_complete_pipeline.py

Step 3: Ask your questions!
    ❓ Your question: What is our company strategy?
    
That's it! You're ready to use your RAG system.

For detailed testing:
    python test_steps_6_7.py          # Test validation & LLM
    python test_advanced_qa.py         # Test retrieval
    python rag_complete_pipeline.py batch   # Batch testing
""")

print("\n" + "="*70)
print("✅ Your RAG System is Ready!")
print("="*70)

