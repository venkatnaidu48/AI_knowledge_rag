#!/usr/bin/env python
"""Complete Fix: Recreate DB tables and reload knowledge base"""
import sys
sys.path.insert(0, '.')

import subprocess
import time

print("=" * 80)
print("COMPLETE DATABASE & KNOWLEDGE BASE RESTORATION")
print("=" * 80)

# Step 1: Recreate tables
print("\n[STEP 1/2] Recreating database tables...")
from src.database.database import engine, Base
from src.database.models import *

try:
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")
except Exception as e:
    print(f"✗ Error creating tables: {e}")
    sys.exit(1)

# Step 2: Reload knowledge base
print("\n[STEP 2/2] Reloading knowledge base...")
print("(This will take 5-10 minutes)")
print()

try:
    result = subprocess.run(
        [sys.executable, "load_knowledge_base.py"],
        capture_output=False,
        timeout=3600
    )
    
    if result.returncode == 0:
        print("\n✓ Knowledge base reload complete!")
        print("=" * 80)
        print("✅ SYSTEM READY FOR Q&A!")
        print("=" * 80)
    else:
        print(f"\n✗ Error during knowledge base load (exit code: {result.returncode})")
        sys.exit(1)
        
except subprocess.TimeoutExpired:
    print("\n✗ Timeout waiting for knowledge base load")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Error: {e}")
    sys.exit(1)
