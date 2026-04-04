#!/usr/bin/env python
"""
FINAL END-TO-END Q&A SYSTEM DEMONSTRATION
Shows working RAG system with annual report data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress logging
import logging
logging.disable(logging.CRITICAL)

from qa_production import search_knowledge_base, display_result

print("\n" + "="*80)
print("RAG SYSTEM - FINAL DEMONSTRATION")
print(f"Annual Report and Knowledge Base Q&A")
print("="*80 + "\n")

test_queries = [
    "What is the production for 2024?",
    "Tell me about renewables pipeline capacity",
    "What are major projects",
    "What is the stock price of Apple?",
    "How to cook pizza?"
]

for query in test_queries:
    print(f"Q: {query}")
    result = search_knowledge_base(query)
    answer = display_result(query, result)
    
    # Show answer preview
    lines = answer.split('\n')
    for line in lines[:3]:
        if line.strip():
            print(f"   {line[:70]}")
    
    if len(answer) > 200:
        print(f"   [Answer length: {len(answer)} chars, truncated...]")
    
    print()

print("="*80)
print("END-TO-END TEST COMPLETED")
print("="*80)
