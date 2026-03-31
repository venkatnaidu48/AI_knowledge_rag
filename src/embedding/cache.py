"""
Embedding Cache Module
Handles caching of embeddings in Redis to avoid recomputation.
TTL: 30 days for standard embeddings, 90 days for frequently accessed chunks.
"""

import json
import hashlib
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import redis
from redis import ConnectionPool, Redis

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Redis-based caching layer for embeddings.
    Features:
    - Automatic TTL management (30 days default)
    - Hash-based key generation
    - Batch operations
    - Statistics tracking
    - Graceful fallback if Redis unavailable
    """

    # Redis connection parameters
    DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
    CACHE_PREFIX = "embedding:"
    STATS_PREFIX = "embedding_stats:"

    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Initialize cache with optional Redis connection.
        
        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            ttl_seconds: Time-to-live for cached embeddings
        """
        self.ttl_seconds = ttl_seconds
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client: Optional[Redis] = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "errors": 0,
        }
        
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection with error handling."""
        if not self.redis_url:
            logger.warning("Redis URL not configured, cache disabled")
            return

        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"✓ Redis cache connected: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed, cache disabled: {str(e)}")
            self.redis_client = None

    def _generate_key(self, text: str) -> str:
        """
        Generate cache key from text using SHA256 hash.
        
        Args:
            text: Text to hash
            
        Returns:
            Cache key prefixed with "embedding:"
        """
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        return f"{self.CACHE_PREFIX}{hash_hex}"

    def _generate_keys(self, texts: List[str]) -> List[str]:
        """Generate cache keys for multiple texts."""
        return [self._generate_key(text) for text in texts]

    def get(self, text: str) -> Optional[List[float]]:
        """
        Retrieve embedding from cache.
        
        Args:
            text: Text whose embedding to retrieve
            
        Returns:
            Embedding vector if found, None otherwise
        """
        if not self.redis_client:
            return None

        try:
            key = self._generate_key(text)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                self.stats["hits"] += 1
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return data.get("embedding")
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            logger.error(f"Cache retrieval error: {str(e)}")
            self.stats["errors"] += 1
            return None

    def get_batch(self, texts: List[str]) -> Tuple[List[Optional[List[float]]], List[str]]:
        """
        Retrieve embeddings for multiple texts.
        
        Args:
            texts: List of texts
            
        Returns:
            Tuple of (embeddings list, keys of missing texts)
        """
        if not self.redis_client:
            return [None] * len(texts), texts

        embeddings = []
        missing_texts = []
        
        try:
            keys = self._generate_keys(texts)
            cached_data_list = self.redis_client.mget(keys)
            
            for i, (text, key, cached_data) in enumerate(zip(texts, keys, cached_data_list)):
                if cached_data:
                    data = json.loads(cached_data)
                    embeddings.append(data.get("embedding"))
                    self.stats["hits"] += 1
                else:
                    embeddings.append(None)
                    missing_texts.append(text)
                    self.stats["misses"] += 1
            
            logger.info(f"Batch cache: {len(texts) - len(missing_texts)} hits, {len(missing_texts)} misses")
            return embeddings, missing_texts
            
        except Exception as e:
            logger.error(f"Batch cache retrieval error: {str(e)}")
            self.stats["errors"] += 1
            return [None] * len(texts), texts

    def set(self, text: str, embedding: List[float], ttl_seconds: Optional[int] = None) -> bool:
        """
        Store embedding in cache.
        
        Args:
            text: Original text
            embedding: Embedding vector
            ttl_seconds: Optional TTL override (default: 30 days)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            key = self._generate_key(text)
            ttl = ttl_seconds or self.ttl_seconds
            
            data = {
                "embedding": embedding,
                "text_preview": text[:100],
                "cached_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat(),
            }
            
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(data),
            )
            
            self.stats["writes"] += 1
            logger.debug(f"Cached embedding for text: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Cache write error: {str(e)}")
            self.stats["errors"] += 1
            return False

    def set_batch(self, texts: List[str], embeddings: List[List[float]], ttl_seconds: Optional[int] = None) -> int:
        """
        Store multiple embeddings in cache.
        
        Args:
            texts: List of texts
            embeddings: List of embedding vectors
            ttl_seconds: Optional TTL override
            
        Returns:
            Number of embeddings successfully cached
        """
        if not self.redis_client or len(texts) != len(embeddings):
            return 0

        try:
            ttl = ttl_seconds or self.ttl_seconds
            pipe = self.redis_client.pipeline()
            
            for text, embedding in zip(texts, embeddings):
                key = self._generate_key(text)
                data = {
                    "embedding": embedding,
                    "text_preview": text[:100],
                    "cached_at": datetime.utcnow().isoformat(),
                }
                pipe.setex(key, ttl, json.dumps(data))
            
            pipe.execute()
            self.stats["writes"] += len(texts)
            logger.info(f"Batch cached {len(texts)} embeddings")
            return len(texts)
            
        except Exception as e:
            logger.error(f"Batch cache write error: {str(e)}")
            self.stats["errors"] += 1
            return 0

    def delete(self, text: str) -> bool:
        """Delete embedding from cache."""
        if not self.redis_client:
            return False

        try:
            key = self._generate_key(text)
            self.redis_client.delete(key)
            logger.debug(f"Deleted cache for text: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Cache deletion error: {str(e)}")
            return False

    def delete_batch(self, texts: List[str]) -> int:
        """Delete multiple embeddings from cache."""
        if not self.redis_client:
            return 0

        try:
            keys = self._generate_keys(texts)
            deleted = self.redis_client.delete(*keys)
            logger.info(f"Deleted {deleted} embeddings from cache")
            return deleted
        except Exception as e:
            logger.error(f"Batch cache deletion error: {str(e)}")
            return 0

    def clear(self) -> bool:
        """Clear all embeddings from cache."""
        if not self.redis_client:
            return False

        try:
            pattern = f"{self.CACHE_PREFIX}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} embeddings from cache")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) 
            if total_requests > 0 else 0
        )
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "writes": self.stats["writes"],
            "errors": self.stats["errors"],
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_enabled": self.redis_client is not None,
        }

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {"hits": 0, "misses": 0, "writes": 0, "errors": 0}
        logger.info("Cache statistics reset")

    def is_available(self) -> bool:
        """Check if Redis cache is available."""
        return self.redis_client is not None


# Singleton instance
_embedding_cache = None


def get_embedding_cache() -> EmbeddingCache:
    """Get or create singleton embedding cache instance."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache
