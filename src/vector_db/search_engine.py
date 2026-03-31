"""
Vector Search Engine
High-level interface for similarity search with ranking and reranking.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from src.vector_db.index_manager import FAISSIndexManager, get_faiss_manager
from src.database.models import DocumentChunk, Document
from config.settings import settings

logger = logging.getLogger(__name__)


class VectorSearchEngine:
    """
    High-level search engine built on FAISS.
    
    Features:
    - Semantic search
    - Filtering by document/department
    - Result reranking and deduplication
    - Search statistics and logging
    - Context expansion (retrieve surrounding chunks)
    """

    def __init__(self, faiss_manager: Optional[FAISSIndexManager] = None):
        """
        Initialize search engine.
        
        Args:
            faiss_manager: FAISS manager instance (default: singleton)
        """
        self.faiss_manager = faiss_manager or get_faiss_manager()
        self.search_stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "total_results": 0,
            "failed_searches": 0,
        }
        logger.info("[OK] Vector search engine initialized")

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        score_threshold: float = 0.3,
    ) -> Dict:
        """
        Semantic similarity search.
        
        Args:
            query_embedding: Query vector (1536D for OpenAI, 384D for local)
            k: Number of results to return
            score_threshold: Minimum similarity threshold (0-1)
            
        Returns:
            Dict with results and metadata
        """
        self.search_stats["total_searches"] += 1
        
        try:
            result = self.faiss_manager.search(query_embedding, k=k)
            
            if not result["success"]:
                self.search_stats["failed_searches"] += 1
                return result
            
            # Filter by threshold
            filtered_results = [
                r for r in result["results"]
                if r["similarity"] >= score_threshold
            ]
            
            self.search_stats["successful_searches"] += 1
            self.search_stats["total_results"] += len(filtered_results)
            
            return {
                "success": True,
                "results": filtered_results,
                "count": len(filtered_results),
                "score_threshold": score_threshold,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            self.search_stats["failed_searches"] += 1
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "count": 0,
            }

    def search_with_context(
        self,
        query_embedding: List[float],
        db: Session,
        k: int = 5,
        context_size: int = 1,
        score_threshold: float = 0.3,
    ) -> Dict:
        """
        Search with expanded context (surrounding chunks).
        
        Args:
            query_embedding: Query vector
            db: Database session
            k: Number of top results
            context_size: Number of surrounding chunks to include
            score_threshold: Minimum similarity
            
        Returns:
            Results with expanded context
        """
        try:
            # Get top results
            search_result = self.search(query_embedding, k=k, score_threshold=score_threshold)
            
            if not search_result["success"]:
                return search_result
            
            # Expand with context
            expanded_results = []
            for result in search_result["results"]:
                chunk_id = result["chunk_id"]
                doc_id = result["document_id"]
                chunk_num = result["chunk_number"]
                
                # Get chunk and neighbors
                chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc_id,
                    DocumentChunk.chunk_number.between(
                        max(0, chunk_num - context_size),
                        chunk_num + context_size
                    )
                ).order_by(DocumentChunk.chunk_number).all()
                
                context_text = "\n---\n".join([c.chunk_text for c in chunks if c.chunk_text])
                
                result["context_chunks_count"] = len(chunks)
                result["context_text"] = context_text
                expanded_results.append(result)
            
            return {
                "success": True,
                "results": expanded_results,
                "count": len(expanded_results),
                "context_size": context_size,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Context search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    def search_by_document(
        self,
        query_embedding: List[float],
        document_id: str,
        db: Session,
        k: int = 5,
        score_threshold: float = 0.3,
    ) -> Dict:
        """
        Search within a specific document only.
        
        Args:
            query_embedding: Query vector
            document_id: Document to search within
            db: Database session
            k: Number of results
            score_threshold: Minimum similarity
            
        Returns:
            Results from document only
        """
        try:
            # Verify document exists
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found",
                    "results": [],
                }
            
            # Search and filter by document
            result = self.faiss_manager.search(query_embedding, k=k * 2)
            
            if not result["success"]:
                return result
            
            # Filter to document and by threshold
            filtered = [
                r for r in result["results"]
                if r["document_id"] == document_id and r["similarity"] >= score_threshold
            ][:k]
            
            self.search_stats["successful_searches"] += 1
            self.search_stats["total_results"] += len(filtered)
            
            return {
                "success": True,
                "results": filtered,
                "count": len(filtered),
                "document_id": document_id,
                "document_name": doc.name,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Document search failed: {str(e)}")
            self.search_stats["failed_searches"] += 1
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    def search_by_department(
        self,
        query_embedding: List[float],
        department: str,
        db: Session,
        k: int = 5,
        score_threshold: float = 0.3,
    ) -> Dict:
        """
        Search within documents of a specific department.
        
        Args:
            query_embedding: Query vector
            department: Department filter
            db: Database session
            k: Number of results
            score_threshold: Minimum similarity
            
        Returns:
            Results from department's documents
        """
        try:
            # Get document IDs for department
            doc_ids = db.query(Document.id).filter(
                Document.department == department
            ).all()
            
            doc_ids = [d[0] for d in doc_ids]
            if not doc_ids:
                return {
                    "success": True,
                    "results": [],
                    "count": 0,
                    "department": department,
                    "message": "No documents for this department",
                }
            
            # Search and filter
            result = self.faiss_manager.search(query_embedding, k=k * 3)
            
            if not result["success"]:
                return result
            
            # Filter to department and by threshold
            filtered = [
                r for r in result["results"]
                if r["document_id"] in doc_ids and r["similarity"] >= score_threshold
            ][:k]
            
            self.search_stats["successful_searches"] += 1
            self.search_stats["total_results"] += len(filtered)
            
            return {
                "success": True,
                "results": filtered,
                "count": len(filtered),
                "department": department,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Department search failed: {str(e)}")
            self.search_stats["failed_searches"] += 1
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    def get_chunk_details(self, chunk_id: str, db: Session) -> Dict:
        """
        Get full details for a chunk.
        
        Args:
            chunk_id: Chunk UUID
            db: Database session
            
        Returns:
            Full chunk data with document info
        """
        try:
            chunk = db.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id
            ).first()
            
            if not chunk:
                return {
                    "success": False,
                    "error": "Chunk not found",
                }
            
            doc = db.query(Document).filter(
                Document.id == chunk.document_id
            ).first()
            
            return {
                "success": True,
                "chunk": {
                    "id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "document_name": doc.name if doc else "Unknown",
                    "chunk_number": chunk.chunk_number,
                    "text": chunk.chunk_text,
                    "importance_score": chunk.importance_score,
                    "quality_score": chunk.quality_score,
                    "embedding_model": chunk.embedding_model,
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
                },
            }

        except Exception as e:
            logger.error(f"Error fetching chunk details: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_stats(self) -> Dict:
        """Get search statistics."""
        total_searches = self.search_stats["total_searches"]
        success_rate = (
            (self.search_stats["successful_searches"] / total_searches * 100)
            if total_searches > 0 else 0
        )
        
        return {
            "total_searches": self.search_stats["total_searches"],
            "successful_searches": self.search_stats["successful_searches"],
            "failed_searches": self.search_stats["failed_searches"],
            "success_rate_percent": round(success_rate, 2),
            "total_results_returned": self.search_stats["total_results"],
            "avg_results_per_search": (
                self.search_stats["total_results"] / self.search_stats["successful_searches"]
                if self.search_stats["successful_searches"] > 0 else 0
            ),
            "index_stats": self.faiss_manager.get_stats(),
        }

    def reset_stats(self):
        """Reset search statistics."""
        self.search_stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "total_results": 0,
            "failed_searches": 0,
        }
        logger.info("Search statistics reset")


# Singleton instance
_search_engine = None


def get_search_engine(faiss_manager: Optional[FAISSIndexManager] = None) -> VectorSearchEngine:
    """Get or create singleton search engine."""
    global _search_engine
    if _search_engine is None:
        _search_engine = VectorSearchEngine(faiss_manager)
    return _search_engine
