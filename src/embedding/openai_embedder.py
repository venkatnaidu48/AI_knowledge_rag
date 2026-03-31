"""
OpenAI Embeddings Module
Handles text embedding generation using OpenAI's API with rate limiting and error handling.
"""

import asyncio
import tiktoken
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
from openai import OpenAI, RateLimitError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """
    Generates embeddings using OpenAI's text-embedding-3-small model.
    Features:
    - Batch processing (max 32 embeddings per API call)
    - Automatic rate limit handling
    - Token limit enforcement (8191 tokens max)
    - Cost tracking
    - Comprehensive error handling
    """

    MODEL = "text-embedding-3-small"
    MAX_BATCH_SIZE = 32
    MAX_TOKENS = 8191
    EMBEDDING_DIMENSION = 1536  # Output dimension of text-embedding-3-small

    def __init__(self):
        """Initialize OpenAI client with API key from settings."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.encoding = tiktoken.encoding_for_model(self.MODEL)
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.api_calls_made = 0
        logger.info(f"✓ OpenAI embedder initialized with model: {self.MODEL}")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken encoder."""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token count failed, using fallback heuristic: {str(e)}")
            return len(text) // 4  # Rough estimate: 1 token ≈ 4 characters

    def _truncate_text(self, text: str, max_tokens: int = MAX_TOKENS) -> str:
        """Truncate text to fit within token limit."""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost in USD.
        text-embedding-3-small: $0.02 per 1M input tokens
        """
        cost_per_1m_tokens = 0.02
        cost = (input_tokens / 1_000_000) * cost_per_1m_tokens
        return cost

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _generate_batch(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        """
        Generate embeddings for a batch of texts with retry logic.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Tuple of (embeddings, total_tokens_used)
            
        Raises:
            RateLimitError: If API rate limit exceeded
            APIConnectionError: If API connection fails
        """
        if not texts:
            return [], 0

        # Validate and truncate texts
        validated_texts = []
        total_input_tokens = 0
        for text in texts:
            truncated = self._truncate_text(text)
            validated_texts.append(truncated)
            total_input_tokens += self._count_tokens(truncated)

        logger.debug(f"Generating {len(validated_texts)} embeddings, {total_input_tokens} tokens")

        try:
            response = self.client.embeddings.create(
                model=self.MODEL,
                input=validated_texts,
                dimensions=self.EMBEDDING_DIMENSION
            )

            embeddings = [item.embedding for item in response.data]
            output_tokens = len(validated_texts) * 64  # Rough estimate for output tokens

            # Track usage and cost
            self.api_calls_made += 1
            self.total_tokens_used += total_input_tokens
            cost = self._estimate_cost(total_input_tokens, output_tokens)
            self.total_cost += cost

            logger.info(
                f"✓ Batch embedding complete: {len(embeddings)} embeddings, "
                f"{total_input_tokens} tokens, cost: ${cost:.6f}"
            )

            return embeddings, total_input_tokens

        except RateLimitError as e:
            logger.warning(f"Rate limit hit, retrying: {str(e)}")
            raise
        except APIConnectionError as e:
            logger.error(f"API connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during embedding generation: {str(e)}")
            raise

    async def embed_batch_async(self, texts: List[str]) -> Dict:
        """
        Asynchronously generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Dict with embeddings, tokens_used, and cost
        """
        # Process in batches
        all_embeddings = []
        total_tokens = 0
        total_cost = 0.0

        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i : i + self.MAX_BATCH_SIZE]
            try:
                embeddings, tokens = self._generate_batch(batch)
                all_embeddings.extend(embeddings)
                total_tokens += tokens
                cost = self._estimate_cost(tokens, len(batch) * 64)
                total_cost += cost
                
                # Add delay between batches to avoid rate limiting
                if i + self.MAX_BATCH_SIZE < len(texts):
                    await asyncio.sleep(1)
                    
            except (RateLimitError, APIConnectionError) as e:
                logger.error(f"Batch {i // self.MAX_BATCH_SIZE} failed: {str(e)}")
                raise

        return {
            "success": True,
            "embeddings": all_embeddings,
            "tokens_used": total_tokens,
            "cost": total_cost,
            "count": len(all_embeddings),
            "timestamp": datetime.utcnow().isoformat(),
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
            truncated = self._truncate_text(text)
            tokens = self._count_tokens(truncated)
            embeddings, _ = self._generate_batch([truncated])
            
            return {
                "success": True,
                "embedding": embeddings[0],
                "tokens_used": tokens,
                "dimension": self.EMBEDDING_DIMENSION,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Single embedding failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_usage_stats(self) -> Dict:
        """Get embedding API usage statistics."""
        return {
            "api_calls": self.api_calls_made,
            "total_tokens": self.total_tokens_used,
            "total_cost_usd": self.total_cost,
            "avg_tokens_per_call": (
                self.total_tokens_used / self.api_calls_made 
                if self.api_calls_made > 0 else 0
            ),
            "avg_cost_per_call": (
                self.total_cost / self.api_calls_made 
                if self.api_calls_made > 0 else 0
            ),
        }

    def reset_stats(self):
        """Reset usage statistics."""
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.api_calls_made = 0
        logger.info("Usage statistics reset")


# Singleton instance
_openai_embedder = None


def get_openai_embedder() -> OpenAIEmbedder:
    """Get or create singleton OpenAI embedder instance."""
    global _openai_embedder
    if _openai_embedder is None:
        _openai_embedder = OpenAIEmbedder()
    return _openai_embedder
