"""
Context Grounding - LLM Provider Base Classes
Abstract interfaces for multiple LLM providers (paid & free)
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"  # Paid
    MISTRAL = "mistral"  # Free (local)
    HUGGINGFACE = "huggingface"  # Free (cloud)
    GROQ = "groq"  # Free tier available


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text response from prompt.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
            **kwargs: Provider-specific parameters
        
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available/configured."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get current model name."""
        pass
    
    async def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate provider configuration.
        
        Returns:
            {
                "available": bool,
                "authenticated": bool,
                "model_accessible": bool,
                "message": str
            }
        """
        return {
            "available": self.is_available(),
            "message": f"Provider {self.get_provider_name()} available",
        }


class GroundingResult:
    """Result from grounding check."""
    
    def __init__(
        self,
        is_grounded: bool,
        grounding_score: float,
        source_references: List[str],
        issues: List[str] = None,
        explanation: str = "",
    ):
        """
        Initialize grounding result.
        
        Args:
            is_grounded: Whether response is grounded in sources
            grounding_score: Score 0.0-1.0 (1.0 = fully grounded)
            source_references: List of source chunk IDs referenced
            issues: List of grounding issues found
            explanation: Explanation of grounding analysis
        """
        self.is_grounded = is_grounded
        self.grounding_score = grounding_score
        self.source_references = source_references
        self.issues = issues or []
        self.explanation = explanation
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "is_grounded": self.is_grounded,
            "grounding_score": self.grounding_score,
            "source_references": self.source_references,
            "issues": self.issues,
            "explanation": self.explanation,
        }


class GenerationRequest:
    """Validated request for text generation."""
    
    def __init__(
        self,
        query: str,
        context_chunks: List[Dict],
        prompt: str,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        require_grounding: bool = True,
    ):
        """
        Initialize generation request.
        
        Args:
            query: Original user query
            context_chunks: Retrieved context chunks
            prompt: Formatted prompt for LLM
            provider: LLM provider to use (or None for default)
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            require_grounding: Whether to enforce grounding
        """
        self.query = query
        self.context_chunks = context_chunks
        self.prompt = prompt
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.require_grounding = require_grounding
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "context_chunks": len(self.context_chunks),
            "provider": self.provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "require_grounding": self.require_grounding,
        }


class GenerationResponse:
    """Response from LLM generation."""
    
    def __init__(
        self,
        response_text: str,
        provider_used: str,
        model_used: str,
        grounding_result: Optional[GroundingResult] = None,
        tokens_used: Optional[Dict] = None,
        latency_ms: float = 0.0,
    ):
        """
        Initialize generation response.
        
        Args:
            response_text: Generated response
            provider_used: Provider that generated response
            model_used: Model name used
            grounding_result: Grounding analysis result
            tokens_used: {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
            latency_ms: Generation latency in milliseconds
        """
        self.response_text = response_text
        self.provider_used = provider_used
        self.model_used = model_used
        self.grounding_result = grounding_result
        self.tokens_used = tokens_used or {}
        self.latency_ms = latency_ms
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "response": self.response_text,
            "provider": self.provider_used,
            "model": self.model_used,
            "grounding": self.grounding_result.to_dict() if self.grounding_result else None,
            "tokens": self.tokens_used,
            "latency_ms": self.latency_ms,
        }
