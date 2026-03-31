#!/usr/bin/env python
"""Check database tables status"""
import sys
sys.path.insert(0, '.')

from src.database.database import engine
from sqlalchemy import inspect

print("=" * 80)
print("DATABASE TABLE CHECK")
print("=" * 80)

# Get inspector
inspector = inspect(engine)
tables = inspector.get_table_names()

print(f"\nTables in database: {tables}")
print(f"✓ Has 'documents': {'documents' in tables}")
print(f"✓ Has 'document_chunks': {'document_chunks' in tables}")
print(f"✓ Has 'chunk_embeddings': {'chunk_embeddings' in tables}")

if not tables:
    print("\n❌ NO TABLES FOUND! Database is empty!")
    print("\nFIX: Need to recreate tables...")
    
    # Try to recreate tables
    print("\nRecreating tables...")
    from src.database.models import Base
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Tables recreated successfully!")
        
        # Verify again
        tables = inspect(engine).get_table_names()
        print(f"Tables now: {tables}")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("\n✓ Database tables exist!")
    
    # Check if tables have data
    from src.database.database import SessionLocal
    from src.database.models import Document, DocumentChunk
    
    db = SessionLocal()
    try:
        doc_count = db.query(Document).count()
        chunk_count = db.query(DocumentChunk).count()
        print(f"\n✓ Documents: {doc_count}")
        print(f"✓ Chunks: {chunk_count}")
        
        if chunk_count == 0:
            print("\n⚠️ Tables exist but are EMPTY!")
            print("Need to reload knowledge base again...")
    finally:
        db.close()

print("\n" + "=" * 80)
