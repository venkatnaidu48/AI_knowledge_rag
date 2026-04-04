"""
Query Pipeline - Query Processing Module
Handles user queries: embeddings, retrieval, context aggregation
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from src.embedding.processor import EmbeddingProcessor
from src.vector_db.search_engine import VectorSearchEngine
from src.database.models import Document, DocumentChunk, ChunkEmbedding

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Process user queries end-to-end:
    1. Generate embedding for query
    2. Perform semantic search
    3. Aggregate context from top results
    4. Build response with metadata
    """
    
    def __init__(self, embedding_processor: EmbeddingProcessor, search_engine: VectorSearchEngine):
        """
        Initialize query processor.
        
        Args:
            embedding_processor: For generating query embeddings
            search_engine: For semantic search in vector space
        """
        self.embedding_processor = embedding_processor
        self.search_engine = search_engine
        self.query_count = 0
        self.successful_queries = 0
        self.failed_queries = 0
        
    async def process_query(
        self,
        query: str,
        db: Session,
        k: int = 5,
        score_threshold: float = 0.3,
        include_context: bool = True,
        context_size: int = 1,
    ) -> Dict:
        """
        Process user query end-to-end.
        
        **Pipeline:**
        1. Validate query
        2. Generate embedding
        3. Search vector DB
        4. Retrieve full chunk details
        5. Aggregate context
        6. Return structured response
        
        Args:
            query: User question/search query
            db: Database session
            k: Top-k results to retrieve
            score_threshold: Minimum similarity threshold (0-1)
            include_context: Include surrounding chunks
            context_size: Number of surrounding chunks to include
        
        Returns:
            {
                "success": bool,
                "query": str,
                "query_embedding_dimension": int,
                "search_results": [{
                    "rank": int,
                    "chunk_id": str,
                    "document_id": str,
                    "document_title": str,
                    "chunk_number": int,
                    "similarity_score": float,
                    "text": str,
                    "context_chunks": [{...}]  # if include_context=True
                }],
                "result_count": int,
                "processing_time_ms": float,
                "timestamp": str
            }
        """
        self.query_count += 1
        start_time = datetime.now()
        
        try:
            # Validate input
            if not query or not isinstance(query, str):
                return self._error_response("Query must be non-empty string")
            
            query = query.strip()
            if len(query) < 2:
                return self._error_response("Query too short (minimum 2 characters)")
            
            if len(query) > 1000:
                return self._error_response("Query too long (maximum 1000 characters)")
            
            logger.info(f"Processing query: {query[:50]}...")
            
            # Generate query embedding
            query_embedding = await self._embed_query(query)
            if query_embedding is None:
                return self._error_response("Failed to generate query embedding")
            
            # Perform semantic search
            search_results = self.search_engine.search(
                query_embedding=query_embedding,
                k=k,
                score_threshold=score_threshold
            )
            
            if not search_results.get("success"):
                return self._error_response("Vector search failed")
            
            # Retrieve full details for each result
            detailed_results = []
            for result in search_results.get("results", []):
                chunk_id = result.get("chunk_id")
                chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.id == chunk_id
                ).first()
                
                if chunk:
                    document = db.query(Document).filter(
                        Document.id == chunk.document_id
                    ).first()
                    
                    chunk_response = {
                        "rank": result.get("rank"),
                        "chunk_id": chunk_id,
                        "document_id": chunk.document_id,
                        "document_title": document.name if document else "Unknown",
                        "document_department": document.department if document else None,
                        "chunk_number": chunk.chunk_number,
                        "similarity_score": result.get("similarity", 0.0),
                        "text": chunk.chunk_text,
                        "tokens": chunk.tokens_count,
                        "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
                    }
                    
                    # Add context chunks if requested
                    if include_context and context_size > 0:
                        context_chunks = db.query(DocumentChunk).filter(
                            DocumentChunk.document_id == chunk.document_id,
                            DocumentChunk.chunk_number.in_([
                                chunk.chunk_number - i for i in range(1, context_size + 1)
                            ] + [
                                chunk.chunk_number + i for i in range(1, context_size + 1)
                            ])
                        ).all()
                        
                        chunk_response["context_chunks"] = [
                            {
                                "chunk_number": c.chunk_number,
                                "text": c.chunk_text,
                            }
                            for c in sorted(context_chunks, key=lambda x: x.chunk_number)
                            if c.chunk_number != chunk.chunk_number
                        ]
                    
                    detailed_results.append(chunk_response)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.successful_queries += 1
            
            logger.info(f"[OK] Query processed: {len(detailed_results)} results in {processing_time:.1f}ms")
            
            return {
                "success": True,
                "query": query,
                "query_embedding_dimension": len(query_embedding),
                "search_results": detailed_results,
                "result_count": len(detailed_results),
                "processing_time_ms": processing_time,
            }
        
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Query processing error: {str(e)}")
            return self._error_response(f"Processing failed: {str(e)}")
    
    async def process_query_by_document(
        self,
        query: str,
        document_id: str,
        db: Session,
        k: int = 5,
        score_threshold: float = 0.3,
    ) -> Dict:
        """
        Process query restricted to specific document.
        
        Args:
            query: User question
            document_id: UUID of document to search within
            db: Database session
            k: Top-k results
            score_threshold: Minimum similarity
        
        Returns:
            Query response limited to document
        """
        self.query_count += 1
        
        try:
            if not query or len(query.strip()) < 2:
                return self._error_response("Invalid query")
            
            # Generate embedding
            query_embedding = await self._embed_query(query)
            if query_embedding is None:
                return self._error_response("Embedding failed")
            
            # Search within document
            results = self.search_engine.search_by_document(
                query_embedding=query_embedding,
                document_id=document_id,
                db=db,
                k=k,
                score_threshold=score_threshold,
            )
            
            if not results.get("success"):
                self.failed_queries += 1
                return self._error_response("Document search failed")
            
            # Retrieve full details
            detailed_results = []
            for result in results.get("results", []):
                chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.id == result.get("chunk_id")
                ).first()
                
                if chunk:
                    detailed_results.append({
                        "rank": result.get("rank"),
                        "chunk_id": chunk.id,
                        "chunk_number": chunk.chunk_number,
                        "similarity_score": result.get("similarity", 0.0),
                        "text": chunk.chunk_text,
                    })
            
            self.successful_queries += 1
            
            return {
                "success": True,
                "query": query,
                "document_id": document_id,
                "search_results": detailed_results,
                "result_count": len(detailed_results),
            }
        
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Document query error: {str(e)}")
            return self._error_response(f"Error: {str(e)}")
    
    async def process_query_by_department(
        self,
        query: str,
        department: str,
        db: Session,
        k: int = 5,
        score_threshold: float = 0.3,
    ) -> Dict:
        """
        Process query restricted to department's documents.
        Args:
            query: User question
            department: Department name
            db: Database session
            k: Top-k results
            score_threshold: Minimum similarity
        Returns:
            Query response limited to department
        """
        self.query_count += 1
        
        try:
            if not query or len(query.strip()) < 2:
                return self._error_response("Invalid query")
            
            if not department or len(department.strip()) < 1:
                return self._error_response("Invalid department")
            
            # Generate embedding
            query_embedding = await self._embed_query(query)
            if query_embedding is None:
                return self._error_response("Embedding failed")
            
            # Search by department
            results = self.search_engine.search_by_department(
                query_embedding=query_embedding,
                department=department,
                db=db,
                k=k,
                score_threshold=score_threshold,
            )
            
            if not results.get("success"):
                self.failed_queries += 1
                return self._error_response("Department search failed")
            
            # Retrieve full details
            detailed_results = []
            for result in results.get("results", []):
                chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.id == result.get("chunk_id")
                ).first()
                
                if chunk:
                    document = db.query(Document).filter(
                        Document.id == chunk.document_id
                    ).first()
                    
                    detailed_results.append({
                        "rank": result.get("rank"),
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "document_title": document.name if document else "Unknown",
                        "chunk_number": chunk.chunk_number,
                        "similarity_score": result.get("similarity", 0.0),
                        "text": chunk.chunk_text,
                    })
            
            self.successful_queries += 1
            
            return {
                "success": True,
                "query": query,
                "department": department,
                "search_results": detailed_results,
                "result_count": len(detailed_results),
            }
        
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Department query error: {str(e)}")
            return self._error_response(f"Error: {str(e)}")
    
    async def _embed_query(self, query: str) -> Optional[List[float]]:
        """
        Generate embedding for query text.
        
        Args:
            query: Query text
        
        Returns:
            Query embedding vector or None on error
        """
        try:
            # Use caching from embedding processor
            result = await self.embedding_processor.embed_chunk(query)
            if result.get("success"):
                return result.get("embedding")
            else:
                logger.error(f"Query embedding failed: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"Query embedding failed: {str(e)}")
            return None
    
    def _error_response(self, error_message: str) -> Dict:
        """Build error response."""
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_stats(self) -> Dict:
        """Get query processing statistics."""
        return {
            "total_queries": self.query_count,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": (
                self.successful_queries / self.query_count * 100
                if self.query_count > 0 else 0.0
            ),
        }
    
    def reset_stats(self):
        """Reset query statistics."""
        self.query_count = 0
        self.successful_queries = 0
        self.failed_queries = 0


# Singleton instance
_query_processor: Optional[QueryProcessor] = None


def get_query_processor(
    embedding_processor: Optional[EmbeddingProcessor] = None,
    search_engine: Optional[VectorSearchEngine] = None,
) -> QueryProcessor:
    """
    Get or create query processor singleton.
    
    Args:
        embedding_processor: Optional embedding processor instance
        search_engine: Optional search engine instance
    
    Returns:
        Singleton QueryProcessor instance
    """
    global _query_processor
    
    if _query_processor is None:
        if embedding_processor is None:
            from src.embedding.processor import get_embedding_processor
            embedding_processor = get_embedding_processor()
        
        if search_engine is None:
            from src.vector_db.search_engine import get_search_engine
            search_engine = get_search_engine()
        
        _query_processor = QueryProcessor(embedding_processor, search_engine)
        logger.info("[OK] Query processor initialized")
    
    return _query_processor
