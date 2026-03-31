"""
Local Embeddings Module
Handles text embedding generation using local models (sentence-transformers).
Used as fallback when OpenAI API is unavailable.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from config.settings import settings

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """
    Generates embeddings using local sentence-transformers models.
    Features:
    - No API calls needed (offline capability)
    - Lower latency
    - Deterministic (same results every time)
    - Model caching
    - GPU support when available
    
    Default model: all-MiniLM-L6-v2
    - 384 dimensions
    - Fast inference (~100ms per text)
    - Good semantic understanding
    """

    # Available models (cached locally)
    MODELS = {
        "all-MiniLM-L6-v2": 384,  # Fast, good quality (default)
        "all-mpnet-base-v2": 768,  # Slower, best quality
        "all-distilroberta-v1": 768,  # Fast, good quality
    }

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embedder with specified model.
        
        Args:
            model_name: Name of sentence-transformers model to use
        """
        if model_name not in self.MODELS:
            logger.warning(f"Unknown model {model_name}, using default")
            model_name = "all-MiniLM-L6-v2"

        self.model_name = model_name
        self.embedding_dimension = self.MODELS[model_name]
        
        # Set device (GPU if available)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
            self.model.eval()  # Set to evaluation mode
            logger.info(f"✓ Local embedder initialized: {model_name} ({self.embedding_dimension}D) on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> Dict:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process simultaneously (default 32)
            
        Returns:
            Dict with embeddings and metadata
        """
        if not texts:
            return {
                "success": False,
                "error": "Empty text list",
                "embeddings": [],
                "count": 0,
            }

        try:
            # Encode texts
            with torch.no_grad():
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    convert_to_tensor=False,
                    show_progress_bar=False,
                )

            # Convert to list of lists
            embeddings_list = [emb.tolist() for emb in embeddings]

            logger.info(f"✓ Generated {len(embeddings_list)} local embeddings")

            return {
                "success": True,
                "embeddings": embeddings_list,
                "count": len(embeddings_list),
                "dimension": self.embedding_dimension,
                "model": self.model_name,
                "device": self.device,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Batch embedding failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "embeddings": [],
                "count": 0,
            }

    def embed_single(self, text: str) -> Dict:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Dict with embedding vector and metadata
        """
        try:
            with torch.no_grad():
                embedding = self.model.encode([text], convert_to_tensor=False)[0]

            return {
                "success": True,
                "embedding": embedding.tolist(),
                "dimension": self.embedding_dimension,
                "model": self.model_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Single embedding failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "embedding": None,
            }

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)
            
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Similarity computation failed: {str(e)}")
            return 0.0

    def batch_similarity(self, query_embedding: List[float], embeddings: List[List[float]]) -> List[float]:
        """
        Compute similarity between query and multiple embeddings (vectorized).
        
        Args:
            query_embedding: Query embedding vector
            embeddings: List of embedding vectors
            
        Returns:
            List of similarity scores
        """
        try:
            query = np.array(query_embedding)
            emb_array = np.array(embeddings)
            
            # Normalize vectors
            query_norm = query / (np.linalg.norm(query) + 1e-8)
            emb_norms = emb_array / (np.linalg.norm(emb_array, axis=1, keepdims=True) + 1e-8)
            
            # Compute similarities (dot product of normalized vectors)
            similarities = np.dot(emb_norms, query_norm)
            
            return similarities.tolist()
        except Exception as e:
            logger.error(f"Batch similarity computation failed: {str(e)}")
            return [0.0] * len(embeddings)

    def get_model_info(self) -> Dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dimension,
            "device": self.device,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }


# Singleton instances for different models
_local_embedders = {}


def get_local_embedder(model_name: str = "all-MiniLM-L6-v2") -> LocalEmbedder:
    """Get or create local embedder instance for specified model."""
    if model_name not in _local_embedders:
        _local_embedders[model_name] = LocalEmbedder(model_name)
    return _local_embedders[model_name]
