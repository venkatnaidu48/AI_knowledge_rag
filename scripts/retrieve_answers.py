#!/usr/bin/env python
"""
Retrieve Answers from Knowledge Base
Standalone script for programmatic query execution
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database import SessionLocal
from src.database.models import Document, DocumentChunk
from config.settings import get_settings
import logging
import requests
from typing import List, Tuple

# Suppress verbose logs
logging.disable(logging.CRITICAL)

settings = get_settings()


def search_knowledge_base(query: str, limit: int = 5) -> List[Tuple]:
    """
    Search knowledge base for relevant chunks
    
    Args:
        query: User query string
        limit: Maximum chunks to return
        
    Returns:
        List of (chunk, document) tuples
    """
    db = SessionLocal()
    
    try:
        if not query.strip():
            return []
        
        # Extract keywords from query
        keywords = [w for w in query.lower().split() if len(w) > 2]
        results = []
        seen_chunks = set()
        
        # Search for each keyword
        for keyword in keywords[:3]:
            chunks = db.query(DocumentChunk, Document).join(
                Document, DocumentChunk.document_id == Document.id
            ).filter(
                DocumentChunk.chunk_text.ilike(f"%{keyword}%")
            ).limit(limit).all()
            
            for chunk, doc in chunks:
                if chunk.id not in seen_chunks:
                    seen_chunks.add(chunk.id)
                    results.append((chunk, doc))
        
        return results[:limit]
        
    finally:
        db.close()


def generate_answer(question: str, chunks_and_docs: List[Tuple], 
                   use_ollama: bool = True) -> Tuple[str, List[Tuple]]:
    """
    Generate answer from context chunks
    
    Args:
        question: User question
        chunks_and_docs: Retrieved chunks and documents
        use_ollama: Whether to use Ollama for generation
        
    Returns:
        Tuple of (answer_text, sources)
    """
    if not chunks_and_docs:
        return ("No information found in the knowledge base.", [])
    
    # Build context from chunks
    context = ""
    sources = []
    
    for i, (chunk, doc) in enumerate(chunks_and_docs[:3], 1):
        context += f"\n[Document {i}: {doc.name}]\n{chunk.chunk_text[:1000]}\n"
        sources.append((i, doc.name))
    
    # Build prompt
    prompt = f"""Based on the provided documents, answer the following question accurately and concisely.

Question: {question}

Documents:
{context}

Answer:"""

    if not use_ollama:
        # Simple keyword-based extraction fallback
        answer = "Unable to generate answer (Ollama not available). Retrieved documents:\n"
        for idx, (chunk, doc) in enumerate(chunks_and_docs[:2], 1):
            answer += f"\n{idx}. From {doc.name}: {chunk.chunk_text[:200]}..."
        return answer, sources

    try:
        # Query Ollama
        url = "http://localhost:11434/api/generate"
        
        payload = {
            "model": "mistral:latest",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 200
        }
        
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', '').strip()
            answer = ' '.join(answer.split())
        else:
            answer = f"Error generating answer (HTTP {response.status_code})"
            
    except requests.exceptions.Timeout:
        answer = "Response timed out. Try again later."
    except requests.exceptions.ConnectionError:
        answer = "Ollama service not running at localhost:11434"
    except Exception as e:
        answer = f"Error: {str(e)}"
    
    return answer, sources


def retrieve_answer(query: str, verbose: bool = False) -> dict:
    """
    Main function to retrieve answer for a query
    
    Args:
        query: User question
        verbose: Print detailed output
        
    Returns:
        Dictionary with answer, sources, and metadata
    """
    if verbose:
        print(f"\n🔍 Searching for: {query}")
    
    # Search knowledge base
    results = search_knowledge_base(query, limit=5)
    
    if not results:
        if verbose:
            print("❌ No relevant documents found")
        return {
            "query": query,
            "answer": "No information found to answer this question.",
            "sources": [],
            "chunks_found": 0
        }
    
    if verbose:
        print(f"✅ Found {len(results)} relevant chunks")
    
    # Generate answer
    answer, sources = generate_answer(query, results)
    
    if verbose:
        print(f"\n📝 Answer:\n{answer}\n")
        print(f"📚 Sources:")
        for idx, source in sources:
            print(f"   {idx}. {source}")
    
    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_found": len(results)
    }


def main():
    """
    Main entry point - accepts query via command line or stdin
    """
    if len(sys.argv) > 1:
        # Query provided as command line argument
        query = ' '.join(sys.argv[1:])
        result = retrieve_answer(query, verbose=True)
        print(f"\nAnswer: {result['answer']}")
    else:
        # Interactive mode
        print("\n" + "="*80)
        print("Knowledge Base Answer Retrieval")
        print("="*80)
        print("Enter your question (or 'quit' to exit):\n")
        
        while True:
            try:
                query = input("❓ Question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                result = retrieve_answer(query, verbose=True)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    main()
