"""
RAG Pipeline - Main Orchestrator

Coordinates all pipeline components:
1. Retrieval - Find relevant documents
2. Ranking - Score and filter results
3. Context Building - Format for LLM
4. Generation - LLM creates answer
5. Validation - Check response quality
"""

import os
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass

from .retrieval import DocumentRetriever
from .ranking import ResultRanker
from .context_builder import ContextBuilder

logger = logging.getLogger(__name__)


@dataclass
class PipelineResponse:
    """Complete RAG pipeline response"""
    question: str
    answer: str
    context: str
    sources: List[str]
    confidence_score: float
    retrieved_docs: int
    generation_time_ms: float
    metadata: Dict


class RAGPipeline:
    """
    Complete Retrieval-Augmented Generation Pipeline.
    
    Process:
    1. Retrieve relevant documents from vector store
    2. Rank and filter results
    3. Build context for LLM
    4. Generate answer with LLM
    5. Validate response quality
    """
    
    def __init__(
        self,
        index_path: str = "./data/vector_index/faiss.index",
        metadata_path: str = "./data/vector_index/faiss_metadata.pkl",
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
        min_similarity: float = 0.3,
        max_context_length: int = 2000,
        verbose: bool = False,
    ):
        """
        Initialize RAG pipeline.
        
        Args:
            index_path: Path to FAISS index
            metadata_path: Path to metadata
            embedding_model: Embedding model name
            top_k: Number of documents to retrieve
            min_similarity: Minimum similarity threshold
            max_context_length: Maximum context length for LLM
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        
        # Initialize components
        logger.info("Initializing RAG Pipeline components...")
        
        self.retriever = DocumentRetriever(
            index_path=index_path,
            metadata_path=metadata_path,
            embedding_model=embedding_model,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        
        self.ranker = ResultRanker(
            similarity_weight=0.7,
            diversity_weight=0.2,
            quality_weight=0.1,
            enforce_diversity=True,
        )
        
        self.context_builder = ContextBuilder(
            max_context_length=max_context_length,
            context_format="default",
            include_source=True,
        )
        
        logger.info("RAG Pipeline initialized successfully")
    
    def process_query(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
    ) -> Dict:
        """
        Process user query through full pipeline.
        
        Args:
            query: User query
            top_k: Override top_k
            min_similarity: Override minimum similarity
            
        Returns:
            Dictionary with retrieval results
        """
        import time
        start_time = time.time()
        
        logger.info(f"Processing query: {query[:50]}...")
        
        # Step 1: Retrieve documents
        logger.debug("Step 1: Retrieving documents...")
        retrieved_docs = self.retriever.retrieve(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        logger.info(f"Retrieved {len(retrieved_docs)} documents")
        
        # Step 2: Rank results
        logger.debug("Step 2: Ranking results...")
        ranked_results = self.ranker.rank(retrieved_docs)
        logger.info(f"Ranked down to {len(ranked_results)} results")
        
        # Step 3: Build context
        logger.debug("Step 3: Building context...")
        context = self.context_builder.build(ranked_results)
        logger.info(f"Built context: {context.total_length} characters")
        
        elapsed_time = (time.time() - start_time) * 1000  # ms
        
        return {
            "query": query,
            "retrieved_documents": len(retrieved_docs),
            "ranked_results": len(ranked_results),
            "context": context.context_text,
            "sources": context.sources,
            "processing_time_ms": elapsed_time,
            "ranked_results_objects": ranked_results,
        }
    
    def close(self) -> None:
        """Clean up resources."""
        logger.info("Closing RAG Pipeline")
    
    def get_status(self) -> Dict:
        """Get pipeline status and statistics."""
        return {
            "retriever": self.retriever.get_stats(),
            "ranker": {
                "similarity_weight": self.ranker.similarity_weight,
                "diversity_weight": self.ranker.diversity_weight,
                "quality_weight": self.ranker.quality_weight,
            },
            "context_builder": {
                "max_length": self.context_builder.max_context_length,
                "format": self.context_builder.context_format,
            },
        }
