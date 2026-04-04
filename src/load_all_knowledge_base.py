#!/usr/bin/env python
"""
COMPREHENSIVE KNOWLEDGE BASE LOADER
Automatically loads ALL documents from knowledge_base directory
Supports continuous document upload without model retraining
"""
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.database import SessionLocal
from src.database.models import Document, DocumentChunk
import logging

logging.disable(logging.CRITICAL)

def load_all_knowledge_base_documents():
    """Load ALL documents from knowledge_base directory recursively"""
    
    knowledge_base_path = Path(__file__).parent / "knowledge_base"
    db = SessionLocal()
    
    if not knowledge_base_path.exists():
        print(f"[ERROR] Knowledge base path not found: {knowledge_base_path}")
        return
    
    supported_extensions = {'.txt', '.md'}
    loaded_count = 0
    skipped_count = 0
    
    print(f"[INFO] Scanning knowledge_base directory: {knowledge_base_path}")
    print(f"[INFO] Looking for: {', '.join(supported_extensions)}\n")
    
    # Find all supported files
    all_files = knowledge_base_path.rglob('*')
    files_to_load = [f for f in all_files if f.is_file() and f.suffix.lower() in supported_extensions]
    
    print(f"[INFO] Found {len(files_to_load)} files to process\n")
    
    for file_path in sorted(files_to_load):
        try:
            # Read file
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            if not content.strip():
                print(f"[SKIP] Empty file: {file_path.relative_to(knowledge_base_path)}")
                skipped_count += 1
                continue
            
            # Create document name with relative path
            doc_name = f"{file_path.stem} ({file_path.parent.name})"
            
            # Check if already loaded
            existing = db.query(Document).filter_by(name=doc_name).first()
            if existing:
                print(f"[SKIP] Already loaded: {doc_name}")
                skipped_count += 1
                continue
            
            # Calculate hash
            file_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Create document
            doc = Document(
                name=doc_name,
                storage_path=str(file_path),
                category=file_path.parent.name,
                department="Knowledge Base",
                hash_md5=file_hash,
                file_size_bytes=len(content.encode()),
                status="active",
                processing_status="indexed"
            )
            
            db.add(doc)
            db.flush()  # Get the document ID
            
            # Split into chunks (by paragraphs or max 800 chars)
            chunks = content.split('\n\n')
            chunk_count = 0
            
            for chunk_idx, chunk in enumerate(chunks):
                chunk = chunk.strip()
                if len(chunk) < 50:  # Skip very small chunks
                    continue
                
                # Split large chunks further
                if len(chunk) > 800:
                    sub_chunks = [chunk[i:i+800] for i in range(0, len(chunk), 800)]
                else:
                    sub_chunks = [chunk]
                
                for sub_chunk in sub_chunks:
                    doc_chunk = DocumentChunk(
                        document_id=doc.id,
                        chunk_text=sub_chunk,
                        chunk_number=chunk_count,
                        tokens_count=len(sub_chunk.split()),
                        section_title=doc_name,
                        language="en"
                    )
                    db.add(doc_chunk)
                    chunk_count += 1
            
            db.commit()
            print(f"[LOAD] ✓ {doc_name} ({chunk_count} chunks)")
            loaded_count += 1
            
        except Exception as e:
            db.rollback()
            print(f"[ERROR] Failed to load {file_path.relative_to(knowledge_base_path)}: {str(e)}")
    
    db.close()
    
    print(f"\n[COMPLETE] Loaded: {loaded_count} | Skipped: {skipped_count}")
    print(f"[INFO] Total documents in database: {get_total_documents()}")

def get_total_documents():
    """Get total count of documents in database"""
    db = SessionLocal()
    count = db.query(Document).count()
    db.close()
    return count

if __name__ == "__main__":
    load_all_knowledge_base_documents()
