"""
Enterprise-Grade Text Chunker
Implements adaptive chunking with rich metadata extraction, batch processing,
and quality filtering for production-scale RAG systems.

Features:
- Dynamic chunking based on document type
- Rich metadata extraction (18+ fields)
- Quality filtering pipeline (multi-gate validation)
- Batch processing with parallel support
- Structured data handling (tables, lists, code)
- Chunk relationship tracking
"""

import logging
import re
import hashlib
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class DocumentType(Enum):
    """Types of documents"""
    GENERAL_TEXT = "general_text"
    PDF_TEXT = "pdf_text"
    PDF_SCANNED = "pdf_scanned"
    TABLE_RICH = "table_rich"
    CODE = "code"
    STRUCTURED_DATA = "structured_data"
    LEGAL_CONTRACT = "legal_contract"
    SCIENTIFIC_PAPER = "scientific_paper"
    EMAIL = "email"
    FORM = "form"


class ChunkType(Enum):
    """Types of chunks"""
    HEADER = "header"
    BODY = "body"
    TABLE = "table"
    LIST = "list"
    CODE = "code"
    FORMULA = "formula"
    IMAGE_CAPTION = "image_caption"
    FOOTER = "footer"
    UNKNOWN = "unknown"


class QualityGate(Enum):
    """Quality assessment gates"""
    PASSED = "passed"
    FAILED = "failed"
    FLAGGED = "flagged"


@dataclass
class ChunkMetadata:
    """Rich metadata for each chunk"""
    # Core identification
    chunk_id: str
    document_id: str
    chunk_number: int
    
    # Position & hierarchy
    page_number: Optional[int] = None
    position_in_document: int = 0  # Byte offset
    start_char: int = 0
    end_char: int = 0
    
    # Structural metadata
    section_id: Optional[str] = None
    section_title: str = ""
    section_path: str = ""  # e.g., "1.2.3.4"
    hierarchy_level: int = 0  # 0-5 levels
    nesting_level: int = 0
    
    # Content type
    chunk_type: ChunkType = ChunkType.UNKNOWN
    is_header: bool = False
    is_footer: bool = False
    
    # Quality scores
    quality_score: float = 0.5  # 0-1: Content quality
    completeness_score: float = 0.5  # 0-1: Information completeness
    coherence_score: float = 0.5  # 0-1: Text coherence
    readability_score: float = 50.0  # 0-100: Flesch-Kincaid
    language_confidence: float = 0.95  # 0-1: Language detection confidence
    technical_score: float = 0.0  # 0-1: Code/formula presence
    
    # Importance & relevance
    importance_score: float = 0.5  # 0-1: Domain importance
    entity_count: int = 0  # Named entities count
    keyword_density: float = 0.0  # 0-1: Keyword density
    
    # Content analysis
    token_count: int = 0
    character_count: int = 0
    sentence_count: int = 0
    average_sentence_length: float = 0.0
    contains_code: bool = False
    contains_numbers: bool = False
    contains_url: bool = False
    language: str = "en"
    
    # Relationships
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    related_chunk_ids: List[str] = field(default_factory=list)
    
    # Summary
    key_points: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)  # {"PERSON": [...], "ORG": [...]}
    summary: Optional[str] = None
    
    # Processing metadata
    extraction_method: str = "default"  # "text_extraction", "ocr", etc.
    confidence: float = 1.0  # Extraction confidence
    processed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Quality gate results
    quality_gate_result: QualityGate = QualityGate.PASSED
    quality_issues: List[str] = field(default_factory=list)


@dataclass
class ChunkBatch:
    """Batch of chunks for processing"""
    document_id: str
    document_type: DocumentType
    total_chunks: int
    chunks: List[Tuple[str, ChunkMetadata]] = field(default_factory=list)  # (text, metadata)
    processing_time: float = 0.0
    quality_filtered: int = 0


# ============================================================================
# ENTERPRISE CHUNKER
# ============================================================================

class EnterpriseTextChunker:
    """
    Advanced text chunker for enterprise RAG systems.
    
    Supports:
    - Multiple chunking strategies optimized for document type
    - Rich metadata extraction (18+ fields)
    - Quality filtering pipeline
    - Batch processing
    - Structured data handling
    """
    
    # Default configurations for different document types
    CONFIG = {
        DocumentType.GENERAL_TEXT: {
            "chunk_size": 512,
            "chunk_overlap": 100,
            "min_size": 100,
            "strategy": "semantic",
        },
        DocumentType.PDF_TEXT: {
            "chunk_size": 512,
            "chunk_overlap": 100,
            "min_size": 100,
            "strategy": "semantic",
        },
        DocumentType.TABLE_RICH: {
            "chunk_size": 256,
            "chunk_overlap": 50,
            "min_size": 50,
            "strategy": "table_aware",
        },
        DocumentType.CODE: {
            "chunk_size": 256,
            "chunk_overlap": 50,
            "min_size": 50,
            "strategy": "syntax_aware",
        },
        DocumentType.LEGAL_CONTRACT: {
            "chunk_size": 768,
            "chunk_overlap": 200,
            "min_size": 150,
            "strategy": "section_aware",
        },
        DocumentType.SCIENTIFIC_PAPER: {
            "chunk_size": 512,
            "chunk_overlap": 150,
            "min_size": 100,
            "strategy": "semantic",
        },
    }
    
    def __init__(self, default_type: DocumentType = DocumentType.GENERAL_TEXT):
        self.default_type = default_type
        self.chars_per_token = 4  # Rough approximation
        
    def chunk(
        self,
        text: str,
        document_id: str,
        document_type: Optional[DocumentType] = None,
        metadata_hints: Optional[Dict] = None,
    ) -> ChunkBatch:
        """
        Chunk document with type-specific strategy and rich metadata.
        
        Args:
            text: Document text to chunk
            document_id: ID of parent document
            document_type: Type of document (for strategy selection)
            metadata_hints: Additional metadata (page_number, section_title, etc.)
            
        Returns:
            ChunkBatch with chunks and metadata
        """
        doc_type = document_type or self.default_type
        config = self.CONFIG.get(doc_type, self.CONFIG[DocumentType.GENERAL_TEXT])
        
        # Get chunking strategy
        strategy = config.get("strategy", "semantic")
        
        if strategy == "table_aware":
            chunk_texts = self._chunk_table_aware(text, config)
        elif strategy == "syntax_aware":
            chunk_texts = self._chunk_syntax_aware(text, config)
        elif strategy == "section_aware":
            chunk_texts = self._chunk_section_aware(text, config)
        else:  # default: semantic
            chunk_texts = self._chunk_semantic(text, config)
        
        # Extract metadata for each chunk
        chunks = []
        for chunk_num, chunk_text in enumerate(chunk_texts, 1):
            metadata = self._extract_chunk_metadata(
                chunk_text=chunk_text,
                chunk_number=chunk_num,
                document_id=document_id,
                document_type=doc_type,
                metadata_hints=metadata_hints,
            )
            chunks.append((chunk_text, metadata))
        
        # Apply quality filtering
        filtered_chunks = self._apply_quality_gates(chunks)
        
        # Track relationships
        self._establish_chunk_relationships(filtered_chunks)
        
        # Create batch
        batch = ChunkBatch(
            document_id=document_id,
            document_type=doc_type,
            total_chunks=len(chunk_texts),
            chunks=filtered_chunks,
            quality_filtered=len(chunks) - len(filtered_chunks),
        )
        
        logger.info(
            f"Chunked {document_id}: {len(chunk_texts)} chunks created, "
            f"{len(filtered_chunks)} passed quality gates"
        )
        
        return batch
    
    # ========================================================================
    # CHUNKING STRATEGIES
    # ========================================================================
    
    def _chunk_semantic(self, text: str, config: Dict) -> List[str]:
        """Semantic chunking: splits at meaningful boundaries"""
        chunks = []
        chunk_size = config["chunk_size"] * self.chars_per_token
        min_size = config["min_size"]
        
        # Split by paragraphs
        paragraphs = re.split(r'\n\s*\n+', text)
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is too large, split by sentences
            if len(para) > chunk_size * 1.5:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split by sentence
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_chunk = ""
                
                for sentence in sentences:
                    if len(sub_chunk) + len(sentence) < chunk_size:
                        sub_chunk += sentence + " "
                    else:
                        if sub_chunk.strip():
                            chunks.append(sub_chunk.strip())
                        sub_chunk = sentence + " "
                
                if sub_chunk.strip():
                    chunks.append(sub_chunk.strip())
            else:
                # Add paragraph to current chunk
                if len(current_chunk) + len(para) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
                else:
                    current_chunk += para + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter by minimum size
        chunks = [c for c in chunks if len(c) >= min_size]
        
        logger.debug(f"Semantic chunking: {len(chunks)} chunks")
        return chunks
    
    def _chunk_table_aware(self, text: str, config: Dict) -> List[str]:
        """Table-aware chunking: handles rows and columns"""
        chunks = []
        
        # Detect tables (simple heuristic: lines with consistent delimiters)
        lines = text.split('\n')
        current_chunk = ""
        in_table = False
        
        for line in lines:
            # Table detection (lines with pipes or multiple spaces)
            is_table_line = '|' in line or (line.count('\t') >= 2)
            
            if is_table_line and not in_table:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = ""
                in_table = True
            elif not is_table_line and in_table:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = ""
                in_table = False
            
            current_chunk += line + "\n"
            
            # Size limit
            if len(current_chunk) > config["chunk_size"] * self.chars_per_token * 1.5:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter by minimum size
        min_size = config["min_size"]
        chunks = [c for c in chunks if len(c) >= min_size]
        
        logger.debug(f"Table-aware chunking: {len(chunks)} chunks")
        return chunks
    
    def _chunk_syntax_aware(self, text: str, config: Dict) -> List[str]:
        """Syntax-aware chunking: for code (function-level)"""
        chunks = []
        
        # Try to detect function/method boundaries
        # Look for patterns like: def func(), function func(), class ClassName
        func_pattern = r'^(def|class|function|async def)\s+\w+.*?:'
        
        current_chunk = ""
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            current_chunk += line + "\n"
            
            # Check if next line starts a new function/class
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if re.match(func_pattern, next_line) or re.match(func_pattern, line):
                    if current_chunk.strip() and len(current_chunk) > config["min_size"]:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
            
            # Size limit
            if len(current_chunk) > config["chunk_size"] * self.chars_per_token:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter by minimum size
        min_size = config["min_size"]
        chunks = [c for c in chunks if len(c) >= min_size]
        
        logger.debug(f"Syntax-aware chunking: {len(chunks)} chunks")
        return chunks
    
    def _chunk_section_aware(self, text: str, config: Dict) -> List[str]:
        """Section-aware chunking: for structured documents (contracts, papers)"""
        chunks = []
        
        # Match headers like "1. Section Title", "## Section", etc.
        section_pattern = r'^#{1,4}\s+|^\d+\.\s+|^[A-Z][A-Z\s]+:$'
        
        current_chunk = ""
        lines = text.split('\n')
        
        for line in lines:
            current_chunk += line + "\n"
            
            # If we found a new section and have content, save chunk
            if re.match(section_pattern, line) and len(current_chunk) > config["min_size"]:
                # Remove the section header from current chunk for next iteration
                chunks.append(current_chunk.strip())
                current_chunk = line + "\n"  # Keep header for next chunk
            
            # Size limit
            if len(current_chunk) > config["chunk_size"] * self.chars_per_token * 2:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter by minimum size
        min_size = config["min_size"]
        chunks = [c for c in chunks if len(c) >= min_size]
        
        logger.debug(f"Section-aware chunking: {len(chunks)} chunks")
        return chunks
    
    # ========================================================================
    # METADATA EXTRACTION
    # ========================================================================
    
    def _extract_chunk_metadata(
        self,
        chunk_text: str,
        chunk_number: int,
        document_id: str,
        document_type: DocumentType,
        metadata_hints: Optional[Dict] = None,
    ) -> ChunkMetadata:
        """Extract comprehensive metadata for a chunk"""
        
        metadata_hints = metadata_hints or {}
        
        # Generate chunk ID
        chunk_id = self._generate_chunk_id(document_id, chunk_number, chunk_text)
        
        # Basic statistics
        token_count = self._count_tokens_approx(chunk_text)
        char_count = len(chunk_text)
        sentence_count = len(re.split(r'[.!?]+', chunk_text))
        avg_sentence_length = token_count / max(sentence_count, 1)
        
        # Detect chunk type
        chunk_type = self._detect_chunk_type(chunk_text)
        
        # Quality scores
        quality_score = self._calculate_quality_score(chunk_text)
        readability_score = self._calculate_readability_score(chunk_text)
        coherence_score = self._calculate_coherence_score(chunk_text)
        completeness_score = self._calculate_completeness_score(chunk_text)
        
        # Content analysis
        contains_code = self._detect_code(chunk_text)
        contains_numbers = bool(re.search(r'\d+', chunk_text))
        contains_url = bool(re.search(r'https?://', chunk_text))
        technical_score = 0.8 if contains_code else 0.2
        
        # Language confidence
        language_confidence = self._estimate_language_confidence(chunk_text)
        
        # Entity counting (simplified)
        entity_count = self._count_entities(chunk_text)
        keyword_density = self._calculate_keyword_density(chunk_text)
        
        # Hierarchy detection
        hierarchy_level = self._detect_hierarchy_level(chunk_text)
        
        # Section detection
        section_title = metadata_hints.get("section_title", self._extract_section_title(chunk_text))
        section_path = metadata_hints.get("section_path", f"{hierarchy_level}")
        
        # Importance scoring
        importance_score = self._calculate_importance_score(chunk_text, chunk_number, document_type)
        
        # Key points extraction (simplified)
        key_points = self._extract_key_points(chunk_text)
        
        # Confidence based on extraction method
        extraction_method = metadata_hints.get("extraction_method", "text_extraction")
        confidence = 1.0 if extraction_method == "text_extraction" else 0.8
        
        return ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_number=chunk_number,
            page_number=metadata_hints.get("page_number"),
            position_in_document=(chunk_number - 1) * char_count,
            start_char=0,
            end_char=char_count,
            section_id=metadata_hints.get("section_id"),
            section_title=section_title,
            section_path=section_path,
            hierarchy_level=hierarchy_level,
            chunk_type=chunk_type,
            is_header=chunk_type in [ChunkType.HEADER, ChunkType.FOOTER],
            is_footer=chunk_type == ChunkType.FOOTER,
            quality_score=quality_score,
            completeness_score=completeness_score,
            coherence_score=coherence_score,
            readability_score=readability_score,
            language_confidence=language_confidence,
            technical_score=technical_score,
            importance_score=importance_score,
            entity_count=entity_count,
            keyword_density=keyword_density,
            token_count=token_count,
            character_count=char_count,
            sentence_count=sentence_count,
            average_sentence_length=avg_sentence_length,
            contains_code=contains_code,
            contains_numbers=contains_numbers,
            contains_url=contains_url,
            key_points=key_points,
            extraction_method=extraction_method,
            confidence=confidence,
        )
    
    def _detect_chunk_type(self, text: str) -> ChunkType:
        """Detect the type of chunk"""
        if re.match(r'^#{1,6}\s+', text):
            return ChunkType.HEADER
        elif re.search(r'^\|.*\|', text, re.MULTILINE):
            return ChunkType.TABLE
        elif re.search(r'^\s*[-*]\s+', text, re.MULTILINE):
            return ChunkType.LIST
        elif re.search(r'^(def|class|function|async)\s+', text):
            return ChunkType.CODE
        elif re.search(r'^\$\$.*\$\$$', text, re.MULTILINE):
            return ChunkType.FORMULA
        else:
            return ChunkType.BODY
    
    def _calculate_quality_score(self, text: str) -> float:
        """Calculate overall quality score (0-1)"""
        score = 0.5
        
        # Length check
        if 100 < len(text) < 5000:
            score += 0.2
        
        # Character diversity check
        unique_chars = len(set(text))
        if unique_chars > 20:
            score += 0.15
        
        # No excessive special characters
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s.!?,\-]', text)) / max(len(text), 1)
        if special_char_ratio < 0.1:
            score += 0.15
        
        # Minimum alphanumeric content
        alphanumeric_ratio = len(re.findall(r'[a-zA-Z0-9]', text)) / max(len(text), 1)
        if alphanumeric_ratio > 0.5:
            score += 0.15
        
        return min(1.0, score)
    
    def _calculate_readability_score(self, text: str) -> float:
        """Calculate Flesch-Kincaid readability (0-100)"""
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        syllables = self._count_syllables(text)
        
        if sentences == 0 or words == 0:
            return 50.0
        
        # Flesch-Kincaid Grade Level
        fk_grade = (0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59)
        
        # Convert to 0-100 scale
        readability = max(0, min(100, (100 - fk_grade * 5)))
        
        return readability
    
    def _count_syllables(self, text: str) -> int:
        """Estimate syllable count (simplified)"""
        vowels = "aeiouy"
        syllable_count = 0
        previous_was_vowel = False
        
        for char in text.lower():
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        return max(1, syllable_count)
    
    def _calculate_coherence_score(self, text: str) -> float:
        """Calculate text coherence (0-1)"""
        # Check for pronouns (indicator of coherence)
        pronouns = ['he', 'she', 'it', 'they', 'this', 'that', 'these', 'those']
        pronoun_count = sum(1 for p in pronouns if f' {p} ' in f' {text.lower()} ')
        
        # Check for connectors
        connectors = ['therefore', 'however', 'moreover', 'thus', 'consequently']
        connector_count = sum(1 for c in connectors if c in text.lower())
        
        # Check for repeated key terms (coherence indicator)
        words = text.split()
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only consider significant words
                word_freq[word.lower()] = word_freq.get(word.lower(), 0) + 1
        
        repeated_words = sum(1 for freq in word_freq.values() if freq > 2)
        
        score = min(1.0, (pronoun_count + connector_count + repeated_words) / 10)
        
        return max(0.3, score)  # Minimum 0.3
    
    def _calculate_completeness_score(self, text: str) -> float:
        """Calculate information completeness (0-1)"""
        # Check if chunk has introduction and content
        has_intro = len(text) > 20
        has_details = len(text.split()) > 10
        
        # Check for entities and numbers
        has_entities = len(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)) > 0
        has_numbers = bool(re.search(r'\d+', text))
        
        completeness = sum([has_intro, has_details, has_entities, has_numbers]) / 4
        
        return completeness
    
    def _detect_code(self, text: str) -> bool:
        """Detect if chunk contains code"""
        code_patterns = [
            r'\bdef\s+\w+',
            r'\bclass\s+\w+',
            r'function\s+\w+',
            r'\breturn\s+',
            r'=>',
            r'\{\s*\}',
            r'\[\s*\]',
        ]
        return any(re.search(pattern, text) for pattern in code_patterns)
    
    def _estimate_language_confidence(self, text: str) -> float:
        """Estimate confidence in language detection"""
        # High confidence if mostly ASCII and common words
        ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
        
        # Check for English stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'is', 'are'}
        words_lower = set(word.lower() for word in text.split())
        stop_word_match = len(words_lower & stop_words) / max(len(words_lower), 1)
        
        confidence = (ascii_ratio * 0.6 + stop_word_match * 0.4)
        
        return min(1.0, max(0.5, confidence))
    
    def _count_entities(self, text: str) -> int:
        """Count named entities (simplified - using capitalization)"""
        # Find capitalized words that look like entities
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        return len(set(entities))  # Unique entities
    
    def _calculate_keyword_density(self, text: str) -> float:
        """Calculate keyword density"""
        words = text.lower().split()
        if not words:
            return 0.0
        
        # Find words that appear multiple times
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only significant words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        keywords = [w for w, f in word_freq.items() if f > 2]
        
        if not keywords:
            return 0.0
        
        keyword_occurrences = sum(word_freq[kw] for kw in keywords)
        density = keyword_occurrences / len(words)
        
        return min(1.0, density)
    
    def _detect_hierarchy_level(self, text: str) -> int:
        """Detect hierarchy level from markdown headers or numbering"""
        if text.startswith('# '):
            return 1
        elif text.startswith('## '):
            return 2
        elif text.startswith('### '):
            return 3
        elif text.startswith('#### '):
            return 4
        elif re.match(r'^1\.', text):
            return 1
        elif re.match(r'^1\.1', text):
            return 2
        elif re.match(r'^1\.1\.1', text):
            return 3
        else:
            return 0
    
    def _extract_section_title(self, text: str) -> str:
        """Extract section title from chunk"""
        # Get first line if it looks like a title
        first_line = text.split('\n')[0].strip()
        
        if len(first_line) < 100 and first_line and first_line[-1] not in '.,;:':
            return first_line[:50]  # Max 50 chars
        
        # Otherwise, get first few words
        words = text.split()[:5]
        return " ".join(words)
    
    def _calculate_importance_score(
        self,
        text: str,
        chunk_number: int,
        document_type: DocumentType,
    ) -> float:
        """Calculate importance score based on position and content"""
        score = 0.5
        
        # Early chunks are more important (likely overview)
        if chunk_number < 5:
            score += 0.2
        
        # Headers are important
        if text.startswith('#'):
            score += 0.15
        
        # Check for important keywords
        important_keywords = [
            'important', 'critical', 'required', 'must', 'essential',
            'policy', 'procedure', 'summary', 'conclusion', 'recommendation'
        ]
        keyword_count = sum(1 for kw in important_keywords if kw in text.lower())
        score += min(0.2, keyword_count * 0.05)
        
        # Document type specific importance
        if document_type in [DocumentType.LEGAL_CONTRACT, DocumentType.SCIENTIFIC_PAPER]:
            if chunk_number < 10:  # Abstract/intro more important
                score += 0.1
        
        return min(1.0, score)
    
    def _extract_key_points(self, text: str, max_points: int = 3) -> List[str]:
        """Extract key points from chunk"""
        # Simple heuristic: sentences with important words
        sentences = re.split(r'[.!?]+', text)
        
        scored_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent.split()) < 5:  # Skip very short sentences
                continue
            
            score = 0
            if any(kw in sent.lower() for kw in ['important', 'critical', 'must', 'required']):
                score += 2
            if len(sent.split()) > 10:
                score += 1
            
            scored_sentences.append((score, sent))
        
        # Get top points
        scored_sentences.sort(reverse=True)
        key_points = [sent for _, sent in scored_sentences[:max_points]]
        
        return key_points
    
    def _count_tokens_approx(self, text: str) -> int:
        """Approximate token count"""
        return max(1, len(text) // self.chars_per_token)
    
    def _generate_chunk_id(self, document_id: str, chunk_number: int, text: str) -> str:
        """Generate unique chunk ID"""
        content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{document_id}-chunk-{chunk_number}-{content_hash}"
    
    # ========================================================================
    # QUALITY FILTERING GATES
    # ========================================================================
    
    def _apply_quality_gates(self, chunks: List[Tuple[str, ChunkMetadata]]) -> List[Tuple[str, ChunkMetadata]]:
        """Apply multi-gate quality filtering"""
        filtered_chunks = []
        
        for chunk_text, metadata in chunks:
            # Gate 1: Content validation
            if not self._gate1_content_validation(chunk_text, metadata):
                metadata.quality_gate_result = QualityGate.FAILED
                metadata.quality_issues.append("Failed content validation")
                continue
            
            # Gate 2: Semantic check
            if not self._gate2_semantic_check(chunk_text, metadata):
                metadata.quality_gate_result = QualityGate.FLAGGED
                metadata.quality_issues.append("Failed semantic check")
                # Still keep it, but flagged
            
            # Gate 3: Quality ranking
            self._gate3_quality_ranking(metadata)
            
            filtered_chunks.append((chunk_text, metadata))
        
        logger.info(f"Quality gates: {len(chunks)} chunks → {len(filtered_chunks)} passed")
        
        return filtered_chunks
    
    def _gate1_content_validation(self, chunk_text: str, metadata: ChunkMetadata) -> bool:
        """Gate 1: Basic content validation"""
        issues = []
        
        # Length check
        if len(chunk_text) < 50:
            issues.append("Too short")
        if len(chunk_text) > 10000:
            issues.append("Too long")
        
        # Encoding check
        try:
            chunk_text.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError:
            issues.append("Invalid encoding")
        
        # Language confidence check
        if metadata.language_confidence < 0.5:
            issues.append("Low language confidence")
        
        # Minimum information content
        if metadata.entity_count == 0 and not metadata.contains_numbers:
            issues.append("No meaningful content")
        
        metadata.quality_issues.extend(issues)
        return len(issues) == 0
    
    def _gate2_semantic_check(self, chunk_text: str, metadata: ChunkMetadata) -> bool:
        """Gate 2: Semantic quality check"""
        issues = []
        
        # Check for gibberish (too many repeated characters)
        if re.search(r'(.)\1{10,}', chunk_text):
            issues.append("Excessive character repetition")
        
        # Check for noise (special characters)
        special_ratio = len(re.findall(r'[^a-zA-Z0-9\s.!?,\-]', chunk_text)) / max(len(chunk_text), 1)
        if special_ratio > 0.3:
            issues.append("High special character ratio")
        
        # Minimum unique words
        unique_words = len(set(chunk_text.lower().split()))
        if unique_words < 5:
            issues.append("Too few unique words")
        
        # Quality and coherence thresholds
        if metadata.quality_score < 0.4:
            issues.append("Low quality score")
        if metadata.coherence_score < 0.3:
            issues.append("Low coherence score")
        
        metadata.quality_issues.extend(issues)
        return len(issues) == 0
    
    def _gate3_quality_ranking(self, metadata: ChunkMetadata) -> None:
        """Gate 3: Rank by quality"""
        # Composite quality score
        quality_composite = (
            metadata.quality_score * 0.40 +
            metadata.coherence_score * 0.30 +
            metadata.completeness_score * 0.20 +
            (metadata.importance_score * 0.10)
        )
        
        # Store composite score in quality_score
        metadata.quality_score = quality_composite
    
    # ========================================================================
    # CHUNK RELATIONSHIPS
    # ========================================================================
    
    def _establish_chunk_relationships(self, chunks: List[Tuple[str, ChunkMetadata]]) -> None:
        """Establish relationships between chunks"""
        for i, (_, metadata) in enumerate(chunks):
            if i > 0:
                metadata.previous_chunk_id = chunks[i-1][1].chunk_id
            if i < len(chunks) - 1:
                metadata.next_chunk_id = chunks[i+1][1].chunk_id


# ============================================================================
# BATCH PROCESSOR
# ============================================================================

class BatchChunkProcessor:
    """Process multiple chunks in batch for efficiency"""
    
    def __init__(self, chunker: EnterpriseTextChunker, batch_size: int = 100):
        self.chunker = chunker
        self.batch_size = batch_size
    
    def process_batch(
        self,
        documents: List[Tuple[str, str, DocumentType, Optional[Dict]]],
        parallel: bool = False,
    ) -> List[ChunkBatch]:
        """
        Process multiple documents.
        
        Args:
            documents: List of (text, document_id, doc_type, metadata_hints)
            parallel: Use parallel processing if True
            
        Returns:
            List of ChunkBatch results
        """
        results = []
        
        if parallel and len(documents) > 1:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(
                        self.chunker.chunk,
                        text, doc_id, doc_type, hints
                    )
                    for text, doc_id, doc_type, hints in documents
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
        else:
            results = [
                self.chunker.chunk(text, doc_id, doc_type, hints)
                for text, doc_id, doc_type, hints in documents
            ]
        
        return results
    
    def to_database_format(self, batch: ChunkBatch) -> List[Dict]:
        """Convert ChunkBatch to database insert format"""
        records = []
        
        for chunk_text, metadata in batch.chunks:
            record = {
                "chunk_id": metadata.chunk_id,
                "document_id": metadata.document_id,
                "chunk_text": chunk_text,
                "chunk_number": metadata.chunk_number,
                **asdict(metadata)
            }
            record.pop("chunk_id")  # ID already in dict
            records.append(record)
        
        return records
