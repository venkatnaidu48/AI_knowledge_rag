"""
Text chunking module
Implements semantic, sentence-aware, and fixed-size chunking strategies
"""

import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)


class TextChunker:
    """Break text into chunks for embedding"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 100, min_size: int = 100):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target tokens per chunk (~4 chars per token approx)
            chunk_overlap: Overlap between chunks for context preservation
            min_size: Minimum chunk size in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_size = min_size
        
        # Estimate chars per token (rough: 1 token ≈ 4 chars)
        self.chars_per_token = 4
        self.target_chars = chunk_size * self.chars_per_token
        self.overlap_chars = chunk_overlap * self.chars_per_token
    
    def chunk_semantic(self, text: str) -> List[str]:
        """
        Semantic chunking - splits at meaningful boundaries (headers, paragraphs)
        Best quality but requires structured text
        """
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n+', text)
        
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            
            if not para:
                continue
            
            # If paragraph alone is larger than target, split it further
            if len(para) > self.target_chars * 1.5:
                # Add current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split large paragraph into sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_chunk = ""
                
                for sentence in sentences:
                    if len(sub_chunk) + len(sentence) < self.target_chars:
                        sub_chunk += sentence + " "
                    else:
                        if sub_chunk.strip():
                            chunks.append(sub_chunk.strip())
                        sub_chunk = sentence + " "
                
                if sub_chunk.strip():
                    chunks.append(sub_chunk.strip())
            
            else:
                # If adding this paragraph would exceed limit, save current chunk
                if len(current_chunk) + len(para) > self.target_chars:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
                else:
                    current_chunk += para + "\n\n"
        
        # Don't forget last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter by minimum size and clean
        chunks = [c.strip() for c in chunks if len(c.strip()) >= self.min_size]
        
        logger.info(f"Semantic chunking created {len(chunks)} chunks")
        return chunks
    
    def chunk_sentence_aware(self, text: str) -> List[str]:
        """
        Sentence-aware chunking - groups sentences together
        Good balance of quality and robustness
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Check if adding this sentence exceeds limit
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) > self.target_chars and current_chunk:
                # Save current chunk and start new one
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Add to current chunk
                current_chunk = potential_chunk if not current_chunk else current_chunk + " " + sentence
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter by minimum size
        chunks = [c for c in chunks if len(c) >= self.min_size]
        
        logger.info(f"Sentence-aware chunking created {len(chunks)} chunks")
        return chunks
    
    def chunk_fixed_size(self, text: str) -> List[str]:
        """
        Fixed-size chunking with overlap
        Simplest but least intelligent
        """
        chunks = []
        overlap_chars = self.overlap_chars
        target_chars = self.target_chars
        
        for i in range(0, len(text), target_chars - overlap_chars):
            chunk = text[i : i + target_chars]
            
            if len(chunk.strip()) >= self.min_size:
                chunks.append(chunk.strip())
        
        logger.info(f"Fixed-size chunking created {len(chunks)} chunks")
        return chunks
    
    def chunk(self, text: str, strategy: str = "semantic") -> List[str]:
        """
        Chunk text using specified strategy
        
        Args:
            text: Text to chunk
            strategy: "semantic", "sentence_aware", or "fixed"
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        if strategy == "semantic":
            chunks = self.chunk_semantic(text)
        elif strategy == "sentence_aware":
            chunks = self.chunk_sentence_aware(text)
        elif strategy == "fixed":
            chunks = self.chunk_fixed_size(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        
        return chunks


def count_tokens_approx(text: str) -> int:
    """
    Approximate token count (using simple heuristic)
    1 token ≈ 4 characters (rough estimate)
    More accurate with tiktoken but slower
    """
    return max(1, len(text) // 4)


def calculate_chunk_metadata(chunk_text: str, chunk_number: int, section_title: str = "") -> Dict:
    """Calculate metadata for a chunk"""
    
    # Estimate tokens
    tokens = count_tokens_approx(chunk_text)
    
    # Get first few words for section detection
    words = chunk_text.split()[:3]
    section = section_title or " ".join(words)
    
    # Hierarchy level (try to detect from markdown headers)
    hierarchy_level = 0
    if chunk_text.startswith("# "):
        hierarchy_level = 1
    elif chunk_text.startswith("## "):
        hierarchy_level = 2
    elif chunk_text.startswith("### "):
        hierarchy_level = 3
    
    # Importance scoring (rough)
    importance_score = 0.5
    
    # Higher importance if chunk contains certain keywords
    important_keywords = ["important", "critical", "required", "must", "essential", "policy", "procedure"]
    text_lower = chunk_text.lower()
    keyword_count = sum(1 for kw in important_keywords if kw in text_lower)
    importance_score += min(0.4, keyword_count * 0.1)  # Max 0.9
    
    # Higher importance for early chunks (more likely to be overview)
    if chunk_number < 3:
        importance_score += 0.1
    
    return {
        "chunk_number": chunk_number,
        "tokens_count": tokens,
        "section_title": section,
        "hierarchy_level": hierarchy_level,
        "importance_score": min(1.0, importance_score),
        "language": "en",  # Default to English
    }
