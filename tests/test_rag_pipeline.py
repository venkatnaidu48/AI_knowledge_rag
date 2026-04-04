#!/usr/bin/env python
"""Quick test of complete RAG pipeline"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.disable(logging.CRITICAL)

from rag_complete_pipeline import RAGPipeline

pipeline = RAGPipeline(verbose=False)

tests = [
    "production 2024",
    "net zero emission 2039",
    "IIMA policies",
    "pizza recipe",
]

print("\n" + "="*90)
print("COMPLETE RAG PIPELINE TEST (Steps 5-7)")
print("="*90)

for q in tests:
    print(f"\n[Query] {q}")
    response = pipeline.process_query(q)
    print(f"[Found] {response.source_documents if response.source_documents else 'NOT FOUND'}")
    print(f"[Score] {response.validation_score:.1%} - {response.quality_level}")
    if response.hallucination_detected:
        print(f"[Alert] ⚠️ Hallucination Risk")
    preview = response.answer.replace('\n', ' ')[:100]
    print(f"[Reply] {preview}...")

pipeline.close()
print("\n" + "="*90)
