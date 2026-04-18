#!/usr/bin/env python
"""
CI/CD Workflow Debugger
Run this to identify and fix workflow issues
"""

import os
import sys
import subprocess

print("=" * 80)
print("🔍 CI/CD WORKFLOW DEBUGGER")
print("=" * 80)

# Check 1: Verify test files exist
print("\n✓ CHECKING TEST FILES:")
test_dir = "tests"
if os.path.exists(test_dir):
    test_files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
    print(f"   ✅ Found {len(test_files)} test files:")
    for f in test_files:
        print(f"      • {f}")
else:
    print(f"   ❌ Test directory not found: {test_dir}")

# Check 2: Verify requirements.txt exists
print("\n✓ CHECKING DEPENDENCIES:")
if os.path.exists("requirements.txt"):
    print("   ✅ requirements.txt exists")
else:
    print("   ❌ requirements.txt not found")

# Check 3: Verify pytest.ini exists
print("\n✓ CHECKING PYTEST CONFIG:")
if os.path.exists("pytest.ini"):
    print("   ✅ pytest.ini exists")
else:
    print("   ❌ pytest.ini not found")

# Check 4: Try running pytest
print("\n✓ RUNNING PYTEST:")
try:
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        print("   ✅ Tests passed!")
    else:
        print("   ⚠️  Some tests failed. Error output:")
        print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
        print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
except Exception as e:
    print(f"   ❌ Error running pytest: {e}")

print("\n" + "=" * 80)
print("\n💡 COMMON FIXES:")
print("   1. Make sure all imports in test files are correct")
print("   2. Verify requirements.txt has all dependencies")
print("   3. Check that no test files have syntax errors")
print("   4. Ensure pytest is installed: pip install pytest")
print("\n" + "=" * 80)
