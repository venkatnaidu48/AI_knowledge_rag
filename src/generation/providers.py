"""
Context Grounding - LLM Provider Implementations
Supports multiple LLM providers: Mistral (free), OpenAI (paid), HuggingFace (free)
"""

import logging
import httpx
import os
from typing import Dict, Optional
from datetime import datetime

from src.generation.base import LLMProvider, LLMProviderType

logger = logging.getLogger(__name__)


class MistralProvider(LLMProvider):
    """
    Free Mistral LLM via Ollama (local).
    Completely free, runs on your machine, no API keys needed.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mistral",
    ):
        """
        Initialize Mistral provider.
        
        Args:
            base_url: Ollama server URL
            model: Model name (mistral, mistral:13b, etc.)
        """
        self.base_url = base_url
        self.model = model
        self.provider_type = LLMProviderType.MISTRAL
        self._available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama server is running."""
        try:
            # Try to connect to Ollama
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self._available = response.status_code == 200
            if self._available:
                logger.info(f"[OK] Mistral/Ollama available at {self.base_url}")
            else:
                logger.warning(f"Ollama not responding at {self.base_url}")
        except Exception as e:
            logger.warning(f"Ollama not available: {str(e)}")
            self._available = False
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using Mistral/Ollama (local, free).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum response length
        
        Returns:
            Generated text
        """
        if not self._available:
            raise RuntimeError(
                "Ollama server not available. "
                "Start Ollama with: ollama serve"
            )
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error: {response.text}")
            
            result = response.json()
            logger.info(f"[OK] Mistral generated {result.get('eval_count', 0)} tokens")
            return result.get("response", "")
        
        except Exception as e:
            logger.error(f"Mistral generation failed: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "Mistral (Ollama) - FREE LOCAL"
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available


class OpenAIProvider(LLMProvider):
    """
    Paid OpenAI GPT models via API.
    Requires API key and credits. Optional - only used when configured.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key (or use OPENAI_API_KEY env var)
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.provider_type = LLMProviderType.OPENAI
        self.base_url = "https://api.openai.com/v1"
        self._available = bool(self.api_key)
        
        if self._available:
            logger.info(f"[OK] OpenAI provider configured (model: {model})")
        else:
            logger.info("OpenAI not configured (API key missing)")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using OpenAI (paid cloud).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum response length
        
        Returns:
            Generated text
        """
        if not self._available:
            raise RuntimeError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
        
        try:
            import openai
            
            openai.api_key = self.api_key
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful business assistant answering questions based on provided context.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            text = response.choices[0].message.content
            logger.info(f"[OK] OpenAI generated response ({self.model})")
            return text
        
        except ImportError:
            raise RuntimeError("openai package not installed: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "OpenAI (Paid)"
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available


class HuggingFaceProvider(LLMProvider):
    """
    Free HuggingFace Inference API.
    Has free tier, cloud-hosted alternative to Ollama.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistralai/Mistral-7B-Instruct-v0.1",
    ):
        """
        Initialize HuggingFace provider.
        
        Args:
            api_key: HuggingFace API key (or use HF_API_KEY env var)
            model: Model ID from HuggingFace hub
        """
        self.api_key = api_key or os.getenv("HF_API_KEY")
        self.model = model
        self.provider_type = LLMProviderType.HUGGINGFACE
        self.base_url = "https://api-inference.huggingface.co/models"
        self._available = bool(self.api_key)
        
        if self._available:
            logger.info(f"[OK] HuggingFace provider configured (model: {model})")
        else:
            logger.info("HuggingFace not configured (API key missing)")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using HuggingFace (free tier available).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum response length
        
        Returns:
            Generated text
        """
        if not self._available:
            raise RuntimeError(
                "HuggingFace API key not configured. "
                "Set HF_API_KEY environment variable or pass api_key parameter."
            )
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                response = await client.post(
                    f"{self.base_url}/{self.model}",
                    headers=headers,
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "temperature": temperature,
                            "max_length": max_tokens,
                        },
                    },
                )
            
            if response.status_code != 200:
                raise RuntimeError(f"HuggingFace error: {response.text}")
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get("generated_text", "")
            else:
                text = result.get("generated_text", "")
            
            logger.info(f"[OK] HuggingFace generated response")
            return text
        
        except Exception as e:
            logger.error(f"HuggingFace generation failed: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "HuggingFace (Free Cloud)"
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available


class GroqProvider(LLMProvider):
    """
    Groq Cloud LLM API - Fast inference with free tier.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mixtral-8x7b-32768",
    ):
        """
        Initialize Groq provider.
        
        Args:
            api_key: Groq API key (or use GROQ_API_KEY env var)
            model: Model name (mixtral-8x7b-32768, etc.)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.provider_type = LLMProviderType.GROQ
        self._available = bool(self.api_key)
        
        if self._available:
            logger.info(f"[OK] Groq provider configured (model: {model})")
        else:
            logger.info("Groq not configured (API key missing)")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using Groq (fast, free tier available).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum response length
        
        Returns:
            Generated text
        """
        if not self._available:
            raise RuntimeError(
                "Groq API key not configured. "
                "Set GROQ_API_KEY environment variable."
            )
        
        try:
            from groq import Groq
            
            client = Groq(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful business assistant.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            text = response.choices[0].message.content
            logger.info(f"✓ Groq generated response ({self.model})")
            return text
        
        except ImportError:
            raise RuntimeError("groq package not installed: pip install groq")
        except Exception as e:
            logger.error(f"Groq generation failed: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "Groq (Fast, Free Tier)"
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available
