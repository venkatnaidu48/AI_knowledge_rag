"""
Document Management System
Handles document versioning, metadata, and lifecycle management
"""

from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import json

Base = declarative_base()

class Document(Base):
    """Enhanced document model with metadata"""
    __tablename__ = "documents_metadata"
    
    id = Column(String, primary_key=True)
    filename = Column(String, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)  # bytes
    file_type = Column(String)  # pdf, docx, txt, etc.
    
    # Content metadata
    total_chunks = Column(Integer, default=0)
    extracted_text_length = Column(Integer)
    language = Column(String, default="english")
    
    # Versioning
    version = Column(Integer, default=1)
    parent_version_id = Column(String, nullable=True)
    
    # User & organization
    uploaded_by = Column(String, index=True)
    organization_id = Column(String, nullable=True)
    
    # Tags and categories
    tags = Column(Text, nullable=True)  # JSON array
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # Status and lifecycle
    status = Column(String, default="active")  # active, archived, deleted
    is_indexed = Column(Boolean, default=False)
    index_errors = Column(Text, nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

class DocumentVersion(Base):
    """Track document version history"""
    __tablename__ = "document_versions"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, index=True)
    version_number = Column(Integer)
    file_path = Column(String)
    file_size = Column(Integer)
    change_summary = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)

class DocumentTag(Base):
    """Document tags for categorization"""
    __tablename__ = "document_tags"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, index=True)
    tag = Column(String)

class DocumentManagementSystem:
    """Manages document lifecycle and metadata"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def register_document(self, filename: str, file_path: str, file_size: int,
                         file_type: str, uploaded_by: str, organization_id: str = None,
                         tags: List[str] = None, category: str = None,
                         description: str = None, extracted_text_length: int = 0) -> str:
        """Register a new document"""
        import uuid
        doc_id = str(uuid.uuid4())
        
        doc = Document(
            id=doc_id,
            filename=filename,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            uploaded_by=uploaded_by,
            organization_id=organization_id,
            tags=json.dumps(tags) if tags else None,
            category=category,
            description=description,
            extracted_text_length=extracted_text_length
        )
        self.db.add(doc)
        self.db.commit()
        
        # Add tags
        if tags:
            for tag in tags:
                self._add_tag(doc_id, tag)
        
        return doc_id
    
    def _add_tag(self, document_id: str, tag: str):
        """Add a tag to document"""
        import uuid
        tag_id = str(uuid.uuid4())
        
        tag_obj = DocumentTag(
            id=tag_id,
            document_id=document_id,
            tag=tag
        )
        self.db.add(tag_obj)
        self.db.commit()
    
    def update_document_status(self, document_id: str, status: str, chunk_count: int = None):
        """Update document status and indexing info"""
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        
        if doc:
            doc.status = status
            if chunk_count is not None:
                doc.total_chunks = chunk_count
            doc.is_indexed = (status == "indexed")
            self.db.commit()
    
    def mark_indexed(self, document_id: str, chunk_count: int):
        """Mark document as successfully indexed"""
        self.update_document_status(document_id, "indexed", chunk_count)
    
    def mark_index_error(self, document_id: str, error_message: str):
        """Mark document with indexing error"""
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "error"
            doc.index_errors = error_message
            self.db.commit()
    
    def archive_document(self, document_id: str):
        """Archive (soft delete) a document"""
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "archived"
            doc.archived_at = datetime.utcnow()
            self.db.commit()
    
    def delete_document(self, document_id: str):
        """Delete (hard delete) a document"""
        # Delete tags first
        self.db.query(DocumentTag).filter(DocumentTag.document_id == document_id).delete()
        # Delete versions
        self.db.query(DocumentVersion).filter(DocumentVersion.document_id == document_id).delete()
        # Delete document
        self.db.query(Document).filter(Document.id == document_id).delete()
        self.db.commit()
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get document metadata"""
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not doc:
            return None
        
        tags = self.db.query(DocumentTag).filter(DocumentTag.document_id == document_id).all()
        
        return {
            "id": doc.id,
            "filename": doc.filename,
            "original_filename": doc.original_filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "total_chunks": doc.total_chunks,
            "tags": [t.tag for t in tags],
            "category": doc.category,
            "description": doc.description,
            "status": doc.status,
            "is_indexed": doc.is_indexed,
            "uploaded_by": doc.uploaded_by,
            "uploaded_at": doc.uploaded_at.isoformat(),
            "version": doc.version
        }
    
    def list_documents(self, status: str = "indexed", limit: int = 50,
                      organization_id: str = None, uploaded_by: str = None) -> List[Dict]:
        """List documents with filtering"""
        query = self.db.query(Document).filter(Document.status == status)
        
        if organization_id:
            query = query.filter(Document.organization_id == organization_id)
        if uploaded_by:
            query = query.filter(Document.uploaded_by == uploaded_by)
        
        docs = query.order_by(Document.uploaded_at.desc()).limit(limit).all()
        
        return [{
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "total_chunks": d.total_chunks,
            "status": d.status,
            "uploaded_at": d.uploaded_at.isoformat(),
            "category": d.category
        } for d in docs]
    
    def get_document_stats(self) -> Dict:
        """Get document management statistics"""
        total = self.db.query(Document).count()
        indexed = self.db.query(Document).filter(Document.status == "indexed").count()
        archived = self.db.query(Document).filter(Document.status == "archived").count()
        errors = self.db.query(Document).filter(Document.status == "error").count()
        
        total_size = self.db.query(Document).filter(Document.status != "deleted").all()
        total_bytes = sum([d.file_size for d in total_size])
        
        total_chunks = sum([d.total_chunks for d in total_size])
        
        return {
            "total_documents": total,
            "indexed": indexed,
            "archived": archived,
            "errors": errors,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "total_chunks": total_chunks
        }
    
    def search_documents(self, query: str, limit: int = 20) -> List[Dict]:
        """Search documents by filename or tags"""
        # Search in filename
        results = self.db.query(Document)\
            .filter(Document.filename.ilike(f"%{query}%"))\
            .filter(Document.status != "deleted")\
            .limit(limit)\
            .all()
        
        # Also search in tags if not enough results
        if len(results) < limit:
            tag_results = self.db.query(DocumentTag)\
                .filter(DocumentTag.tag.ilike(f"%{query}%"))\
                .all()
            
            doc_ids = [tr.document_id for tr in tag_results]
            if doc_ids:
                tag_docs = self.db.query(Document)\
                    .filter(Document.id.in_(doc_ids))\
                    .filter(Document.status != "deleted")\
                    .all()
                results.extend(tag_docs)
                results = list(set(results))[:limit]
        
        return [{
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "category": d.category,
            "total_chunks": d.total_chunks
        } for d in results]
