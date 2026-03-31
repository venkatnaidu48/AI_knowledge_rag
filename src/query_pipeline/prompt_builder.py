"""
Query Pipeline - Prompt Builder Module
Formats retrieved context + question into prompts for LLM generation
"""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class PromptTemplate(str, Enum):
    """Available prompt templates."""
    BASIC = "basic"
    DETAILED = "detailed"
    CONTEXT_FIRST = "context_first"
    QA_STRUCTURED = "qa_structured"
    SUMMARIZATION = "summarization"


class PromptBuilder:
    """
    Build prompts from retrieved context and user queries.
    Formats retrieved chunks for LLM consumption with metadata.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        """
        Initialize prompt builder.
        
        Args:
            model_name: Target LLM model name (affects prompt formatting)
        """
        self.model_name = model_name
        self.template = PromptTemplate.DETAILED
        self.max_context_tokens = 2000
        
    def build_prompt(
        self,
        query: str,
        search_results: List[Dict],
        template: Optional[PromptTemplate] = None,
        include_sources: bool = True,
        include_metadata: bool = True,
    ) -> Dict:
        """
        Build complete prompt from query and search results.
        
        Args:
            query: User question
            search_results: Retrieved chunks from vector search
            template: Prompt template to use
            include_sources: Include document source information
            include_metadata: Include chunk metadata (rank, document, etc.)
        
        Returns:
            {
                "prompt": str,  # Full formatted prompt
                "context": str,  # Context section only
                "system_prompt": str,  # System instructions
                "context_tokens": int,  # Estimated tokens in context
                "template_used": str,
                "chunks_included": int,
            }
        """
        template = template or self.template
        
        # Validate inputs
        if not query or not isinstance(query, str):
            return self._error_response("Invalid query")
        
        if not search_results or not isinstance(search_results, list):
            search_results = []
        
        # Build context from results
        context = self._build_context_section(
            search_results,
            include_sources=include_sources,
            include_metadata=include_metadata,
        )
        
        # Get system prompt
        system_prompt = self._get_system_prompt(template)
        
        # Build full prompt based on template
        if template == PromptTemplate.BASIC:
            full_prompt = self._build_basic_prompt(query, context)
        elif template == PromptTemplate.DETAILED:
            full_prompt = self._build_detailed_prompt(query, context, search_results)
        elif template == PromptTemplate.CONTEXT_FIRST:
            full_prompt = self._build_context_first_prompt(query, context)
        elif template == PromptTemplate.QA_STRUCTURED:
            full_prompt = self._build_qa_structured_prompt(query, context, search_results)
        elif template == PromptTemplate.SUMMARIZATION:
            full_prompt = self._build_summarization_prompt(query, context)
        else:
            full_prompt = self._build_detailed_prompt(query, context, search_results)
        
        # Estimate tokens
        context_tokens = self._estimate_tokens(context)
        
        logger.info(f"[OK] Prompt built ({len(search_results)} chunks, ~{context_tokens} tokens)")
        
        return {
            "success": True,
            "prompt": full_prompt,
            "context": context,
            "system_prompt": system_prompt,
            "context_tokens": context_tokens,
            "template_used": template.value,
            "chunks_included": len(search_results),
            "query": query,
        }
    
    def _build_context_section(
        self,
        search_results: List[Dict],
        include_sources: bool = True,
        include_metadata: bool = True,
    ) -> str:
        """Build formatted context from search results."""
        if not search_results:
            return "No relevant context found."
        
        context_parts = []
        
        for idx, result in enumerate(search_results[:10], 1):  # Limit to top 10
            chunk_text = result.get("text", "")
            
            # Add metadata if requested
            if include_metadata:
                line = f"[{idx}] (Relevance: {result.get('similarity_score', 0):.1%})"
                if include_sources:
                    line += f" {result.get('document_title', 'Unknown')}"
                context_parts.append(line)
            
            context_parts.append(chunk_text)
            context_parts.append("")  # Empty line separator
        
        return "\n".join(context_parts)
    
    def _get_system_prompt(self, template: PromptTemplate) -> str:
        """Get system prompt for template."""
        prompts = {
            PromptTemplate.BASIC: (
                "You are a helpful business assistant. Answer questions accurately "
                "based on the provided context. If the answer is not in the context, say so."
            ),
            PromptTemplate.DETAILED: (
                "You are an expert business analyst. Answer the user's question comprehensively "
                "using the retrieved context. Include relevant details, cite sources when appropriate, "
                "and clearly state if information is not available in the provided context."
            ),
            PromptTemplate.CONTEXT_FIRST: (
                "First, analyze the provided context carefully. Then, answer the user's question "
                "based strictly on that context. Highlight any assumptions or limitations."
            ),
            PromptTemplate.QA_STRUCTURED: (
                "You are an AI that answers questions in structured format. "
                "Provide a clear answer, supporting evidence, and any relevant caveats."
            ),
            PromptTemplate.SUMMARIZATION: (
                "You are an expert summarizer. Based on the provided context, "
                "create a comprehensive summary addressing the user's query."
            ),
        }
        return prompts.get(template, prompts[PromptTemplate.DETAILED])
    
    def _build_basic_prompt(self, query: str, context: str) -> str:
        """Build basic prompt template."""
        return f"""Context:
{context}

Question: {query}

Answer:"""
    
    def _build_detailed_prompt(
        self,
        query: str,
        context: str,
        search_results: List[Dict],
    ) -> str:
        """Build detailed prompt template with metadata."""
        answer_count = len(search_results)
        
        return f"""You are analyzing business documents to answer a specific question.

Retrieved Context Sources: {answer_count} relevant sections

CONTEXT:
{context}

QUESTION:
{query}

INSTRUCTIONS:
1. Answer based ON the context provided above
2. Be specific and cite section numbers when helpful
3. If the answer is not clearly in the context, state this
4. Provide relevant supporting details from the context

ANSWER:"""
    
    def _build_context_first_prompt(self, query: str, context: str) -> str:
        """Build context-first prompt (good for understanding relationships)."""
        return f"""BACKGROUND INFORMATION:
{context}

Based on the context above, please answer this question:

{query}

Please provide:
1. A direct answer to the question
2. Supporting information from the context
3. Any relevant details not directly asked but important to understand

Answer:"""
    
    def _build_qa_structured_prompt(
        self,
        query: str,
        context: str,
        search_results: List[Dict],
    ) -> str:
        """Build structured Q&A prompt."""
        sources = [r.get("document_title", "Unknown") for r in search_results[:3]]
        
        return f"""Question: {query}

Relevant Documents: {", ".join(sources)}

Context:
{context}

Please provide your answer in this format:
- Answer: [Your main answer]
- Supporting Evidence: [Specific details from context]
- Source Documentation: [Which documents support this]
- Limitations: [Any gaps or uncertainties]

Answer:"""
    
    def _build_summarization_prompt(self, query: str, context: str) -> str:
        """Build summarization prompt."""
        return f"""Based on the following business context, summarize key information related to: {query}

CONTEXT MATERIAL:
{context}

Please provide:
1. Executive Summary (2-3 sentences)
2. Key Points (bullet list)
3. Important Details
4. Recommendations (if applicable)

Summary:"""
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using simple heuristic.
        ~1 token per 4 characters for English text.
        """
        return max(1, len(text) // 4)
    
    def _error_response(self, error: str) -> Dict:
        """Build error response."""
        return {
            "success": False,
            "error": error,
        }
    
    def set_template(self, template: PromptTemplate):
        """Set default prompt template."""
        if isinstance(template, str):
            self.template = PromptTemplate(template)
        else:
            self.template = template
        logger.info(f"Prompt template set to: {self.template.value}")
    
    def set_max_context_tokens(self, max_tokens: int):
        """Set maximum tokens for context."""
        self.max_context_tokens = max(100, max_tokens)
        logger.info(f"Max context tokens set to: {self.max_context_tokens}")
    
    def get_available_templates(self) -> List[str]:
        """Get list of available prompt templates."""
        return [t.value for t in PromptTemplate]
    
    def get_template_info(self, template_name: str) -> Dict:
        """Get information about a prompt template."""
        template_info = {
            "basic": {
                "name": "Basic",
                "description": "Simple context + question format",
                "best_for": "Quick answers, simple questions",
                "token_efficiency": "High",
            },
            "detailed": {
                "name": "Detailed",
                "description": "Comprehensive with metadata and instructions",
                "best_for": "Complex analysis, detailed responses",
                "token_efficiency": "Medium",
            },
            "context_first": {
                "name": "Context First",
                "description": "Emphasizes context analysis before answering",
                "best_for": "Understanding relationships, document analysis",
                "token_efficiency": "Medium",
            },
            "qa_structured": {
                "name": "QA Structured",
                "description": "Structured Q&A with evidence and limitations",
                "best_for": "Research, fact-checking",
                "token_efficiency": "Medium-High",
            },
            "summarization": {
                "name": "Summarization",
                "description": "Optimized for document summarization",
                "best_for": "Executive summaries, condensing information",
                "token_efficiency": "High",
            },
        }
        return template_info.get(template_name, {})


# Singleton instance
_prompt_builder: Optional[PromptBuilder] = None


def get_prompt_builder(model_name: str = "gpt-4") -> PromptBuilder:
    """
    Get or create prompt builder singleton.
    
    Args:
        model_name: Target LLM model name
    
    Returns:
        Singleton PromptBuilder instance
    """
    global _prompt_builder
    
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder(model_name)
        logger.info(f"[OK] Prompt builder initialized (model: {model_name})")
    
    return _prompt_builder
