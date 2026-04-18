"""
Document Retrieval Module

Handles retrieval of relevant documents from FAISS vector store.
"""

import os
import pickle
import numpy as np
import faiss
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """Represents a retrieved document chunk"""
    chunk_id: int
    text: str
    source: str
    distance: float
    similarity_score: float  # 0.0-1.0 normalized


class DocumentRetriever:
    """
    Retrieves relevant documents from FAISS vector store.
    
    Process:
    1. Embed query using embedding model
    2. Search FAISS index for similar vectors
    3. Return documents with similarity scores
    """
    
    def __init__(
        self,
        index_path: str = "./data/vector_index/faiss.index",
        metadata_path: str = "./data/vector_index/faiss_metadata.pkl",
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
        min_similarity: float = 0.3,
    ):
        """
        Initialize retriever.
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata pickle file
            embedding_model: HuggingFace embedding model name
            top_k: Number of top results to retrieve
            min_similarity: Minimum similarity threshold (0.0-1.0)
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.top_k = top_k
        self.min_similarity = min_similarity
        
        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Load FAISS index and metadata
        self._load_index()
        self._load_metadata()
        
    def _load_index(self) -> None:
        """Load FAISS index from file."""
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"FAISS index not found: {self.index_path}")
        
        try:
            self.index = faiss.read_index(self.index_path)
            logger.info(
                f"Loaded FAISS index: {self.index.ntotal} vectors, "
                f"{self.index.d} dimensions"
            )
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            raise
    
    def _load_metadata(self) -> None:
        """Load metadata mapping from pickle file."""
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")
        
        try:
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            logger.info(f"Loaded metadata: {len(self.metadata)} chunks")
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            raise
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
    ) -> List[RetrievedDocument]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: User query string
            top_k: Override default top_k
            min_similarity: Override default similarity threshold
            
        Returns:
            List of RetrievedDocument sorted by relevance
        """
        top_k = top_k or self.top_k
        min_similarity = min_similarity if min_similarity is not None else self.min_similarity
        
        try:
            # Embed query
            query_vector = self._embed_query(query)
            
            # Search FAISS index
            distances, indices = self.index.search(query_vector, top_k)
            
            # Convert results to RetrievedDocument objects
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx == -1:  # Invalid index
                    continue
                
                # Convert distance to similarity (cosine similarity: 1 - distance)
                similarity = self._distance_to_similarity(distance)
                
                # Filter by minimum similarity
                if similarity < min_similarity:
                    continue
                
                # Get metadata for this chunk
                if idx not in self.metadata:
                    logger.warning(f"Metadata not found for chunk {idx}")
                    continue
                
                chunk_data = self.metadata[idx]
                
                doc = RetrievedDocument(
                    chunk_id=int(idx),
                    text=chunk_data.get('text', ''),
                    source=chunk_data.get('source', 'unknown'),
                    distance=float(distance),
                    similarity_score=float(similarity),
                )
                results.append(doc)
            
            logger.info(f"Retrieved {len(results)} documents for query (top_{top_k})")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    def _embed_query(self, query: str) -> np.ndarray:
        """
        Embed query string to vector.
        
        Args:
            query: Query text
            
        Returns:
            Embedding vector (1, embedding_dim)
        """
        embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return np.array([embedding], dtype=np.float32)
    
    @staticmethod
    def _distance_to_similarity(distance: float) -> float:
        """
        Convert FAISS distance to similarity score (0.0-1.0).
        
        For cosine distance: similarity = 1 - distance
        Clipped to [0, 1] range.
        
        Args:
            distance: FAISS distance value
            
        Returns:
            Similarity score (0.0-1.0)
        """
        similarity = 1.0 - distance
        return max(0.0, min(1.0, similarity))
    
    def get_stats(self) -> Dict[str, any]:
        """Get retriever statistics."""
        return {
            "index_vectors": self.index.ntotal,
            "embedding_dimension": self.embedding_dim,
            "metadata_chunks": len(self.metadata),
            "top_k": self.top_k,
            "min_similarity": self.min_similarity,
        }
