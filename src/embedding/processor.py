"""
Embedding Processor Module
Orchestrates embedding generation with caching, fallback strategies, and batch processing.
"""

import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.models import DocumentChunk, ChunkEmbedding
from src.embedding.openai_embedder import get_openai_embedder, OpenAIEmbedder
from src.embedding.local_embedder import get_local_embedder, LocalEmbedder
from src.embedding.cache import get_embedding_cache, EmbeddingCache
from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingProcessor:
    """
    Orchestrates embedding generation with intelligent fallback and caching.
    Flow:
    1. Check cache for existing embeddings
    2. Generate missing embeddings via OpenAI (primary) or local model (fallback)
    3. Store generated embeddings in cache
    4. Persist embeddings to database
    5. Track costs and usage
    """

    def __init__(self):
        """Initialize embedding processor with all backends."""
        self.openai_embedder: OpenAIEmbedder = get_openai_embedder()
        self.local_embedder: LocalEmbedder = get_local_embedder("all-MiniLM-L6-v2")
        self.cache: EmbeddingCache = get_embedding_cache()
        self.stats = {
            "total_chunks_processed": 0,
            "cached_hits": 0,
            "openai_generated": 0,
            "local_generated": 0,
            "total_tokens_used": 0,
            "total_cost_usd": 0.0,
            "errors": 0,
        }
        logger.info("[OK] Embedding processor initialized")

    def embed_chunk(self, chunk_text: str, use_secondary: bool = False) -> Dict:
        """
        Generate embedding for a single chunk (synchronous wrapper).
        
        Args:
            chunk_text: Text of chunk to embed
            use_secondary: Force use of local model (for testing/fallback)
            
        Returns:
            Dict with embedding, model used, and metadata
        """
        # 1. Check cache
        cached_embedding = self.cache.get(chunk_text)
        if cached_embedding:
            self.stats["cached_hits"] += 1
            logger.debug(f"Cache hit for chunk embedding")
            return {
                "success": True,
                "embedding": cached_embedding,
                "source": "cache",
                "model": "cached",
                "dimension": len(cached_embedding),
            }

        # 2. Generate new embedding
        try:
            if use_secondary or not settings.OPENAI_API_KEY:
                # Use local model
                result = self.local_embedder.embed_single(chunk_text)
                if result["success"]:
                    embedding = result["embedding"]
                    self.cache.set(chunk_text, embedding)
                    self.stats["local_generated"] += 1
                    return {
                        "success": True,
                        "embedding": embedding,
                        "source": "local_model",
                        "model": result.get("model"),
                        "dimension": result.get("dimension"),
                    }
            else:
                # Use OpenAI (primary)
                result = self.openai_embedder.embed_single(chunk_text)
                if result["success"]:
                    embedding = result["embedding"]
                    self.cache.set(chunk_text, embedding)
                    self.stats["openai_generated"] += 1
                    self.stats["total_tokens_used"] += result.get("tokens_used", 0)
                    self.stats["total_cost_usd"] += result.get("cost", 0)
                    return {
                        "success": True,
                        "embedding": embedding,
                        "source": "openai",
                        "model": "text-embedding-3-small",
                        "dimension": result.get("dimension"),
                        "tokens": result.get("tokens_used", 0),
                    }
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {str(e)}, falling back to local")
            result = self.local_embedder.embed_single(chunk_text)
            if result["success"]:
                embedding = result["embedding"]
                self.cache.set(chunk_text, embedding)
                self.stats["local_generated"] += 1
                return {
                    "success": True,
                    "embedding": embedding,
                    "source": "local_model_fallback",
                    "model": result.get("model"),
                    "dimension": result.get("dimension"),
                }

        # All embedding sources failed
        self.stats["errors"] += 1
        logger.error(f"Failed to generate embedding for chunk")
        return {
            "success": False,
            "error": "All embedding sources failed",
            "embedding": None,
        }

    async def embed_batch(
        self,
        chunk_texts: List[str],
        use_secondary: bool = False,
    ) -> Dict:
        """
        Generate embeddings for multiple chunks with intelligent batching.
        
        Args:
            chunk_texts: List of chunk texts to embed
            use_secondary: Force use of local model
            
        Returns:
            Dict with embeddings list, statistics, and errors
        """
        logger.info(f"Starting batch embedding for {len(chunk_texts)} chunks")
        
        # 1. Check cache for existing embeddings
        cached_embeddings, missing_texts = self.cache.get_batch(chunk_texts)
        
        if not missing_texts:
            logger.info(f"[OK] All {len(chunk_texts)} chunks found in cache")
            return {
                "success": True,
                "embeddings": cached_embeddings,
                "count": len(cached_embeddings),
                "from_cache": len(cached_embeddings),
                "newly_generated": 0,
                "stats": self.get_stats(),
            }

        # 2. Generate missing embeddings
        logger.info(f"Generating {len(missing_texts)} new embeddings")
        new_embeddings = []
        generation_errors = []

        try:
            if use_secondary or not settings.OPENAI_API_KEY:
                # Use local model for batch
                result = self.local_embedder.embed_batch(missing_texts)
                if result["success"]:
                    new_embeddings = result["embeddings"]
                    self.stats["local_generated"] += len(new_embeddings)
                    source = "local_model"
                else:
                    generation_errors.append(result.get("error"))
            else:
                # Use OpenAI for batch (via async)
                result = await self.openai_embedder.embed_batch_async(missing_texts)
                if result["success"]:
                    new_embeddings = result["embeddings"]
                    self.stats["openai_generated"] += len(new_embeddings)
                    self.stats["total_tokens_used"] += result.get("tokens_used", 0)
                    self.stats["total_cost_usd"] += result.get("cost", 0)
                    source = "openai"
                else:
                    generation_errors.append(result.get("error"))

        except Exception as e:
            logger.warning(f"OpenAI batch failed: {str(e)}, falling back to local")
            result = self.local_embedder.embed_batch(missing_texts)
            if result["success"]:
                new_embeddings = result["embeddings"]
                self.stats["local_generated"] += len(new_embeddings)
                source = "local_model_fallback"
            else:
                generation_errors.append(result.get("error"))
                self.stats["errors"] += len(missing_texts)

        # 3. Cache new embeddings
        if new_embeddings:
            cached_count = self.cache.set_batch(missing_texts, new_embeddings)
            logger.info(f"Cached {cached_count} new embeddings")

        # 4. Merge cached and new embeddings
        final_embeddings = []
        for i, text in enumerate(chunk_texts):
            if cached_embeddings[i] is not None:
                final_embeddings.append(cached_embeddings[i])
            else:
                # Find corresponding new embedding
                missing_idx = missing_texts.index(text) if text in missing_texts else -1
                if missing_idx >= 0 and missing_idx < len(new_embeddings):
                    final_embeddings.append(new_embeddings[missing_idx])
                else:
                    final_embeddings.append(None)

        self.stats["total_chunks_processed"] += len(chunk_texts)

        return {
            "success": len(generation_errors) == 0,
            "embeddings": final_embeddings,
            "count": len(final_embeddings),
            "from_cache": len(cached_embeddings) - missing_texts.__len__(),
            "newly_generated": len(new_embeddings),
            "source": source if new_embeddings else "cache",
            "errors": generation_errors,
            "stats": self.get_stats(),
        }

    def embed_chunks_for_document(
        self,
        db: Session,
        document_id: str,
        chunk_ids: Optional[List[str]] = None,
        use_secondary: bool = False,
    ) -> Dict:
        """
        Generate embeddings for all chunks of a document and persist to DB.
        
        Args:
            db: Database session
            document_id: Document ID
            chunk_ids: Optional list of chunk IDs to embed (default: all)
            use_secondary: Force use of local model
            
        Returns:
            Dict with result status and statistics
        """
        logger.info(f"Embedding document {document_id}")

        try:
            # Fetch chunks from database
            query = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            )
            
            if chunk_ids:
                query = query.filter(DocumentChunk.id.in_(chunk_ids))

            chunks = query.all()
            if not chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return {
                    "success": False,
                    "error": "No chunks found",
                    "embedded_count": 0,
                }

            # Extract text content
            chunk_texts = [chunk.chunk_text for chunk in chunks]
            logger.info(f"Embedding {len(chunks)} chunks for document {document_id}")

            # Generate embeddings (sync wrapper around async)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.embed_batch(chunk_texts, use_secondary))
            loop.close()

            if not result["success"]:
                logger.error(f"Batch embedding failed: {result.get('errors')}")
                return result

            # Persist embeddings to database
            embedded_count = 0
            for i, (chunk, embedding) in enumerate(zip(chunks, result["embeddings"])):
                if embedding is None:
                    logger.warning(f"Skipping chunk {chunk.id} - no embedding generated")
                    continue

                # Store primary embedding
                chunk_embedding = ChunkEmbedding(
                    chunk_id=chunk.id,
                    embedding_vector=embedding,
                    embedding_model="text-embedding-3-small",
                )
                db.add(chunk_embedding)

                # Mark chunk as embedded
                chunk.embedding_generated = True
                chunk.embedding_timestamp = datetime.utcnow()
                chunk.embedding_model = "text-embedding-3-small"
                embedded_count += 1

            db.commit()
            logger.info(f"✓ Persisted {embedded_count} embeddings to database")

            return {
                "success": True,
                "document_id": document_id,
                "embedded_count": embedded_count,
                "from_cache": result["from_cache"],
                "newly_generated": result["newly_generated"],
                "source": result.get("source"),
                "stats": self.get_stats(),
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error embedding document: {str(e)}")
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e),
                "embedded_count": 0,
            }

    def get_stats(self) -> Dict:
        """Get embedding processor statistics."""
        return {
            "total_chunks_processed": self.stats["total_chunks_processed"],
            "cached_hits": self.stats["cached_hits"],
            "openai_generated": self.stats["openai_generated"],
            "local_generated": self.stats["local_generated"],
            "total_tokens_used": self.stats["total_tokens_used"],
            "total_cost_usd": round(self.stats["total_cost_usd"], 6),
            "cache_stats": self.cache.get_stats(),
            "errors": self.stats["errors"],
        }

    def reset_stats(self):
        """Reset all statistics."""
        self.stats = {
            "total_chunks_processed": 0,
            "cached_hits": 0,
            "openai_generated": 0,
            "local_generated": 0,
            "total_tokens_used": 0,
            "total_cost_usd": 0.0,
            "errors": 0,
        }
        self.cache.reset_stats()
        logger.info("Embedding processor statistics reset")


# Singleton instance
_embedding_processor = None


def get_embedding_processor() -> EmbeddingProcessor:
    """Get or create singleton embedding processor instance."""
    global _embedding_processor
    if _embedding_processor is None:
        _embedding_processor = EmbeddingProcessor()
    return _embedding_processor
