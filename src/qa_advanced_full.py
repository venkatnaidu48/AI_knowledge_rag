#!/usr/bin/env python
"""
ADVANCED Q&A SYSTEM - Full Knowledge Base Integration
- Loads ALL knowledge base documents
- Supports continuous document updates
- Better relevance matching
- LLM-powered answer generation (optional)
- Proper source attribution
"""
import sys
import os

# Add parent directory (project root) to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database.database import SessionLocal
from src.database.models import Document, DocumentChunk
import re
from typing import Optional, Dict, List

# Comprehensive stopwords
STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'or', 'and', 'of', 'to', 'for', 'in', 'on', 'at', 'by', 'from', 'as', 'be', 
    'what', 'how', 'when', 'where', 'why', 'which', 'who', 'if', 'that', 'this', 'was', 'been', 'being', 'have', 
    'has', 'had', 'do', 'does', 'did', 'should', 'will', 'would', 'could', 'may', 'might', 'can', 'just', 'more', 
    'only', 'some', 'any', 'you', 'your', 'we', 'our', 'they', 'them', 'with', 'about', 'out', 'after', 'before',
    'up', 'down', 'all', 'each', 'no', 'not', 'but', 'then', 'now', 'also', 'here', 'there', 'have', 'do', 'does'
}

class AdvancedQASystem:
    """Advanced Q&A system with knowledge base support"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def extract_meaningful_keywords(self, question: str) -> List[str]:
        """Extract meaningful keywords from question"""
        # Remove punctuation and convert to lowercase
        words = re.sub(r'[^\w\s]', '', question.lower()).split()
        
        # Filter: longer than 2 chars and not a stopword
        meaningful = [w for w in words if len(w) > 2 and w not in STOP_WORDS]
        
        return meaningful
    
    def search_knowledge_base(self, question: str, min_keywords_present: float = 1.0) -> Optional[Dict]:
        """
        Search knowledge base for relevant chunks
        min_keywords_present: float between 0-1 indicating minimum fraction of keywords that must be present
            1.0 = ALL keywords must be present (strictest, no false positives)
            0.5 = At least 50% of keywords must be present
        """
        meaningful_keywords = self.extract_meaningful_keywords(question)
        
        if not meaningful_keywords:
            return None
        
        best_result = None
        best_score = 0
        
        # Search for chunks containing ANY meaningful keyword
        for keyword in meaningful_keywords[:5]:
            chunks = self.db.query(DocumentChunk, Document).join(
                Document, DocumentChunk.document_id == Document.id
            ).filter(
                DocumentChunk.chunk_text.ilike(f"%{keyword}%")
            ).limit(25).all()
            
            for chunk, doc in chunks:
                # Calculate how many meaningful keywords are present
                chunk_lower = chunk.chunk_text.lower()
                keywords_found = sum(1 for kw in meaningful_keywords if kw in chunk_lower)
                
                # Calculate score: ratio of keywords found to total keywords
                score = keywords_found / len(meaningful_keywords)
                
                # Apply threshold - only accept if enough keywords present
                if score >= min_keywords_present:
                    if score > best_score:
                        best_score = score
                        best_result = {
                            "chunk": chunk,
                            "doc": doc,
                            "keywords": meaningful_keywords,
                            "keywords_found": keywords_found,
                            "score": score,
                            "relevance_percent": int(score * 100)
                        }
        
        return best_result if best_result and best_score > 0 else None
    
    def get_answer(self, question: str, threshold: float = 0.8) -> str:
        """
        Get answer from knowledge base
        threshold: minimum relevance required (0.0 = 0%, 1.0 = 100%)
        """
        result = self.search_knowledge_base(question, min_keywords_present=threshold)
        
        if not result:
            return "Answer not found in knowledge base."
        
        # Create summary
        chunk_text = result["chunk"].chunk_text
        if len(chunk_text) > 600:
            summary = chunk_text[:600] + "\n\n[...more information available...]"
        else:
            summary = chunk_text
        
        # Format answer with source
        answer = f"{summary}\n\n"
        answer += f"[Source: {result['doc'].name}]\n"
        answer += f"[Confidence: {result['relevance_percent']}%]"
        
        return answer
    
    def close(self):
        """Close database connection"""
        self.db.close()

def main():
    """Main function"""
    system = AdvancedQASystem()
    
    if len(sys.argv) > 1:
        # Command line mode
        question = ' '.join(sys.argv[1:])
        threshold = 0.8  # Require 80% of keywords
        
        print(f"Q: {question}\n")
        answer = system.get_answer(question, threshold=threshold)
        print(f"A: {answer}\n")
    else:
        # Interactive mode
        print("\n" + "="*80)
        print("ADVANCED Q&A SYSTEM - Full Knowledge Base")
        print("Type 'quit' or 'exit' to end")
        print("="*80 + "\n")
        
        while True:
            try:
                question = input("Q: ").strip()
                
                if not question:
                    continue
                
                if question.lower() in ['quit', 'exit', 'q']:
                    break
                
                threshold = 0.8  # Require 80% keyword match by default
                answer = system.get_answer(question, threshold=threshold)
                
                print(f"\nA: {answer}\n")
                
            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                print(f"\nA: Error - {e}\n")
    
    system.close()

if __name__ == "__main__":
    main()
