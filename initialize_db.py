#!/usr/bin/env python
"""
Database Initialization Script
Initializes SQLite database and creates all required tables
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("=" * 70)
print("DATABASE INITIALIZATION")
print("=" * 70)

try:
    print("\n[1/3] Importing database module...")
    from src.database.database import initialize_database, engine
    from src.database.models import Base
    print("✓ Database module imported")
    
    print("\n[2/3] Creating database tables...")
    initialize_database()
    print("✓ Database tables created successfully")
    
    print("\n[3/3] Verifying database...")
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n✓ Created {len(tables)} tables:")
    for table in sorted(tables):
        print(f"  ✓ {table}")
    
    print("\n" + "=" * 70)
    print("✓ DATABASE INITIALIZATION COMPLETE")
    print("=" * 70)
    print("\nDatabase Location: sqlite:///./rag_dev.db")
    print("Status: READY FOR USE")
    print("\nYou can now run:")
    print("  cd src")
    print("  python rag_pipeline_improved.py")
    print("=" * 70)

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
