"""
FAISS Vector Index Manager
Handles index creation, loading, updating, and persistence.
"""

import logging
import os
import pickle
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
import faiss
from sqlalchemy.orm import Session

from src.database.models import DocumentChunk, ChunkEmbedding
from config.settings import settings

logger = logging.getLogger(__name__)


class FAISSIndexManager:
    """
    Manages FAISS vector index for similarity search.
    
    Features:
    - Automatic index creation from database embeddings
    - Index persistence (save/load from disk)
    - Dynamic index updates
    - Metadata mapping (FAISS ID ↔ Database ID)
    - Index statistics and health checks
    """

    INDEX_DIR = "./data/vector_index"
    INDEX_FILE = "chunks.index"
    METADATA_FILE = "chunks_metadata.pkl"

    def __init__(self, dimension: int = 1536):
        """
        Initialize FAISS index manager.
        
        Args:
            dimension: Embedding dimension (1536 for OpenAI, 384 for local model)
        """
        self.dimension = dimension
        self.index: Optional[faiss.IndexFlatL2] = None
        self.id_map: Dict[int, str] = {}  # FAISS index ID -> Chunk UUID
        self.reverse_map: Dict[str, int] = {}  # Chunk UUID -> FAISS index ID
        self.metadata: List[Dict] = []  # Metadata for each chunk
        self.embedding_count = 0
        
        # Create index directory if it doesn't exist
        os.makedirs(self.INDEX_DIR, exist_ok=True)
        logger.info(f"[OK] FAISS index manager initialized (dimension: {dimension}D)")

    def _initialize_index(self):
        """Initialize empty FAISS index."""
        # Use IndexFlatL2 for L2 distance (simplest, good for most use cases)
        # For larger datasets (millions), consider IndexIVFFlat or HNSW
        self.index = faiss.IndexFlatL2(self.dimension)
        logger.debug("Created new FAISS index (L2 distance)")

    def create_index_from_db(self, db: Session) -> Dict:
        """
        Create FAISS index from all embeddings in database.
        
        Args:
            db: Database session
            
        Returns:
            Dict with creation status and statistics
        """
        logger.info("Creating FAISS index from database embeddings...")
        
        try:
            # Fetch all chunks with embeddings
            query = db.query(
                DocumentChunk.id,
                ChunkEmbedding.embedding_vector,
                DocumentChunk.document_id,
                DocumentChunk.chunk_number,
                DocumentChunk.chunk_text,
            ).join(
                ChunkEmbedding,
                DocumentChunk.id == ChunkEmbedding.chunk_id
            ).all()

            if not query:
                logger.warning("No embeddings found in database")
                return {
                    "success": False,
                    "error": "No embeddings in database",
                    "count": 0,
                }

            logger.debug(f"Fetched {len(query)} embeddings from database")

            # Build vectors and metadata
            vectors = []
            detected_dimension = None
            
            for i, (chunk_id, embedding_vec, doc_id, chunk_num, chunk_text) in enumerate(query):
                try:
                    # Convert embedding to numpy array
                    if isinstance(embedding_vec, list):
                        vector = np.array(embedding_vec, dtype=np.float32)
                    elif isinstance(embedding_vec, np.ndarray):
                        vector = embedding_vec.astype(np.float32)
                    else:
                        vector = np.array(embedding_vec, dtype=np.float32)
                    
                    # Detect dimension from first embedding
                    if detected_dimension is None:
                        detected_dimension = vector.shape[0]
                        logger.info(f"Detected embedding dimension: {detected_dimension}D")
                        # Update FAISS manager dimension if needed
                        if detected_dimension != self.dimension:
                            logger.info(f"Dimension mismatch: FAISS initialized with {self.dimension}D but embeddings are {detected_dimension}D")
                            logger.info(f"Reinitializing FAISS index with {detected_dimension}D")
                            self.dimension = detected_dimension
                    
                    # Validate dimension consistency
                    if vector.shape[0] != detected_dimension:
                        logger.warning(f"Inconsistent dimension at row {i}: expected {detected_dimension}, got {vector.shape[0]}. Skipping this embedding.")
                        continue
                    
                    vectors.append(vector)
                    
                    # Map FAISS ID to chunk UUID
                    faiss_id = len(self.id_map)
                    self.id_map[faiss_id] = chunk_id
                    self.reverse_map[chunk_id] = faiss_id
                    
                    # Store metadata
                    self.metadata.append({
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "chunk_number": chunk_num,
                        "text_preview": chunk_text[:100] if chunk_text else "",
                        "indexed_at": datetime.utcnow().isoformat(),
                    })
                except Exception as row_error:
                    logger.error(f"Error processing row {i}: {type(row_error).__name__}: {str(row_error)}")
                    continue
            
            logger.debug(f"Converted {len(vectors)} valid embeddings to numpy arrays")
            
            if len(vectors) == 0:
                logger.error("No valid embeddings to add to index")
                return {
                    "success": False,
                    "error": "No valid embeddings after processing",
                    "count": 0,
                }
            
            # Add vectors to index
            try:
                # Reinitialize index with detected dimension
                if detected_dimension != self.dimension:
                    logger.info(f"Reinitializing FAISS index with detected dimension {detected_dimension}D")
                    self.index = faiss.IndexFlatL2(detected_dimension)
                    self.dimension = detected_dimension
                else:
                    self._initialize_index()
                
                vectors_array = np.array(vectors, dtype=np.float32)
                logger.debug(f"Created vectors array with shape: {vectors_array.shape}")
                
                if vectors_array.shape[0] == 0:
                    raise ValueError("No vectors to add to index")
                
                if vectors_array.shape[1] != self.dimension:
                    raise ValueError(f"Vector dimension mismatch: index is {self.dimension}D but vectors are {vectors_array.shape[1]}D")
                
                self.index.add(vectors_array)
                self.embedding_count = len(vectors)
                
                logger.info(f"[OK] Created FAISS index with {self.embedding_count} embeddings ({self.dimension}D)")
                
                return {
                    "success": True,
                    "count": self.embedding_count,
                    "dimension": self.dimension,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as faiss_error:
                logger.error(f"FAISS operation failed: {type(faiss_error).__name__}: {str(faiss_error)}")
                raise

        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Error creating index: {error_msg}")
            logger.debug(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg,
                "count": 0,
            }

    def add_embedding(self, chunk_id: str, embedding: List[float], metadata: Dict) -> bool:
        """
        Add single embedding to index.
        
        Args:
            chunk_id: UUID of chunk
            embedding: Embedding vector
            metadata: Metadata dict (document_id, chunk_number, text_preview)
            
        Returns:
            True if successful
        """
        try:
            if self.index is None:
                self._initialize_index()
            
            # Assign FAISS ID
            faiss_id = self.embedding_count
            self.embedding_count += 1
            
            # Add vector
            vector = np.array([embedding], dtype=np.float32)
            self.index.add(vector)
            
            # Update maps
            self.id_map[faiss_id] = chunk_id
            self.reverse_map[chunk_id] = faiss_id
            metadata["indexed_at"] = datetime.utcnow().isoformat()
            self.metadata.append(metadata)
            
            logger.debug(f"Added embedding for chunk {chunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding embedding: {str(e)}")
            return False

    def add_batch_embeddings(self, embeddings_data: List[Tuple[str, List[float], Dict]]) -> int:
        """
        Add multiple embeddings to index.
        
        Args:
            embeddings_data: List of (chunk_id, embedding_vector, metadata) tuples
            
        Returns:
            Number of embeddings added
        """
        try:
            if self.index is None:
                self._initialize_index()
            
            vectors = []
            chunk_ids = []
            metadatas = []
            
            for chunk_id, embedding, metadata in embeddings_data:
                vector = np.array(embedding, dtype=np.float32)
                vectors.append(vector)
                chunk_ids.append(chunk_id)
                metadatas.append(metadata)
            
            if not vectors:
                return 0
            
            # Add to index
            vectors_array = np.array(vectors, dtype=np.float32)
            start_id = self.embedding_count
            self.index.add(vectors_array)
            
            # Update maps
            for i, chunk_id in enumerate(chunk_ids):
                faiss_id = start_id + i
                self.id_map[faiss_id] = chunk_id
                self.reverse_map[chunk_id] = faiss_id
                metadatas[i]["indexed_at"] = datetime.utcnow().isoformat()
                self.metadata.append(metadatas[i])
            
            self.embedding_count += len(vectors)
            logger.info(f"Added {len(vectors)} embeddings to index")
            return len(vectors)
            
        except Exception as e:
            logger.error(f"Error adding batch: {str(e)}")
            return 0

    def search(self, query_embedding: List[float], k: int = 5) -> Dict:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            
        Returns:
            Dict with distances and metadata
        """
        if self.index is None or self.index.ntotal == 0:
            return {
                "success": False,
                "error": "Index is empty or not initialized",
                "results": [],
            }

        try:
            k = min(k, self.index.ntotal)  # Can't return more than index size
            
            # Convert to numpy array
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # Search (returns distances and indices)
            distances, indices = self.index.search(query_vector, k)
            
            results = []
            for i, (distance, faiss_id) in enumerate(zip(distances[0], indices[0])):
                if faiss_id == -1:  # Invalid result
                    continue
                
                chunk_id = self.id_map.get(int(faiss_id))
                if chunk_id and int(faiss_id) < len(self.metadata):
                    metadata = self.metadata[int(faiss_id)]
                    
                    # Convert L2 distance to similarity score (0-1)
                    # L2 distance is sqrt of sum of squared differences
                    similarity = 1.0 / (1.0 + float(distance))  # Convert to similarity
                    
                    results.append({
                        "rank": i + 1,
                        "chunk_id": chunk_id,
                        "document_id": metadata.get("document_id"),
                        "chunk_number": metadata.get("chunk_number"),
                        "text_preview": metadata.get("text_preview"),
                        "distance": float(distance),
                        "similarity": similarity,
                    })
            
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    def search_hybrid(
        self,
        query_embedding: List[float],
        document_id: Optional[str] = None,
        k: int = 5,
    ) -> Dict:
        """
        Hybrid search: similarity search with optional document filter.
        
        Args:
            query_embedding: Query vector
            document_id: Optional document to filter by
            k: Number of results
            
        Returns:
            Filtered search results
        """
        search_result = self.search(query_embedding, k=k * 2)  # Get more results to filter
        
        if not search_result["success"]:
            return search_result
        
        # Filter by document if specified
        if document_id:
            filtered_results = [
                r for r in search_result["results"]
                if r["document_id"] == document_id
            ]
            search_result["results"] = filtered_results[:k]
            search_result["count"] = len(filtered_results)
        else:
            search_result["results"] = search_result["results"][:k]
        
        return search_result

    def save_index(self) -> bool:
        """
        Save index and metadata to disk.
        
        Returns:
            True if successful
        """
        try:
            if self.index is None:
                logger.warning("Cannot save: index not initialized")
                return False
            
            # Save FAISS index
            index_path = os.path.join(self.INDEX_DIR, self.INDEX_FILE)
            faiss.write_index(self.index, index_path)
            logger.info(f"[OK] Saved FAISS index: {index_path}")
            
            # Save metadata
            metadata_path = os.path.join(self.INDEX_DIR, self.METADATA_FILE)
            with open(metadata_path, "wb") as f:
                pickle.dump({
                    "id_map": self.id_map,
                    "reverse_map": self.reverse_map,
                    "metadata": self.metadata,
                    "embedding_count": self.embedding_count,
                    "dimension": self.dimension,
                    "saved_at": datetime.utcnow().isoformat(),
                }, f)
            logger.info(f"[OK] Saved metadata: {metadata_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
            return False

    def load_index(self) -> Dict:
        """
        Load index and metadata from disk.
        
        Returns:
            Dict with load status
        """
        try:
            index_path = os.path.join(self.INDEX_DIR, self.INDEX_FILE)
            metadata_path = os.path.join(self.INDEX_DIR, self.METADATA_FILE)
            
            if not os.path.exists(index_path) or not os.path.exists(metadata_path):
                logger.warning("Index files not found on disk")
                return {
                    "success": False,
                    "error": "Index files not found",
                }
            
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            logger.info(f"[OK] Loaded FAISS index from {index_path}")
            
            # Load metadata
            with open(metadata_path, "rb") as f:
                data = pickle.load(f)
                self.id_map = data.get("id_map", {})
                self.reverse_map = data.get("reverse_map", {})
                self.metadata = data.get("metadata", [])
                self.embedding_count = data.get("embedding_count", 0)
                saved_at = data.get("saved_at")
            
            logger.info(f"[OK] Loaded metadata with {self.embedding_count} embeddings")
            
            return {
                "success": True,
                "count": self.embedding_count,
                "dimension": self.dimension,
                "saved_at": saved_at,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            "ntotal": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "embedding_count": self.embedding_count,
            "metadata_count": len(self.metadata),
            "id_map_size": len(self.id_map),
            "index_type": "IndexFlatL2",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def clear(self):
        """Clear index and metadata."""
        self._initialize_index()
        self.id_map.clear()
        self.reverse_map.clear()
        self.metadata.clear()
        self.embedding_count = 0
        logger.info("Index cleared")


# Singleton instance
_faiss_manager = None


def get_faiss_manager(dimension: int = 1536) -> FAISSIndexManager:
    """Get or create singleton FAISS manager."""
    global _faiss_manager
    if _faiss_manager is None:
        # Try to detect dimension from saved metadata
        metadata_path = os.path.join(FAISSIndexManager.INDEX_DIR, FAISSIndexManager.METADATA_FILE)
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "rb") as f:
                    data = pickle.load(f)
                    saved_dimension = data.get("dimension", dimension)
                    dimension = saved_dimension
                    logger.info(f"Detected dimension from saved metadata: {dimension}D")
            except Exception as e:
                logger.warning(f"Could not read saved dimension: {e}, using default {dimension}D")
        
        _faiss_manager = FAISSIndexManager(dimension=dimension)
        
        # Try to load existing index from disk
        load_result = _faiss_manager.load_index()
        if load_result.get("success"):
            logger.info(f"✓ Loaded existing FAISS index with {_faiss_manager.embedding_count} embeddings")
        else:
            logger.info("No existing FAISS index found, will create new one on first embedding")
    
    return _faiss_manager
