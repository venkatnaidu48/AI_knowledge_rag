#!/usr/bin/env python
"""Test advanced Q&A system"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.disable(logging.CRITICAL)

from qa_advanced_full import AdvancedQASystem

system = AdvancedQASystem()

print("\n" + "="*80)
print("ADVANCED Q&A SYSTEM - FULL KNOWLEDGE BASE TEST")
print("="*80 + "\n")

#Test cases
tests = [
    ("production 2024", 0.5, "Annual Report"),
    ("net zero emission 2039", 0.5, "Sustainability"),
    ("IIMA policies", 0.6, "HR Policy"),
    ("stock price Apple", 0.8, "Unrelated"),
]

for question, threshold, description in tests:
    print(f"[{description}] Threshold: {int(threshold*100)}%")
    print(f"Q: {question}")
    answer = system.get_answer(question, threshold=threshold)
    
    # Show first 200 chars
    preview = answer.replace('\n', ' ')[:200]
    print(f"A: {preview}...\n")

system.close()
print("="*80)
