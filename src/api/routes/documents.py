"""
Document management API routes
Endpoints for uploading, listing, and deleting documents
"""

import logging
import os
import shutil
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query, status, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.settings import get_settings
from src.database import get_database_session
from src.database.models import Document, DocumentChunk
from src.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"],
)


# ============ Pydantic Models ============

class DocumentUploadResponse(BaseModel):
    """Response when uploading a document"""
    success: bool
    document_id: Optional[str] = None
    name: str
    chunks_created: int = 0
    file_size_bytes: Optional[int] = None
    quality_score: Optional[float] = None
    errors: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "abc123...",
                "name": "company-policy.pdf",
                "chunks_created": 45,
                "file_size_bytes": 512000,
                "quality_score": 0.92,
            }
        }


class DocumentMetadata(BaseModel):
    """Document metadata"""
    id: str
    name: str
    version: str
    upload_date: str
    department: Optional[str] = None
    sensitivity: str
    status: str
    chunks_count: int
    file_size_bytes: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123...",
                "name": "company-policy.pdf",
                "version": "1.0",
                "upload_date": "2026-03-02T10:30:00",
                "department": "HR",
                "sensitivity": "internal",
                "status": "active",
                "chunks_count": 45,
                "file_size_bytes": 512000,
            }
        }


class DocumentListResponse(BaseModel):
    """Response for listing documents"""
    total: int
    documents: List[DocumentMetadata]


# ============ Helper Functions ============

def ensure_upload_dir():
    """Ensure upload directory exists"""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file"""
    # Check file size
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not supported. Supported: .pdf, .docx, .txt, .xlsx"
        )
    
    return True


# ============ API Endpoints ============

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a document",
    description="Upload a document (PDF, DOCX, TXT, XLSX) for ingestion and chunking"
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT, XLSX)"),
    department: Optional[str] = Form(None, description="Department for document"),
    sensitivity: str = Form("internal", description="Sensitivity level: public, internal, confidential"),
    owner_email: Optional[str] = Form(None, description="Email of document owner"),
    db: Session = Depends(get_database_session),
):
    """
    Upload and process a document
    
    - **file**: Document file (PDF, DOCX, TXT, XLSX)
    - **department**: Optional department classification
    - **sensitivity**: Document sensitivity level
    - **owner_email**: Optional owner email for tracking
    
    Returns processing result with document ID and chunk count
    """
    
    try:
        # Validate file
        validate_file(file)
        
        # Ensure upload directory exists
        upload_dir = ensure_upload_dir()
        
        # Save uploaded file temporarily
        file_path = upload_dir / file.filename
        
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            logger.info(f"File saved: {file_path}, size: {len(content)} bytes")
            
            # Process document
            processor = DocumentProcessor(db)
            result = processor.process_document(
                file_path=str(file_path),
                document_name=file.filename,
                department=department,
                sensitivity=sensitivity,
                owner_email=owner_email,
            )
            
            # Clean up temp file after processing
            if file_path.exists() and result["chunks_created"] > 0:
                os.remove(file_path)
                logger.info(f"Temporary file deleted: {file_path}")
            
            return DocumentUploadResponse(
                success=result["success"],
                document_id=result.get("document_id"),
                name=file.filename,
                chunks_created=result.get("chunks_created", 0),
                file_size_bytes=result.get("file_size_bytes"),
                quality_score=result.get("quality_score"),
                errors=result.get("errors", []),
            )
        
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            
            # Clean up file if error
            if file_path.exists():
                try:
                    os.remove(file_path)
                except:
                    pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing document: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/list",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="Get list of all uploaded documents"
)
async def list_documents(
    department: Optional[str] = Query(None, description="Filter by department"),
    status_filter: Optional[str] = Query(None, description="Filter by status (active, archived, deprecated)"),
    db: Session = Depends(get_database_session),
):
    """
    Get list of all documents
    
    - **department**: Optional department filter
    - **status_filter**: Optional status filter
    
    Returns list of documents with metadata
    """
    
    try:
        query = db.query(Document)
        
        if department:
            query = query.filter(Document.department == department)
        
        if status_filter:
            query = query.filter(Document.status == status_filter)
        
        documents = query.all()
        
        doc_list = []
        for doc in documents:
            chunks_count = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).count()
            
            doc_list.append(DocumentMetadata(
                id=doc.id,
                name=doc.name,
                version=doc.version,
                upload_date=doc.upload_date.isoformat() if doc.upload_date else "",
                department=doc.department,
                sensitivity=doc.sensitivity,
                status=doc.status,
                chunks_count=chunks_count,
                file_size_bytes=doc.file_size_bytes or 0,
            ))
        
        return DocumentListResponse(
            total=len(doc_list),
            documents=doc_list,
        )
    
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving documents"
        )


@router.get(
    "/{document_id}",
    response_model=DocumentMetadata,
    summary="Get document details",
    description="Get details for a specific document"
)
async def get_document(
    document_id: str,
    db: Session = Depends(get_database_session),
):
    """Get details for a specific document"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}"
        )
    
    chunks_count = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).count()
    
    return DocumentMetadata(
        id=document.id,
        name=document.name,
        version=document.version,
        upload_date=document.upload_date.isoformat() if document.upload_date else "",
        department=document.department,
        sensitivity=document.sensitivity,
        status=document.status,
        chunks_count=chunks_count,
        file_size_bytes=document.file_size_bytes or 0,
    )


@router.delete(
    "/{document_id}",
    summary="Delete a document",
    description="Delete a document and all associated chunks"
)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_database_session),
):
    """Delete a document and associated chunks"""
    
    processor = DocumentProcessor(db)
    success = processor.delete_document(document_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}"
        )
    
    return {
        "success": True,
        "message": f"Document {document_id} deleted successfully"
    }
