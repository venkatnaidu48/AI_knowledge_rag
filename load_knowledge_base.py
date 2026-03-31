#!/usr/bin/env python
"""
Automated Knowledge Base Loader
Scans knowledge_base directory, chunks all files, generates embeddings, and indexes them.
Usage: python load_knowledge_base.py
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import io

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

# Fix encoding on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_kb.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from config.settings import get_settings
from src.database.database import Base
from src.database.models import Document, DocumentChunk, ChunkEmbedding
from src.document_processor import DocumentProcessor
from src.embedding.processor import EmbeddingProcessor
from src.vector_db.index_manager import FAISSIndexManager, get_faiss_manager


class KnowledgeBaseLoader:
    """Loads and processes all knowledge base documents"""

    def __init__(self):
        """Initialize loader with database and processing components"""
        self.settings = get_settings()
        self.engine = create_engine(
            self.settings.DATABASE_URL,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        
        # Initialize processors
        self.doc_processor = DocumentProcessor(self.db)
        self.embedding_processor = EmbeddingProcessor()
        self.faiss_manager = get_faiss_manager()
        
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "total_embeddings": 0,
            "errors": [],
        }
        
        logger.info("[OK] Knowledge Base Loader initialized")

    def get_kb_files(self) -> List[Path]:
        """Scan knowledge_base directory for supported file types"""
        kb_path = Path("./knowledge_base")
        
        if not kb_path.exists():
            logger.error(f"Knowledge base directory not found: {kb_path}")
            return []
        
        supported_extensions = {'.txt', '.md', '.pdf', '.docx', '.xlsx'}
        files = []
        
        for file_path in kb_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                files.append(file_path)
        
        logger.info(f"Found {len(files)} knowledge base files to process")
        return sorted(files)

    def get_department_from_path(self, file_path: Path) -> str:
        """Extract department from file path"""
        parts = file_path.parts
        if len(parts) >= 2:
            # knowledge_base/DEPARTMENT/...
            return parts[1].lower().replace('_', ' ').title()
        return "General"

    def process_single_file(self, file_path: Path) -> Tuple[bool, Dict]:
        """Process a single file: extract, chunk, embed, index"""
        
        try:
            filename = file_path.name
            department = self.get_department_from_path(file_path)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing: {filename} | Department: {department}")
            logger.info(f"{'='*80}")
            
            # Step 1: Process document (extract + chunk)
            logger.info("[1/4] Extracting and chunking...")
            result = self.doc_processor.process_document(
                file_path=str(file_path),
                document_name=filename,
                department=department,
                sensitivity="internal",
                owner_email=None,
            )
            
            if not result["success"]:
                logger.error(f"[FAILED] Processing failed: {result.get('errors', ['Unknown error'])}")
                self.stats["failed_files"] += 1
                self.stats["errors"].append({
                    "file": filename,
                    "error": result.get("errors", ["Unknown"])[0] if result.get("errors") else "Unknown"
                })
                return False, result
            
            document_id = result["document_id"]
            chunks_created = result["chunks_created"]
            
            logger.info(f"[OK] Created {chunks_created} chunks")
            self.stats["total_chunks"] += chunks_created
            
            # Step 2: Get all chunks from database
            logger.info("[2/4] Retrieving chunks from database...")
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            if not chunks:
                logger.error("No chunks found in database after processing")
                return False, {"success": False, "error": "No chunks in DB"}
            
            logger.info(f"[OK] Retrieved {len(chunks)} chunks")
            
            # Step 3: Generate embeddings
            logger.info(f"[3/4] Generating embeddings for {len(chunks)} chunks...")
            embeddings_created = 0
            
            for i, chunk in enumerate(chunks, 1):
                try:
                    # Generate embedding for chunk text
                    embed_result = self.embedding_processor.embed_chunk(
                        chunk.chunk_text,
                        use_secondary=False
                    )
                    
                    if embed_result["success"]:
                        embedding_vector = embed_result["embedding"]
                        
                        # Store in database
                        chunk_embedding = ChunkEmbedding(
                            chunk_id=chunk.id,
                            embedding_vector=embedding_vector,
                            embedding_model=embed_result.get("model", "unknown"),
                        )
                        self.db.add(chunk_embedding)
                        embeddings_created += 1
                        
                        if i % 10 == 0:
                            logger.info(f"  [OK] Embedded {i}/{len(chunks)} chunks")
                    else:
                        logger.warning(f"Failed to embed chunk {i}: {embed_result.get('error')}")
                
                except Exception as e:
                    logger.error(f"Error embedding chunk {i}: {str(e)}")
            
            # Commit embeddings to database
            self.db.commit()
            logger.info(f"[OK] Created {embeddings_created} embeddings")
            self.stats["total_embeddings"] += embeddings_created
            
            # Step 4: Index in FAISS
            logger.info("[4/4] Indexing embeddings in FAISS...")
            try:
                # Rebuild FAISS index from database
                index_result = self.faiss_manager.create_index_from_db(self.db)
                if index_result["success"]:
                    logger.info(f"[OK] Indexed {index_result.get('count', 0)} embeddings in FAISS")
                    # Save index to disk
                    save_result = self.faiss_manager.save_index()
                    if save_result["success"]:
                        logger.info("[OK] FAISS index saved to disk")
                    else:
                        logger.warning(f"[WARNING] Failed to save FAISS index: {save_result.get('error')}")
                else:
                    logger.warning(f"[WARNING] Failed to index: {index_result.get('error')}")
            except Exception as e:
                logger.error(f"Error indexing in FAISS: {str(e)}")
            
            logger.info(f"[OK] Successfully processed: {filename}")
            self.stats["processed_files"] += 1
            
            return True, {
                "success": True,
                "filename": filename,
                "document_id": document_id,
                "chunks": chunks_created,
                "embeddings": embeddings_created,
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error processing {file_path.name}: {str(e)}")
            self.stats["failed_files"] += 1
            self.stats["errors"].append({
                "file": file_path.name,
                "error": str(e)
            })
            return False, {"success": False, "error": str(e)}

    def load_all(self):
        """Load and process all knowledge base files"""
        
        try:
            # Get all files
            kb_files = self.get_kb_files()
            self.stats["total_files"] = len(kb_files)
            
            if not kb_files:
                logger.error("No knowledge base files found!")
                return False
            
            logger.info(f"\nStarting to process {len(kb_files)} files...")
            start_time = time.time()
            
            # Process each file
            for idx, file_path in enumerate(kb_files, 1):
                logger.info(f"\n[{idx}/{len(kb_files)}] Processing file...")
                success, details = self.process_single_file(file_path)
                
                # Small delay between files
                if idx < len(kb_files):
                    time.sleep(0.5)
            
            # Calculate total time
            elapsed_time = time.time() - start_time
            
            # Print summary
            self._print_summary(elapsed_time)
            
            return True
        
        except Exception as e:
            logger.error(f"Fatal error in load_all: {str(e)}")
            return False
        
        finally:
            self.db.close()

    def _print_summary(self, elapsed_time: float):
        """Print processing summary"""
        summary = f"""
{'='*80}
KNOWLEDGE BASE LOADING COMPLETE
{'='*80}
Total Files:          {self.stats['total_files']}
Successfully Processed: {self.stats['processed_files']}
Failed:               {self.stats['failed_files']}
Total Chunks:         {self.stats['total_chunks']}
Total Embeddings:     {self.stats['total_embeddings']}
Elapsed Time:         {elapsed_time:.2f} seconds
{'='*80}

STATISTICS:
- Average chunks per file: {self.stats['total_chunks'] // max(self.stats['processed_files'], 1):.1f}
- Average processing time: {elapsed_time / max(self.stats['total_files'], 1):.2f}s per file
- Success rate: {(self.stats['processed_files'] / max(self.stats['total_files'], 1) * 100):.1f}%
"""
        logger.info(summary)
        
        # Print errors if any
        if self.stats["errors"]:
            logger.info("\nERRORS:")
            for error in self.stats["errors"]:
                logger.error(f"  - {error['file']}: {error['error']}")


def main():
    """Main entry point"""
    try:
        logger.info("Starting Knowledge Base Loader...")
        loader = KnowledgeBaseLoader()
        
        success = loader.load_all()
        
        if success:
            logger.info("\n[OK] Knowledge base loaded successfully!")
            sys.exit(0)
        else:
            logger.error("\n[FAILED] Knowledge base loading failed!")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
