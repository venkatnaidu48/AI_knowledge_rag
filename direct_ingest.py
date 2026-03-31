#!/usr/bin/env python
"""
Direct batch ingestion into database
Bypasses API layer for speed. Chunks documents and stores directly.
"""
import sys
sys.path.insert(0, '.')

import logging
logging.disable(logging.CRITICAL)

from pathlib import Path
import hashlib
from src.database.database import SessionLocal
from src.database.models import Document, DocumentChunk
from src.document_processor.chunker import TextChunker

def ingest_all_documents():
    """Ingest all documents from knowledge_base folder"""
    kb_path = Path('./knowledge_base')
    all_files = list(kb_path.rglob('*.md')) + list(kb_path.rglob('*.txt'))
    
    if not all_files:
        print(f"❌ No files found in {kb_path}")
        return
    
    print("\n" + "="*80)
    print(f"📚 DIRECT DATABASE INGESTION ({len(all_files)} files)")
    print("="*80 + "\n")
    
    # Group by category
    categories = {}
    for file_path in sorted(all_files):
        parts = file_path.relative_to(kb_path).parts
        category = parts[0] if parts else 'miscellaneous'
        if category not in categories:
            categories[category] = []
        categories[category].append(file_path)
    
    chunker = TextChunker(chunk_size=500, chunk_overlap=50)
    db = SessionLocal()
    total_docs = 0
    total_chunks = 0
    
    try:
        for category in sorted(categories.keys()):
            print(f"📁 {category.upper()}")
            print("─" * 80)
            
            for file_path in categories[category]:
                try:
                    # Read file
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if not content.strip():
                        print(f"   ⏭️  SKIPPED (empty): {file_path.name}")
                        continue
                    
                    # Check if exists
                    existing = db.query(Document).filter(
                        Document.name == file_path.name
                    ).first()
                    
                    if existing:
                        print(f"   ⏭️  SKIPPED (exists): {file_path.name}")
                        continue
                    
                    # Create document with MD5 hash
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    doc = Document(
                        name=file_path.name,
                        category=category,
                        storage_path=str(file_path),
                        file_size_bytes=len(content),
                        hash_md5=content_hash,
                        status='active',
                        processing_status='indexed'  # Use 'indexed' instead of 'completed'
                    )
                    db.add(doc)
                    db.flush()
                    
                    # Chunk and store
                    chunks = chunker.chunk_semantic(content)
                    
                    if not chunks:
                        print(f"   ❌ NO CHUNKS: {file_path.name}")
                        db.rollback()
                        continue
                    
                    for i, chunk_text in enumerate(chunks):
                        chunk = DocumentChunk(
                            document_id=doc.id,
                            chunk_text=chunk_text,
                            chunk_number=i,
                            tokens_count=len(chunk_text.split()),
                            embedding_generated=False  # Will be generated later
                        )
                        db.add(chunk)
                    
                    db.commit()
                    print(f"   ✅ {file_path.name} ({len(chunks)} chunks)")
                    total_docs += 1
                    total_chunks += len(chunks)
                    
                except Exception as e:
                    db.rollback()
                    error_msg = str(e)[:80]
                    print(f"   ❌ ERROR: {file_path.name}")
                    print(f"      Details: {error_msg}")
            
            print()
        
        print("="*80)
        print(f"✅ INGESTION COMPLETE")
        print(f"   • Documents: {total_docs}")
        print(f"   • Chunks: {total_chunks}")
        print("="*80 + "\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    ingest_all_documents()
