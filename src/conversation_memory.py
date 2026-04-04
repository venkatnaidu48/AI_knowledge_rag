"""
Conversation Memory System
Tracks conversation history and context for multi-turn interactions
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import json

Base = declarative_base()

class ConversationSession(Base):
    """Store conversation sessions"""
    __tablename__ = "conversation_sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ConversationMessage(Base):
    """Store individual messages in conversations"""
    __tablename__ = "conversation_messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    user_id = Column(String, index=True)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    quality_score = Column(Integer, nullable=True)
    hallucination_risk = Column(String, nullable=True)
    sources = Column(Text, nullable=True)  # JSON
    timestamp = Column(DateTime, default=datetime.utcnow)

class ConversationMemoryManager:
    """Manages conversation history and context"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, user_id: str, title: str = None) -> str:
        """Create a new conversation session"""
        import uuid
        session_id = str(uuid.uuid4())
        
        session = ConversationSession(
            id=session_id,
            user_id=user_id,
            title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
        self.db.add(session)
        self.db.commit()
        return session_id
    
    def add_message(self, session_id: str, user_id: str, role: str, 
                   content: str, quality_score: int = None, 
                   hallucination_risk: str = None, sources: List[str] = None) -> str:
        """Add a message to conversation"""
        import uuid
        message_id = str(uuid.uuid4())
        
        message = ConversationMessage(
            id=message_id,
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            quality_score=quality_score,
            hallucination_risk=hallucination_risk,
            sources=json.dumps(sources) if sources else None
        )
        self.db.add(message)
        self.db.commit()
        return message_id
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve conversation history"""
        messages = self.db.query(ConversationMessage)\
            .filter(ConversationMessage.session_id == session_id)\
            .order_by(ConversationMessage.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [{
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "quality_score": msg.quality_score,
            "hallucination_risk": msg.hallucination_risk,
            "sources": json.loads(msg.sources) if msg.sources else []
        } for msg in reversed(messages)]
    
    def get_session_context(self, session_id: str, max_context_len: int = 2000) -> str:
        """Build context string from recent conversation"""
        history = self.get_conversation_history(session_id)
        context = []
        
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context.append(f"{role_label}: {msg['content']}")
        
        # Join and truncate to max length
        full_context = "\n".join(context)
        return full_context[-max_context_len:] if len(full_context) > max_context_len else full_context
    
    def list_sessions(self, user_id: str) -> List[Dict]:
        """List user's conversation sessions"""
        sessions = self.db.query(ConversationSession)\
            .filter(ConversationSession.user_id == user_id)\
            .order_by(ConversationSession.updated_at.desc())\
            .all()
        
        return [{
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "is_active": s.is_active
        } for s in sessions]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session"""
        self.db.query(ConversationMessage).filter(
            ConversationMessage.session_id == session_id
        ).delete()
        self.db.query(ConversationSession).filter(
            ConversationSession.id == session_id
        ).delete()
        self.db.commit()
        return True
    
    def export_session(self, session_id: str) -> Dict:
        """Export conversation as JSON"""
        session = self.db.query(ConversationSession)\
            .filter(ConversationSession.id == session_id).first()
        
        if not session:
            return None
        
        history = self.get_conversation_history(session_id, limit=1000)
        
        return {
            "session_id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages": history
        }
