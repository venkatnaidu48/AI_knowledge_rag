"""
Analytics Dashboard System
Tracks usage metrics, response quality, and system performance
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from enum import Enum

Base = declarative_base()

class AnalyticsEvent(Base):
    """Track analytics events"""
    __tablename__ = "analytics_events"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    event_type = Column(String)  # 'query', 'upload', 'export', etc.
    query = Column(String, nullable=True)
    response_time = Column(Float)  # milliseconds
    quality_score = Column(Float)
    hallucination_risk = Column(String)
    llm_provider = Column(String)
    model_used = Column(String)
    token_count = Column(Integer, nullable=True)
    success = Column(Integer, default=1)  # 1 or 0
    error_message = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class AnalyticsManager:
    """Manages analytics and metrics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_query(self, user_id: str, query: str, response_time: float,
                  quality_score: float, hallucination_risk: str,
                  llm_provider: str, model_used: str, token_count: int = None,
                  success: bool = True, error: str = None) -> str:
        """Log a query event"""
        import uuid
        event_id = str(uuid.uuid4())
        
        event = AnalyticsEvent(
            id=event_id,
            user_id=user_id,
            event_type="query",
            query=query[:200],  # Truncate long queries
            response_time=response_time,
            quality_score=quality_score,
            hallucination_risk=hallucination_risk,
            llm_provider=llm_provider,
            model_used=model_used,
            token_count=token_count,
            success=1 if success else 0,
            error_message=error
        )
        self.db.add(event)
        self.db.commit()
        return event_id
    
    def log_upload(self, user_id: str, filename: str, success: bool = True, error: str = None):
        """Log a document upload event"""
        import uuid
        event_id = str(uuid.uuid4())
        
        event = AnalyticsEvent(
            id=event_id,
            user_id=user_id,
            event_type="upload",
            query=filename,
            response_time=0,
            quality_score=100 if success else 0,
            hallucination_risk="SAFE",
            llm_provider="system",
            model_used="none",
            success=1 if success else 0,
            error_message=error
        )
        self.db.add(event)
        self.db.commit()
    
    def get_user_stats(self, user_id: str, days: int = 30) -> Dict:
        """Get user statistics for the last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        events = self.db.query(AnalyticsEvent)\
            .filter(AnalyticsEvent.user_id == user_id)\
            .filter(AnalyticsEvent.timestamp >= start_date)\
            .all()
        
        if not events:
            return {
                "total_queries": 0,
                "total_uploads": 0,
                "avg_response_time": 0,
                "avg_quality_score": 0,
                "success_rate": 0,
                "top_providers": []
            }
        
        queries = [e for e in events if e.event_type == "query"]
        uploads = [e for e in events if e.event_type == "upload"]
        
        # Calculate average response time
        query_times = [e.response_time for e in queries if e.response_time > 0]
        avg_response_time = sum(query_times) / len(query_times) if query_times else 0
        
        # Calculate average quality
        query_scores = [e.quality_score for e in queries]
        avg_quality = sum(query_scores) / len(query_scores) if query_scores else 0
        
        # Calculate success rate
        successful = len([e for e in events if e.success == 1])
        success_rate = (successful / len(events)) * 100 if events else 0
        
        # Get top providers
        from collections import Counter
        providers = Counter([e.llm_provider for e in queries])
        top_providers = providers.most_common(3)
        
        return {
            "total_queries": len(queries),
            "total_uploads": len(uploads),
            "avg_response_time_ms": round(avg_response_time, 2),
            "avg_quality_score": round(avg_quality, 2),
            "success_rate": round(success_rate, 2),
            "top_providers": [{"provider": p, "count": c} for p, c in top_providers]
        }
    
    def get_system_stats(self, days: int = 30) -> Dict:
        """Get system-wide statistics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        events = self.db.query(AnalyticsEvent)\
            .filter(AnalyticsEvent.timestamp >= start_date)\
            .all()
        
        if not events:
            return {
                "total_events": 0,
                "total_queries": 0,
                "total_users": 0,
                "avg_quality_score": 0,
                "provider_usage": {}
            }
        
        queries = [e for e in events if e.event_type == "query"]
        unique_users = set([e.user_id for e in events])
        
        # Quality distribution
        quality_scores = [e.quality_score for e in queries]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Provider distribution
        from collections import Counter
        providers = Counter([e.llm_provider for e in queries])
        
        # Hallucination risk distribution
        hallucination_risks = Counter([e.hallucination_risk for e in queries])
        
        return {
            "total_events": len(events),
            "total_queries": len(queries),
            "total_users": len(unique_users),
            "avg_quality_score": round(avg_quality, 2),
            "provider_usage": dict(providers),
            "hallucination_risk_distribution": dict(hallucination_risks),
            "query_distribution_by_day": self._get_daily_distribution(queries)
        }
    
    def _get_daily_distribution(self, events: List) -> Dict:
        """Get distribution of events by day"""
        from collections import defaultdict
        distribution = defaultdict(int)
        
        for event in events:
            day = event.timestamp.strftime("%Y-%m-%d")
            distribution[day] += 1
        
        return dict(sorted(distribution.items()))
    
    def get_quality_distribution(self, days: int = 30) -> Dict:
        """Get quality score distribution"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        events = self.db.query(AnalyticsEvent)\
            .filter(AnalyticsEvent.event_type == "query")\
            .filter(AnalyticsEvent.timestamp >= start_date)\
            .all()
        
        # Bucket scores
        buckets = {
            "0-30": 0,
            "30-60": 0,
            "60-80": 0,
            "80-100": 0
        }
        
        for event in events:
            score = event.quality_score
            if score < 30:
                buckets["0-30"] += 1
            elif score < 60:
                buckets["30-60"] += 1
            elif score < 80:
                buckets["60-80"] += 1
            else:
                buckets["80-100"] += 1
        
        return buckets
    
    def get_provider_performance(self, days: int = 30) -> Dict:
        """Get performance metrics per LLM provider"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        events = self.db.query(AnalyticsEvent)\
            .filter(AnalyticsEvent.event_type == "query")\
            .filter(AnalyticsEvent.timestamp >= start_date)\
            .all()
        
        from collections import defaultdict
        providers = defaultdict(lambda: {"count": 0, "avg_time": 0, "avg_quality": 0, "errors": 0})
        
        for event in events:
            provider = event.llm_provider
            providers[provider]["count"] += 1
            providers[provider]["avg_time"] += event.response_time
            providers[provider]["avg_quality"] += event.quality_score
            if event.success == 0:
                providers[provider]["errors"] += 1
        
        # Calculate averages
        result = {}
        for provider, stats in providers.items():
            count = stats["count"]
            result[provider] = {
                "total_requests": count,
                "avg_response_time_ms": round(stats["avg_time"] / count, 2) if count > 0 else 0,
                "avg_quality_score": round(stats["avg_quality"] / count, 2) if count > 0 else 0,
                "error_count": stats["errors"]
            }
        
        return result
