"""
Main document processing pipeline
Orchestrates extraction, chunking, quality validation, and storage
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.database.models import Document, DocumentChunk
from src.document_processor.extractor import TextExtractor, calculate_md5, validate_text_quality
from src.document_processor.chunker import TextChunker, calculate_chunk_metadata

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessor:
    """Process documents: extract, chunk, validate, and store"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extractor = TextExtractor()
        self.chunker = TextChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            min_size=settings.MIN_CHUNK_SIZE,
        )
    
    def process_document(
        self,
        file_path: str,
        document_name: str,
        department: Optional[str] = None,
        sensitivity: str = "internal",
        owner_email: Optional[str] = None,
    ) -> Dict:
        """
        Full pipeline: extract → validate → chunk → store
        
        Returns:
            Result dict with status, document_id, chunks_created, etc.
        """
        result = {
            "success": False,
            "document_id": None,
            "document_name": document_name,
            "chunks_created": 0,
            "errors": [],
        }
        
        try:
            # Step 1: Check for duplicates
            logger.info(f"Processing document: {document_name}")
            file_hash = calculate_md5(file_path)
            
            existing = self.db.query(Document).filter(
                Document.hash_md5 == file_hash
            ).first()
            
            if existing:
                result["errors"].append(f"Duplicate document found: {existing.name} (ID: {existing.id})")
                logger.warning(f"Duplicate document detected: {existing.name}")
                return result
            
            # Step 2: Extract text
            logger.info("Extracting text...")
            extraction_result = self.extractor.extract(file_path)
            
            if not extraction_result["success"]:
                result["errors"].append(f"Extraction failed: {extraction_result.get('error', 'Unknown error')}")
                logger.error(f"Extraction failed: {extraction_result.get('error')}")
                return result
            
            text = extraction_result["text"]
            extraction_metadata = extraction_result.get("metadata", {})
            
            # Step 3: Validate text quality
            logger.info("Validating text quality...")
            quality_check = validate_text_quality(text, min_length=settings.MIN_CHUNK_SIZE)
            
            if not quality_check["is_valid"]:
                result["errors"].append(f"Text quality too low: {quality_check['issues']}")
                logger.warning(f"Text quality validation failed: {quality_check}")
                return result
            
            # Step 4: Create document record
            logger.info("Creating document record...")
            document = Document(
                id=str(uuid.uuid4()),
                name=document_name,
                version="1.0",
                department=department,
                owner_email=owner_email,
                sensitivity=sensitivity,
                storage_path=file_path,
                file_size_bytes=extraction_result["file_size_bytes"],
                hash_md5=file_hash,
                status="active",
                processing_status="indexed",
            )
            
            self.db.add(document)
            self.db.flush()  # Get ID without committing
            
            # Step 5: Chunk text
            logger.info("Chunking text...")
            chunks_text = self.chunker.chunk(text, strategy="semantic")
            
            if not chunks_text:
                result["errors"].append("No valid chunks created from text")
                logger.warning("No valid chunks created")
                self.db.rollback()
                return result
            
            # Step 6: Create chunk records
            logger.info(f"Creating {len(chunks_text)} chunk records...")
            chunks_created = 0
            
            for chunk_num, chunk_text in enumerate(chunks_text, 1):
                try:
                    metadata = calculate_chunk_metadata(chunk_text, chunk_num)
                    
                    chunk = DocumentChunk(
                        id=str(uuid.uuid4()),
                        document_id=document.id,
                        chunk_text=chunk_text,
                        chunk_number=chunk_num,
                        tokens_count=metadata["tokens_count"],
                        section_title=metadata.get("section_title", ""),
                        hierarchy_level=metadata.get("hierarchy_level", 0),
                        importance_score=metadata.get("importance_score", 0.5),
                        quality_score=quality_check["quality_score"],
                        language=metadata.get("language", "en"),
                        embedding_generated=False,
                    )
                    
                    self.db.add(chunk)
                    chunks_created += 1
                    
                except Exception as e:
                    logger.error(f"Error creating chunk {chunk_num}: {str(e)}")
                    result["errors"].append(f"Chunk {chunk_num} creation failed: {str(e)}")
            
            # Step 7: Commit to database
            logger.info("Committing to database...")
            self.db.commit()
            
            result["success"] = True
            result["document_id"] = document.id
            result["chunks_created"] = chunks_created
            result["extraction_metadata"] = extraction_metadata
            result["quality_score"] = quality_check["quality_score"]
            
            logger.info(f"✓ Document processed successfully: {chunks_created} chunks created")
            
        except Exception as e:
            logger.error(f"Unexpected error in document processing: {str(e)}", exc_info=True)
            result["errors"].append(f"Processing failed: {str(e)}")
            self.db.rollback()
        
        return result
    
    def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        return self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_number).all()
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document and all associated chunks"""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            
            if not document:
                logger.warning(f"Document not found: {document_id}")
                return False
            
            # Chunks are cascade deleted due to relationship definition
            self.db.delete(document)
            self.db.commit()
            
            logger.info(f"Document deleted: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            self.db.rollback()
            return False
