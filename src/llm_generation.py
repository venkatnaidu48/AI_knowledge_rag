"""
STEP 6: Multi-Provider LLM Generation
Generates answers from context using multiple LLM providers with automatic fallback
"""

import os
import requests
import json
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import time

# Suppress logs
logging.getLogger("urllib3").setLevel(logging.WARNING)


class LLMProvider(Enum):
    """Available LLM providers"""
    LOCAL_MISTRAL = "mistral_local"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    GROQ = "groq"


@dataclass
class GeneratedAnswer:
    """Output from LLM generation"""
    answer: str
    provider_used: str
    generation_time_ms: float
    model_name: str
    grounding_score: float = 0.0  # Will be set by validators


class LLMGenerator:
    """
    Generates answers using multiple LLM providers with fallback strategy
    
    Priority order:
    1. OpenAI (best quality, paid)
    2. LOCAL Mistral (free, local - no data sent)
    3. Groq (fast, free tier)
    4. HuggingFace (free, rate limited)
    """
    
    def __init__(self, verbose: bool = False):
        """Initialize LLM generator"""
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        
        # Provider configs
        self.providers_config = {
            LLMProvider.LOCAL_MISTRAL: {
                "name": "Mistral Local (Ollama)",
                "endpoint": "http://localhost:11434/api/generate",
                "model": "mistral:7b",
                "local": True,
                "enabled": self._check_local_llm()
            },
            LLMProvider.OPENAI: {
                "name": "OpenAI GPT-4",
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "enabled": bool(os.getenv("OPENAI_API_KEY")),
            },
            LLMProvider.GROQ: {
                "name": "Groq (Fast Inference)",
                "endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "model": "mixtral-8x7b-32768",
                "api_key": os.getenv("GROQ_API_KEY"),
                "enabled": bool(os.getenv("GROQ_API_KEY")),
            },
            LLMProvider.HUGGINGFACE: {
                "name": "HuggingFace Inference",
                "endpoint_template": "https://api-inference.huggingface.co/models/{}",
                "model": "meta-llama/Llama-2-7b-chat-hf",
                "api_key": os.getenv("HUGGINGFACE_API_KEY"),
                "enabled": bool(os.getenv("HUGGINGFACE_API_KEY")),
            },
        }
        
        # Provider priority order
        self.provider_priority = [
            LLMProvider.OPENAI,           # Best quality
            LLMProvider.LOCAL_MISTRAL,    # Local, no data sent
            LLMProvider.GROQ,             # Fast
            LLMProvider.HUGGINGFACE,      # Free/backup
        ]
        
        if self.verbose:
            self._print_provider_status()
    
    def _check_local_llm(self) -> bool:
        """Check if local Mistral (Ollama) is available"""
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False
    
    def _print_provider_status(self):
        """Print which providers are available"""
        print("\n" + "="*70)
        print("LLM PROVIDER STATUS")
        print("="*70)
        for provider, config in self.providers_config.items():
            status = "✅ AVAILABLE" if config["enabled"] else "❌ NOT AVAILABLE"
            print(f"{config['name']:<40} {status}")
        print("="*70 + "\n")
    
    # ==================== LOCAL MISTRAL (OLLAMA) ====================
    def _generate_with_mistral(
        self,
        context: str,
        question: str,
        temperature: float = 0.1,
        max_tokens: int = 300
    ) -> Optional[Tuple[str, float]]:
        """
        Generate answer using local Mistral via Ollama
        
        Returns: (answer, generation_time_ms) or None if failed
        """
        try:
            prompt = f"""You are an expert assistant that answers ONLY from provided documents. 

CRITICAL RULES:
1. ONLY answer from the documents below - NO external knowledge
2. If information is NOT in the documents, say "I don't have this information"
3. NEVER make up, infer, assume, or hallucinate facts
4. If unsure, ask for clarification or say you need more information
5. Always cite the source for your answer

DOCUMENTS:
{context}

QUESTION: {question}

ANSWER (from documents only):"""
            
            start_time = time.time()
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral:7b",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "num_predict": max_tokens,
                },
                timeout=60
            )
            
            gen_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                answer = response.json().get("response", "").strip()
                if answer:
                    if self.verbose:
                        print(f"✅ Mistral generated answer in {gen_time:.0f}ms")
                    return answer, gen_time
        
        except requests.Timeout:
            if self.verbose:
                print("❌ Mistral timeout (not running)")
        except Exception as e:
            if self.verbose:
                print(f"❌ Mistral error: {str(e)[:50]}")
        
        return None
    
    # ==================== OPENAI ====================
    def _generate_with_openai(
        self,
        context: str,
        question: str,
        temperature: float = 0.1,
        max_tokens: int = 300
    ) -> Optional[Tuple[str, float]]:
        """Generate answer using OpenAI GPT-4"""
        try:
            import openai
            openai.api_key = self.providers_config[LLMProvider.OPENAI]["api_key"]
            
            system_prompt = (
                "You are an expert assistant that answers ONLY from provided documents.\n"
                "CRITICAL RULES:\n"
                "1. ONLY answer from the documents provided - NO external knowledge\n"
                "2. If information is NOT in documents, say 'I don't have this information in the provided documents'\n"
                "3. NEVER make up, infer, assume, or hallucinate facts\n"
                "4. If unsure, ask for clarification or say you need more information\n"
                "5. Always cite sources when possible\n"
                "6. Do NOT add your own interpretations or generalizations\n"
                "7. Stick strictly to what is written in the documents"
            )
            
            user_message = f"""Based STRICTLY on the following company documents, answer this question:

DOCUMENTS:
{context}

QUESTION: {question}

ANSWER (from documents only - no external knowledge):"""
            
            start_time = time.time()
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30
            )
            
            gen_time = (time.time() - start_time) * 1000
            answer = response.choices[0].message.content.strip()
            
            if answer:
                if self.verbose:
                    print(f"✅ OpenAI GPT-4 generated answer in {gen_time:.0f}ms")
                return answer, gen_time
        
        except Exception as e:
            if self.verbose:
                print(f"❌ OpenAI error: {str(e)[:50]}")
        
        return None
    
    # ==================== GROQ ====================
    def _generate_with_groq(
        self,
        context: str,
        question: str,
        temperature: float = 0.1,
        max_tokens: int = 300
    ) -> Optional[Tuple[str, float]]:
        """Generate answer using Groq (very fast inference)"""
        try:
            api_key = self.providers_config[LLMProvider.GROQ]["api_key"]
            
            system_prompt = (
                "You are an expert assistant that answers ONLY from provided documents.\n"
                "RULES:\n"
                "1. ONLY use the documents provided - NO external knowledge\n"
                "2. If information is NOT in documents, say 'I don't have this information'\n"
                "3. NEVER make up or hallucinate facts\n"
                "4. Stick strictly to what is written"
            )
            
            user_message = f"""Based STRICTLY on these company documents, answer this question:

DOCUMENTS:
{context}

QUESTION: {question}

ANSWER (from documents only):"""
            
            start_time = time.time()
            
            # Get model from config or use fallback
            model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=30
            )
            
            gen_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content'].strip()
                if answer:
                    if self.verbose:
                        print(f"✅ Groq generated answer in {gen_time:.0f}ms")
                    return answer, gen_time
        
        except Exception as e:
            if self.verbose:
                print(f"❌ Groq error: {str(e)[:50]}")
        
        return None
    
    # ==================== HUGGINGFACE ====================
    def _generate_with_huggingface(
        self,
        context: str,
        question: str,
        temperature: float = 0.1,
        max_tokens: int = 300
    ) -> Optional[Tuple[str, float]]:
        """Generate answer using HuggingFace Inference API"""
        try:
            api_key = self.providers_config[LLMProvider.HUGGINGFACE]["api_key"]
            model = "meta-llama/Llama-2-7b-chat-hf"
            
            prompt = f"""DOCUMENTS:
{context}

QUESTION: {question}

ANSWER:"""
            
            start_time = time.time()
            
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "inputs": prompt,
                    "parameters": {
                        "temperature": temperature,
                        "max_new_tokens": max_tokens,
                    }
                },
                timeout=30
            )
            
            gen_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    answer = result[0].get("generated_text", "").strip()
                    if answer:
                        if self.verbose:
                            print(f"✅ HuggingFace generated answer in {gen_time:.0f}ms")
                        return answer, gen_time
        
        except Exception as e:
            if self.verbose:
                print(f"❌ HuggingFace error: {str(e)[:50]}")
        
        return None
    
    # ==================== MAIN GENERATION METHOD ====================
    def generate_answer(
        self,
        context: str,
        question: str,
        temperature: float = 0.1,
        max_tokens: int = 300
    ) -> Optional[GeneratedAnswer]:
        """
        Generate answer with automatic fallback strategy
        
        Args:
            context: Retrieved document chunks
            question: User question
            temperature: 0.0 (deterministic) to 1.0 (creative)
            max_tokens: Maximum response length
        
        Returns:
            GeneratedAnswer with provider info, or None if all fail
        """
        if not context:
            return None
        
        if self.verbose:
            print(f"\n📝 Generating answer for: {question[:60]}...")
        
        # Try each provider in priority order
        for provider in self.provider_priority:
            if not self.providers_config[provider]["enabled"]:
                if self.verbose:
                    print(f"⏭️  {self.providers_config[provider]['name']} not available, skipping...")
                continue
            
            if self.verbose:
                print(f"\n🔄 Trying {self.providers_config[provider]['name']}...")
            
            result = None
            
            # Route to correct provider
            if provider == LLMProvider.LOCAL_MISTRAL:
                result = self._generate_with_mistral(context, question, temperature, max_tokens)
            elif provider == LLMProvider.OPENAI:
                result = self._generate_with_openai(context, question, temperature, max_tokens)
            elif provider == LLMProvider.GROQ:
                result = self._generate_with_groq(context, question, temperature, max_tokens)
            elif provider == LLMProvider.HUGGINGFACE:
                result = self._generate_with_huggingface(context, question, temperature, max_tokens)
            
            if result:
                answer, gen_time = result
                return GeneratedAnswer(
                    answer=answer,
                    provider_used=self.providers_config[provider]["name"],
                    generation_time_ms=gen_time,
                    model_name=self.providers_config[provider]["model"]
                )
        
        if self.verbose:
            print("❌ All LLM providers failed. Falling back to retrieval-only mode.")
        
        return None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        available = []
        for provider, config in self.providers_config.items():
            if config["enabled"]:
                available.append(config["name"])
        return available


# ==================== RETRIEVAL-ONLY MODE ====================
class RetrievalOnlyAnswerer:
    """
    Fallback: Return answer directly from retrieved chunks
    when LLM is not available
    """
    
    @staticmethod
    def format_answer(chunks: List[Dict], question: str) -> str:
        """Format chunks as direct answer"""
        if not chunks:
            return "Answer not found in knowledge base."
        
        # Take the best chunk
        best_chunk = chunks[0]
        
        # Truncate to reasonable length
        answer = best_chunk.get("text", "")[:500]
        
        return answer.strip()


# ==================== TESTING ====================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("LLM GENERATION SYSTEM TEST")
    print("="*70)
    
    # Initialize generator with verbose output
    generator = LLMGenerator(verbose=True)
    
    # Test inputs
    test_context = """
    Our company strategy focuses on three main pillars:
    1. Innovation: We invest heavily in R&D to develop cutting-edge solutions
    2. Customer Focus: We prioritize customer satisfaction and feedback
    3. Operational Excellence: We maintain high standards in all operations
    
    Founded in 2015, we have grown to serve thousands of customers worldwide.
    Our annual revenue is $50 million with 200+ employees.
    """
    
    test_question = "What is your company strategy?"
    
    # Try to generate answer
    print(f"\n📋 Question: {test_question}")
    print(f"\n📄 Context length: {len(test_context)} characters")
    
    answer = generator.generate_answer(test_context, test_question)
    
    if answer:
        print(f"\n✅ ANSWER GENERATED")
        print(f"Provider: {answer.provider_used}")
        print(f"Model: {answer.model_name}")
        print(f"Time: {answer.generation_time_ms:.0f}ms")
        print(f"\nAnswer:\n{answer.answer}")
    else:
        print("\n⚠️  No LLM available - using retrieval-only mode")
        fallback_answer = RetrievalOnlyAnswerer.format_answer(
            [{"text": test_context}], test_question
        )
        print(f"\nFallback Answer:\n{fallback_answer}")

