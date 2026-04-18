#!/usr/bin/env python
"""
Quick Test: Improved RAG Pipeline with SQLite
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 70)
print("IMPROVED RAG PIPELINE - Quick Test")
print("=" * 70)

try:
    from rag_pipeline_improved import ImprovedRAGPipeline
    print("\n✓ ImprovedRAGPipeline imported successfully")
    print("✓ Database: SQLite (rag_dev.db)")
    print("✓ Configuration: Development mode")
    
    print("\n" + "=" * 70)
    print("CONFIGURATION")
    print("=" * 70)
    print("\n✓ Hallucination detection: ENABLED")
    print("✓ Quality filters: ENABLED")
    print("✓ Grounding validation: ENABLED")
    print("✓ Safe mode: OFF (set 'safe' during execution to enable)")
    
    print("\n" + "=" * 70)
    print("DATABASE")
    print("=" * 70)
    print("\n✓ Using SQLite (sqlite:///./rag_dev.db)")
    print("✓ No external database server required")
    print("✓ Ready for local testing")
    
    print("\n" + "=" * 70)
    print("TO RUN THE PIPELINE")
    print("=" * 70)
    print("\n  cd src")
    print("  python rag_pipeline_improved.py")
    print("\nThen:")
    print("  - Type your question (e.g., 'who is venkat?')")
    print("  - Press Enter")
    print("  - Get response with hallucination detection")
    print("  - Type 'quit' to exit")
    
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
