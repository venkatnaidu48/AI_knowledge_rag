"""
Context Grounding - Generation Manager
Orchestrates end-to-end generation with provider management and fallback
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime

from src.generation.base import (
    LLMProvider,
    LLMProviderType,
    GenerationRequest,
    GenerationResponse,
)
from src.generation.providers import (
    MistralProvider,
    OpenAIProvider,
    HuggingFaceProvider,
    GroqProvider,
)
from src.generation.grounding import GroundingEngine, get_grounding_engine

logger = logging.getLogger(__name__)


class GenerationManager:
    """
    Manages LLM generation with multiple providers.
    Handles provider selection, fallback, and grounding validation.
    """
    
    def __init__(
        self,
        primary_provider: Optional[LLMProvider] = None,
        fallback_provider: Optional[LLMProvider] = None,
        grounding_engine: Optional[GroundingEngine] = None,
    ):
        """
        Initialize generation manager.
        
        Args:
            primary_provider: Primary LLM provider
            fallback_provider: Fallback provider if primary fails
            grounding_engine: Grounding validation engine
        """
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.grounding_engine = grounding_engine or get_grounding_engine()
        
        self.generation_count = 0
        self.successful_generations = 0
        self.failed_generations = 0
        self.fallback_used_count = 0
        self.grounded_responses = 0
        self.hallucination_count = 0
        
        self._log_provider_status()
    
    def _log_provider_status(self):
        """Log provider availability status."""
        logger.info("=" * 60)
        logger.info("LLM Provider Status")
        logger.info("=" * 60)
        
        if self.primary_provider:
            status = "✓ Available" if self.primary_provider.is_available() else "✗ Not configured"
            logger.info(f"Primary:  {self.primary_provider.get_provider_name()} ({status})")
        
        if self.fallback_provider:
            status = "✓ Available" if self.fallback_provider.is_available() else "✗ Not configured"
            logger.info(f"Fallback: {self.fallback_provider.get_provider_name()} ({status})")
        
        logger.info("=" * 60)
    
    async def generate(
        self,
        generation_request: GenerationRequest,
    ) -> GenerationResponse:
        """
        Generate response with provider selection and grounding.
        
        **Process:**
        1. Select primary or specified provider
        2. Generate response with retry/fallback
        3. Validate grounding if required
        4. Return complete response
        
        Args:
            generation_request: GenerationRequest with query, context, prompt
        
        Returns:
            GenerationResponse with generated text and metadata
        """
        self.generation_count += 1
        start_time = datetime.now()
        
        try:
            # Determine provider
            provider = self._select_provider(generation_request.provider)
            
            if not provider or not provider.is_available():
                return self._error_response(
                    "No available LLM provider",
                    generation_request,
                )
            
            logger.info(f"Using provider: {provider.get_provider_name()}")
            
            # Generate response
            try:
                response_text = await provider.generate(
                    prompt=generation_request.prompt,
                    temperature=generation_request.temperature,
                    max_tokens=generation_request.max_tokens,
                )
            except Exception as e:
                logger.warning(f"Primary provider failed: {str(e)}")
                
                # Try fallback
                if self.fallback_provider and self.fallback_provider.is_available():
                    logger.info("Attempting fallback provider")
                    self.fallback_used_count += 1
                    
                    response_text = await self.fallback_provider.generate(
                        prompt=generation_request.prompt,
                        temperature=generation_request.temperature,
                        max_tokens=generation_request.max_tokens,
                    )
                    provider = self.fallback_provider
                else:
                    raise
            
            # Check grounding if enabled
            grounding_result = None
            if generation_request.require_grounding:
                grounding_result = self.grounding_engine.check_grounding(
                    response_text=response_text,
                    context_chunks=generation_request.context_chunks,
                    query=generation_request.query,
                )
                
                if grounding_result.is_grounded:
                    self.grounded_responses += 1
                else:
                    self.hallucination_count += 1
                
                logger.info(
                    f"Grounding score: {grounding_result.grounding_score:.1%}"
                )
            
            # Calculate latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            self.successful_generations += 1
            
            logger.info(f"✓ Generation complete ({latency_ms:.1f}ms)")
            
            return GenerationResponse(
                response_text=response_text,
                provider_used=provider.get_provider_name(),
                model_used=provider.get_model_name(),
                grounding_result=grounding_result,
                latency_ms=latency_ms,
            )
        
        except Exception as e:
            self.failed_generations += 1
            logger.error(f"Generation failed: {str(e)}")
            return self._error_response(str(e), generation_request)
    
    def _select_provider(self, provider_type: Optional[str]) -> Optional[LLMProvider]:
        """
        Select LLM provider.
        
        Priority:
        1. Specified provider type
        2. Primary provider
        3. Fallback provider
        """
        # If specific provider requested, use it
        if provider_type:
            if provider_type.lower() == "openai":
                return OpenAIProvider() if OpenAIProvider().is_available() else None
            elif provider_type.lower() == "mistral":
                return MistralProvider() if MistralProvider().is_available() else None
            elif provider_type.lower() == "huggingface":
                return HuggingFaceProvider() if HuggingFaceProvider().is_available() else None
            elif provider_type.lower() == "groq":
                return GroqProvider() if GroqProvider().is_available() else None
        
        # Use primary if available
        if self.primary_provider and self.primary_provider.is_available():
            return self.primary_provider
        
        # Use fallback
        if self.fallback_provider and self.fallback_provider.is_available():
            return self.fallback_provider
        
        return None
    
    def _error_response(
        self,
        error_message: str,
        generation_request: GenerationRequest,
    ) -> GenerationResponse:
        """Build error response."""
        logger.error(f"Generation error: {error_message}")
        
        return GenerationResponse(
            response_text="",
            provider_used="error",
            model_used="",
            grounding_result=None,
            latency_ms=0.0,
        )
    
    def get_stats(self) -> Dict:
        """Get generation statistics."""
        success_rate = (
            self.successful_generations / self.generation_count * 100
            if self.generation_count > 0 else 0.0
        )
        
        grounding_rate = (
            self.grounded_responses / self.successful_generations * 100
            if self.successful_generations > 0 else 0.0
        )
        
        return {
            "total_generations": self.generation_count,
            "successful": self.successful_generations,
            "failed": self.failed_generations,
            "success_rate": success_rate,
            "fallback_used": self.fallback_used_count,
            "grounded_responses": self.grounded_responses,
            "hallucinations": self.hallucination_count,
            "grounding_rate": grounding_rate,
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.generation_count = 0
        self.successful_generations = 0
        self.failed_generations = 0
        self.fallback_used_count = 0
        self.grounded_responses = 0
        self.hallucination_count = 0
        self.grounding_engine.reset_stats()
    
    def set_primary_provider(self, provider: LLMProvider):
        """Change primary provider."""
        self.primary_provider = provider
        logger.info(f"Primary provider updated: {provider.get_provider_name()}")
    
    def set_fallback_provider(self, provider: LLMProvider):
        """Set fallback provider."""
        self.fallback_provider = provider
        logger.info(f"Fallback provider updated: {provider.get_provider_name()}")


# Singleton instance
_generation_manager: Optional[GenerationManager] = None


def get_generation_manager(
    primary_provider: Optional[LLMProvider] = None,
    fallback_provider: Optional[LLMProvider] = None,
) -> GenerationManager:
    """
    Get or create generation manager singleton.
    
    **Default setup:**
    - Primary: Mistral (free local)
    - Fallback: HuggingFace (free cloud)
    
    Args:
        primary_provider: Override primary provider
        fallback_provider: Override fallback provider
    
    Returns:
        Singleton GenerationManager instance
    """
    global _generation_manager
    
    if _generation_manager is None:
        if primary_provider is None:
            primary_provider = MistralProvider()
        
        if fallback_provider is None:
            fallback_provider = HuggingFaceProvider()
        
        _generation_manager = GenerationManager(
            primary_provider=primary_provider,
            fallback_provider=fallback_provider,
        )
        logger.info("✓ Generation manager initialized")
    
    return _generation_manager
