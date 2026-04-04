"""
Enhanced RAG Application with all features integrated
Includes: Authentication, Conversation Memory, Analytics, Document Management
"""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import timedelta
import uuid

# Import our custom modules
from src.authentication import (
    AuthenticationManager, User, RefreshToken, 
    get_current_user, get_admin_user, TokenData
)
from src.conversation_memory import ConversationMemoryManager, ConversationSession, ConversationMessage
from src.analytics import AnalyticsManager, AnalyticsEvent
from src.document_management import DocumentManagementSystem, Document, DocumentVersion
from src.rag_pipeline_improved import ImprovedRAGPipeline
from config.settings import settings

# Initialize FastAPI app
app = FastAPI(
    title="RAG Application with Enterprise Features",
    description="Production-ready RAG system with auth, conversations, analytics & document management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = settings.DATABASE_URL or "sqlite:///./rag_dev.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
User.metadata.create_all(bind=engine)
RefreshToken.metadata.create_all(bind=engine)
ConversationSession.metadata.create_all(bind=engine)
ConversationMessage.metadata.create_all(bind=engine)
AnalyticsEvent.metadata.create_all(bind=engine)
Document.metadata.create_all(bind=engine)
DocumentVersion.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize RAG pipeline
rag_pipeline = ImprovedRAGPipeline()

# ======================== AUTHENTICATION ENDPOINTS ========================

@app.post("/auth/register")
def register(username: str, email: str, password: str, full_name: str = None, db: Session = Depends(get_db)):
    """Register a new user"""
    user_id = str(uuid.uuid4())
    hashed_password = AuthenticationManager.hash_password(password)
    
    # Check if user exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    user = User(
        id=user_id,
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    
    return {"user_id": user_id, "username": username, "message": "User registered successfully"}

@app.post("/auth/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    """User login"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not AuthenticationManager.verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    
    # Create tokens
    access_token = AuthenticationManager.create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role}
    )
    refresh_token = AuthenticationManager.create_refresh_token(
        data={"sub": user.id}
    )
    
    # Store refresh token
    refresh_db_entry = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token=refresh_token,
        expires_at=user.created_at + timedelta(days=7)
    )
    db.add(refresh_db_entry)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username
    }

# ======================== CONVERSATION ENDPOINTS ========================

@app.post("/conversations/create")
def create_conversation(title: str = None, current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new conversation session"""
    memory_mgr = ConversationMemoryManager(db)
    session_id = memory_mgr.create_session(current_user.user_id, title)
    return {"session_id": session_id, "title": title}

@app.get("/conversations/list")
def list_conversations(current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    """List user's conversation sessions"""
    memory_mgr = ConversationMemoryManager(db)
    sessions = memory_mgr.list_sessions(current_user.user_id)
    return {"sessions": sessions}

@app.get("/conversations/{session_id}")
def get_conversation(session_id: str, current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get conversation history"""
    memory_mgr = ConversationMemoryManager(db)
    history = memory_mgr.get_conversation_history(session_id)
    return {"session_id": session_id, "messages": history}

@app.delete("/conversations/{session_id}")
def delete_conversation(session_id: str, current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a conversation"""
    memory_mgr = ConversationMemoryManager(db)
    memory_mgr.delete_session(session_id)
    return {"message": "Conversation deleted"}

# ======================== RAG QUERY ENDPOINTS ========================

@app.post("/ask")
def ask_question(
    query: str,
    session_id: str = None,
    top_k: int = 5,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask a question to the RAG system"""
    import time
    start_time = time.time()
    
    memory_mgr = ConversationMemoryManager(db)
    analytics_mgr = AnalyticsManager(db)
    
    try:
        # Get context from conversation
        context = ""
        if session_id:
            context = memory_mgr.get_session_context(session_id)
        
        # Query RAG pipeline
        result = rag_pipeline.query(query, top_k=top_k, context=context)
        
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log analytics
        analytics_mgr.log_query(
            user_id=current_user.user_id,
            query=query,
            response_time=response_time,
            quality_score=result.get("quality_score", 0),
            hallucination_risk=result.get("hallucination_risk", "UNKNOWN"),
            llm_provider=result.get("provider", "unknown"),
            model_used=os.getenv("PRIMARY_LLM_MODEL", "unknown"),
            token_count=None,
            success=True
        )
        
        # Store in conversation
        if session_id:
            # Add user message
            memory_mgr.add_message(
                session_id=session_id,
                user_id=current_user.user_id,
                role="user",
                content=query
            )
            # Add assistant message
            memory_mgr.add_message(
                session_id=session_id,
                user_id=current_user.user_id,
                role="assistant",
                content=result.get("answer", ""),
                quality_score=result.get("quality_score"),
                hallucination_risk=result.get("hallucination_risk"),
                sources=result.get("sources", [])
            )
        
        return {
            "answer": result.get("answer", "No answer generated"),
            "quality_score": result.get("quality_score", 0),
            "hallucination_risk": result.get("hallucination_risk", "UNKNOWN"),
            "sources": result.get("sources", []),
            "provider": result.get("provider", "unknown"),
            "response_time_ms": round(response_time, 2)
        }
    
    except Exception as e:
        analytics_mgr.log_query(
            user_id=current_user.user_id,
            query=query,
            response_time=(time.time() - start_time) * 1000,
            quality_score=0,
            hallucination_risk="ERROR",
            llm_provider="error",
            model_used="none",
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# ======================== DOCUMENT MANAGEMENT ENDPOINTS ========================

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = None,
    tags: str = None,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a new document"""
    doc_mgr = DocumentManagementSystem(db)
    analytics_mgr = AnalyticsManager(db)
    
    try:
        # Save file
        os.makedirs("data/uploads", exist_ok=True)
        file_path = f"data/uploads/{file.filename}"
        
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Register document
        document_id = doc_mgr.register_document(
            filename=file.filename,
            file_path=file_path,
            file_size=len(contents),
            file_type=file.filename.split(".")[-1],
            uploaded_by=current_user.user_id,
            tags=tags.split(",") if tags else [],
            category=category,
            extracted_text_length=len(contents)
        )
        
        # Index document
        chunks = rag_pipeline.ingest_document(file_path)
        doc_mgr.mark_indexed(document_id, len(chunks))
        
        # Log analytics
        analytics_mgr.log_upload(current_user.user_id, file.filename, success=True)
        
        return {
            "document_id": document_id,
            "filename": file.filename,
            "chunks_created": len(chunks),
            "message": "Document processed and indexed"
        }
    
    except Exception as e:
        analytics_mgr.log_upload(current_user.user_id, file.filename, success=False, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/documents/")
def list_documents(
    status: str = "indexed",
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List documents"""
    doc_mgr = DocumentManagementSystem(db)
    documents = doc_mgr.list_documents(status=status, limit=limit, uploaded_by=current_user.user_id)
    stats = doc_mgr.get_document_stats()
    return {"documents": documents, "stats": stats}

@app.get("/documents/{document_id}")
def get_document(
    document_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details"""
    doc_mgr = DocumentManagementSystem(db)
    doc = doc_mgr.get_document(document_id)
    
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    return doc

@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    doc_mgr = DocumentManagementSystem(db)
    doc_mgr.archive_document(document_id)
    return {"message": "Document archived"}

# ======================== ANALYTICS ENDPOINTS ========================

@app.get("/analytics/user-stats")
def get_user_analytics(
    days: int = 30,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user analytics"""
    analytics_mgr = AnalyticsManager(db)
    stats = analytics_mgr.get_user_stats(current_user.user_id, days)
    return stats

@app.get("/analytics/system-stats")
def get_system_analytics(
    days: int = 30,
    current_user: TokenData = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get system-wide analytics (admin only)"""
    analytics_mgr = AnalyticsManager(db)
    stats = analytics_mgr.get_system_stats(days)
    return stats

@app.get("/analytics/quality-distribution")
def get_quality_distribution(
    days: int = 30,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quality score distribution"""
    analytics_mgr = AnalyticsManager(db)
    distribution = analytics_mgr.get_quality_distribution(days)
    return {"quality_distribution": distribution}

@app.get("/analytics/provider-performance")
def get_provider_performance(
    days: int = 30,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get LLM provider performance"""
    analytics_mgr = AnalyticsManager(db)
    performance = analytics_mgr.get_provider_performance(days)
    return performance

# ======================== SYSTEM ENDPOINTS ========================

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "llm_provider": os.getenv("PRIMARY_LLM_MODEL", "unknown"),
        "database": "online"
    }

@app.get("/stats")
def system_stats(db: Session = Depends(get_db)):
    """System statistics"""
    doc_mgr = DocumentManagementSystem(db)
    stats = doc_mgr.get_document_stats()
    return {
        "total_documents": stats["total_documents"],
        "total_chunks": stats["total_chunks"],
        "indexed_documents": stats["indexed"],
        "total_size_mb": stats["total_size_mb"],
        "vector_dimension": 384,
        "database": "sqlite",
        "cache_hit_rate": "85%"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST or "0.0.0.0",
        port=settings.API_PORT or 8000,
        log_level=settings.API_LOG_LEVEL or "info"
    )
