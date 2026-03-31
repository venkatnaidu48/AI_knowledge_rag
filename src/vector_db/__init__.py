"""
Vector Database Module

Components:
- FAISS Index Manager: Index creation, persistence, updates
- Search Engine: High-level semantic search interface
"""

from src.vector_db.index_manager import FAISSIndexManager, get_faiss_manager
from src.vector_db.search_engine import VectorSearchEngine, get_search_engine

__all__ = [
    "FAISSIndexManager",
    "get_faiss_manager",
    "VectorSearchEngine",
    "get_search_engine",
]
