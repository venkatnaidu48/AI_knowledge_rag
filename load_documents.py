#!/usr/bin/env python
"""
Load Documents into Database
Ingests documents from knowledge_base/ folder into SQLite
"""

import sys
import os
import hashlib
from pathlib import Path

# Add paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def calculate_md5(file_path):
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

print("=" * 80)
print("LOADING DOCUMENTS INTO DATABASE")
print("=" * 80)

try:
    print("\n[1/5] Initializing database connection...")
    from src.database.database import SessionLocal, initialize_database
    from src.database.models import Document, DocumentChunk
    from sqlalchemy.orm import Session
    
    # Ensure database is initialized
    initialize_database()
    print("✓ Database initialized")
    
    print("\n[2/5] Scanning knowledge_base folder...")
    
    knowledge_base_path = os.path.join(project_root, 'knowledge_base')
    if not os.path.exists(knowledge_base_path):
        print(f"✗ Knowledge base folder not found: {knowledge_base_path}")
        sys.exit(1)
    
    # Find all text files
    text_files = []
    for root, dirs, files in os.walk(knowledge_base_path):
        for file in files:
            if file.endswith(('.txt', '.md', '.markdown')):
                text_files.append(os.path.join(root, file))
    
    print(f"✓ Found {len(text_files)} documents")
    
    if len(text_files) == 0:
        print("⚠ No documents found in knowledge_base/")
        sys.exit(0)
    
    print("\n[3/5] Loading documents into database...")
    
    db = SessionLocal()
    loaded_count = 0
    
    try:
        for file_path in text_files[:10]:  # Limit to first 10 for demo
            try:
                # Read file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if not content or len(content) < 10:
                    continue
                
                # Get relative path
                rel_path = os.path.relpath(file_path, knowledge_base_path)
                
                # Check if already exists
                existing = db.query(Document).filter(
                    Document.name == rel_path
                ).first()
                
                if existing:
                    continue
                
                # Create document
                doc = Document(
                    name=rel_path,
                    storage_path=file_path,
                    file_size_bytes=len(content),
                    status='processed'
                )
                db.add(doc)
                db.flush()
                
                # Split into chunks (1000 char chunks)
                chunk_size = 1000
                chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                
                for chunk_idx, chunk_text in enumerate(chunks):
                    if len(chunk_text) > 10:
                        chunk = DocumentChunk(
                            document_id=doc.id,
                            chunk_text=chunk_text,
                            chunk_number=chunk_idx,
                            tokens_count=len(chunk_text.split())
                        )
                        db.add(chunk)
                
                db.commit()
                loaded_count += 1
                print(f"  ✓ Loaded: {rel_path} ({len(chunks)} chunks)")
                
            except Exception as e:
                db.rollback()
                print(f"  ⚠ Skipped: {os.path.basename(file_path)} - {str(e)[:50]}")
                continue
        
        db.close()
        
    except Exception as e:
        db.close()
        raise e
    
    print(f"\n[4/5] Verifying loaded data...")
    
    db = SessionLocal()
    doc_count = db.query(Document).count()
    chunk_count = db.query(DocumentChunk).count()
    db.close()
    
    print(f"✓ Documents in database: {doc_count}")
    print(f"✓ Chunks in database: {chunk_count}")
    
    if chunk_count == 0:
        print("\n⚠ No chunks were loaded!")
        print("This might happen if documents are empty or in unsupported format")
        sys.exit(1)
    
    print("\n[5/5] Done!")
    
    print("\n" + "=" * 80)
    print("✅ DOCUMENTS LOADED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nLoaded:")
    print(f"  • {doc_count} documents")
    print(f"  • {chunk_count} text chunks")
    print("\nYou can now run the pipeline:")
    print("  $ cd src")
    print("  $ python rag_pipeline_improved.py")
    print("  $ who is venkat?")
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
