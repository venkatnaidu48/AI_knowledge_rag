#!/usr/bin/env python
"""
FAST Knowledge Base Q&A - Optimized for Speed
- Minimal chunks sent to LLM (1-2 only)
- Faster Mistral inference
- Reduced timeout, early stopping
"""
import sys
sys.path.insert(0, '.')

from src.database.database import SessionLocal
from src.database.models import Document, DocumentChunk
from config.settings import get_settings
import logging
import requests

# Suppress ALL logs for cleaner output
logging.disable(logging.CRITICAL)

settings = get_settings()

def search_knowledge_base(query: str, limit: int = 2):
    """Search knowledge base - OPTIMIZED: Return only TOP 2 chunks"""
    
    db = SessionLocal()
    
    try:
        if not query.strip():
            return []
        
        keywords = [w for w in query.lower().split() if len(w) > 2]
        results = []
        seen_chunks = set()
        
        for keyword in keywords[:2]:  # REDUCED: Only first 2 keywords
            chunks = db.query(DocumentChunk, Document).join(
                Document, DocumentChunk.document_id == Document.id
            ).filter(
                DocumentChunk.chunk_text.ilike(f"%{keyword}%")
            ).limit(limit).all()
            
            for chunk, doc in chunks:
                if chunk.id not in seen_chunks:
                    seen_chunks.add(chunk.id)
                    results.append((chunk, doc))
        
        return results[:2]  # OPTIMIZED: Return only TOP 2 results
        
    finally:
        db.close()

def generate_answer_fast(question: str, chunks_and_docs):
    """Generate answer with MINIMAL context for speed"""
    
    if not chunks_and_docs:
        return ("❌ No information found in the knowledge base.", [])
    
    # Build MINIMAL context - only from top 1 chunk
    context = ""
    sources = []
    
    for i, (chunk, doc) in enumerate(chunks_and_docs[:1], 1):  # OPTIMIZED: Only 1 chunk
        context += chunk.chunk_text[:500]  # OPTIMIZED: Limit to 500 chars
        sources.append((i, doc.name))
    
    # SHORT, FOCUSED PROMPT for faster inference
    prompt = f"""Answer in one sentence only.

Q: {question}
Context: {context}
Answer:"""

    try:
        url = "http://localhost:11434/api/generate"
        
        payload = {
            "model": "mistral:latest",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.2,  # OPTIMIZED: Lower temp for faster/focused responses
            "top_p": 0.8,  # OPTIMIZED: Reduced diversity
            "num_predict": 50  # OPTIMIZED: Max 50 tokens = ~40 words
        }
        
        # OPTIMIZED: Timeout reduced from 300s to 60s (Mistral usually responds in 5-20s)
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', '').strip()
            answer = ' '.join(answer.split())
        else:
            answer = f"Error generating answer (HTTP {response.status_code})"
            
    except requests.exceptions.Timeout:
        answer = "⏱️  Response timed out. Try again or use interactive_qa.py for instant results."
    except requests.exceptions.ConnectionError:
        answer = "❌ Ollama not running. Make sure Ollama is started!"
    except Exception as e:
        answer = f"❌ Error: {str(e)}"
    
    return answer, sources

def ask_question(query: str):
    """Main Q&A function - OPTIMIZED"""
    
    print(f"⚡ Searching...", end=" ", flush=True)
    
    results = search_knowledge_base(query)
    
    if not results:
        print("\r❌ No information found.\n")
        return
    
    print("\r🔄 Generating...", end=" ", flush=True)
    
    answer, sources = generate_answer_fast(query, results)
    
    print("\r" + " " * 30 + "\r", end="")  # Clear line
    print("─" * 80)
    print(answer)
    print("─" * 80)
    print()

def main():
    """Main interactive loop"""
    
    print("\n" + "="*80)
    print("⚡ FAST Q&A - OPTIMIZED FOR SPEED (3-15 seconds)")
    print("="*80)
    print("\n📌 Instructions:")
    print("   • Type your question and press Enter")
    print("   • Type 'quit' or 'exit' to exit")
    print("   • Optimized for ~5-15s responses (vs 10-60s in advanced_qa)")
    print("\n" + "="*80 + "\n")
    
    while True:
        try:
            question = input("❓ Your Question: ").strip()
            
            if not question:
                print("⚠️  Please enter a question.\n")
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break
            
            if question.lower() == 'help':
                print("\n📚 Example questions:")
                print("   • What is the company about?")
                print("   • Tell me about contract terms")
                print("   • What are the security policies?")
                print("   • Who are the key employees?\n")
                continue
            
            ask_question(question)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    main()
