"""
Embedding Generation Module

Components:
- OpenAI Embedder: text-embedding-3-small via OpenAI API
- Local Embedder: sentence-transformers (all-MiniLM-L6-v2) fallback
- Cache: Redis-based embedding caching (30-day TTL)
- Processor: Orchestration with intelligent fallback and batching
"""

from src.embedding.openai_embedder import OpenAIEmbedder, get_openai_embedder
from src.embedding.local_embedder import LocalEmbedder, get_local_embedder
from src.embedding.cache import EmbeddingCache, get_embedding_cache
from src.embedding.processor import EmbeddingProcessor, get_embedding_processor

__all__ = [
    "OpenAIEmbedder",
    "get_openai_embedder",
    "LocalEmbedder",
    "get_local_embedder",
    "EmbeddingCache",
    "get_embedding_cache",
    "EmbeddingProcessor",
    "get_embedding_processor",
]
