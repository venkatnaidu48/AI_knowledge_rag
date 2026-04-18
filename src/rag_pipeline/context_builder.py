"""
Context Builder Module

Builds context from ranked documents for LLM input.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BuiltContext:
    """Context prepared for LLM input"""
    context_text: str
    sources: List[str]
    num_documents: int
    total_length: int
    metadata: Dict


class ContextBuilder:
    """
    Builds context from ranked documents for LLM input.
    
    Features:
    - Formats documents into readable context
    - Includes source attribution
    - Manages context length
    - Maintains metadata
    """
    
    def __init__(
        self,
        max_context_length: int = 2000,
        context_format: str = "default",
        include_source: bool = True,
        num_separator: str = "\n---\n",
    ):
        """
        Initialize context builder.
        
        Args:
            max_context_length: Maximum context length in characters
            context_format: Format style (default, structured, minimal)
            include_source: Include source attribution
            num_separator: Separator between documents
        """
        self.max_context_length = max_context_length
        self.context_format = context_format
        self.include_source = include_source
        self.num_separator = num_separator
    
    def build(self, ranked_results: List) -> BuiltContext:
        """
        Build context from ranked results.
        
        Args:
            ranked_results: List of RankedResult
            
        Returns:
            BuiltContext with formatted text and metadata
        """
        context_parts = []
        sources = []
        current_length = 0
        
        for i, result in enumerate(ranked_results, 1):
            # Format document
            if self.context_format == "structured":
                doc_text = self._format_structured(result, i)
            elif self.context_format == "minimal":
                doc_text = self._format_minimal(result)
            else:  # default
                doc_text = self._format_default(result, i)
            
            # Check length
            new_length = current_length + len(doc_text) + len(self.num_separator)
            if new_length > self.max_context_length and context_parts:
                logger.warning(
                    f"Context length exceeded. "
                    f"Stopping at {len(context_parts)} documents."
                )
                break
            
            context_parts.append(doc_text)
            sources.append(result.source)
            current_length = new_length
        
        # Combine context
        context_text = self.num_separator.join(context_parts)
        
        logger.info(
            f"Built context from {len(context_parts)} documents "
            f"({current_length} characters)"
        )
        
        return BuiltContext(
            context_text=context_text,
            sources=sources,
            num_documents=len(context_parts),
            total_length=current_length,
            metadata={
                "format": self.context_format,
                "num_sources": len(set(sources)),
                "avg_doc_length": current_length // len(context_parts) if context_parts else 0,
            },
        )
    
    def _format_default(self, result, index: int) -> str:
        """Default format with document number and content."""
        text = f"[Document {index}]\n{result.text}"
        
        if self.include_source:
            text += f"\n(Source: {result.source})"
        
        return text
    
    def _format_structured(self, result, index: int) -> str:
        """Structured format with clear sections."""
        text = f"""
Document {index}:
- Content: {result.text}
- Relevance Score: {result.similarity_score:.2%}
- Rank Score: {result.rank_score:.2%}"""
        
        if self.include_source:
            text += f"\n- Source: {result.source}"
        
        return text
    
    def _format_minimal(self, result) -> str:
        """Minimal format with just content."""
        return result.text
    
    def merge_contexts(
        self,
        contexts: List[BuiltContext],
        separator: str = "\n\n---\n\n",
    ) -> BuiltContext:
        """
        Merge multiple contexts into one.
        
        Args:
            contexts: List of BuiltContext
            separator: Separator between contexts
            
        Returns:
            Merged BuiltContext
        """
        merged_text = separator.join([c.context_text for c in contexts])
        all_sources = []
        total_length = 0
        total_docs = 0
        
        for c in contexts:
            all_sources.extend(c.sources)
            total_length += c.total_length
            total_docs += c.num_documents
        
        return BuiltContext(
            context_text=merged_text,
            sources=all_sources,
            num_documents=total_docs,
            total_length=total_length,
            metadata={
                "num_merged_contexts": len(contexts),
                "unique_sources": len(set(all_sources)),
            },
        )
    
    def truncate_context(
        self,
        context: BuiltContext,
        max_length: Optional[int] = None,
        strategy: str = "end",  # "end" or "middle"
    ) -> BuiltContext:
        """
        Truncate context to maximum length.
        
        Args:
            context: BuiltContext to truncate
            max_length: Maximum length (uses self.max_context_length if None)
            strategy: Truncation strategy (end = remove from end, middle = keep start+end)
            
        Returns:
            Truncated BuiltContext
        """
        max_length = max_length or self.max_context_length
        
        if len(context.context_text) <= max_length:
            return context
        
        if strategy == "end":
            truncated_text = context.context_text[:max_length] + "..."
        else:  # middle
            keep_len = (max_length - 3) // 2  # 3 for "..."
            truncated_text = (
                context.context_text[:keep_len] +
                "...\n[content truncated]\n..." +
                context.context_text[-keep_len:]
            )
        
        logger.warning(
            f"Truncated context from {len(context.context_text)} "
            f"to {len(truncated_text)} characters"
        )
        
        return BuiltContext(
            context_text=truncated_text,
            sources=context.sources,
            num_documents=context.num_documents,
            total_length=len(truncated_text),
            metadata=context.metadata,
        )
    
    @staticmethod
    def get_context_stats(context: BuiltContext) -> Dict:
        """Get statistics about built context."""
        return {
            "total_length": context.total_length,
            "num_documents": context.num_documents,
            "num_sources": len(set(context.sources)),
            "avg_doc_length": context.total_length // context.num_documents if context.num_documents else 0,
            "sources": list(set(context.sources)),
        }
