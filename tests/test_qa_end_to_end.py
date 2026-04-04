#!/usr/bin/env python
"""
End-to-End Testing of Q&A System
Tests with annual report data
"""
import subprocess
import sys

def run_question(question):
    """Run question through Q&A system"""
    result = subprocess.run(
        [sys.executable, "qa_enhanced.py", question],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def main():
    print("\n" + "="*80)
    print("END-TO-END Q&A SYSTEM TEST")
    print("Annual Report 2024")
    print("="*80 + "\n")
    
    # Test cases with expected outcomes
    test_cases = [
        {
            "question": "What is the production for 2024?",
            "should_find": True,
            "category": "Annual Report"
        },
        {
            "question": "What was the reported production 2024?",
            "should_find": True,
            "category": "Annual Report"
        },
        {
            "question": "Tell me about renewable energy pipeline",
            "should_find": True,
            "category": "Annual Report"
        },
        {
            "question": "What is the renewables pipeline capacity?",
            "should_find": True,
            "category": "Annual Report"
        },
        {
            "question": "What are the major projects?",
            "should_find": True,
            "category": "Annual Report"
        },
        {
            "question": "What is the stock price?",
            "should_find": False,
            "category": "Not in Knowledge Base"
        },
        {
            "question": "How to cook pizza?",
            "should_find": False,
            "category": "Not in Knowledge Base"
        },
        {
            "question": "What are IIMA policies?",
            "should_find": True,
            "category": "HR Policy"
        },
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        question = test["question"]
        should_find = test["should_find"]
        category = test["category"]
        
        print(f"[TEST {i}] {category}")
        print(f"Q: {question}")
        
        answer = run_question(question)
        
        if answer.lower() == "answer not found":
            found = False
            status = "✓ PASS" if not should_find else "✗ FAIL"
            print(f"A: Answer not found")
            print(f"   {status}")
        else:
            found = True
            status = "✓ PASS" if should_find else "✗ FAIL"
            # Show preview
            preview = answer[:150] if len(answer) > 150 else answer
            preview = preview.replace('\n', ' ')
            print(f"A: {preview}...")
            print(f"   {status}")
        
        results.append({
            "question": question,
            "found": found,
            "expected": should_find,
            "passed": found == should_find
        })
        
        print()
    
    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print()
    
    # Show failures
    failures = [r for r in results if not r["passed"]]
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f['question']}")
            print(f"    Expected: {f['expected']}, Got: {f['found']}")
    else:
        print("✓ ALL TESTS PASSED!")
    
    print()

if __name__ == "__main__":
    main()
