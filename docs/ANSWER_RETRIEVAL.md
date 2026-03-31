# How to Retrieve Answers from RAG Database - Complete Guide

## 🎯 Overview

Your RAG system has **3 layers of storage and retrieval**:

```
┌─────────────────────────────────────────────────────────────┐
│  📄 DOCUMENTS LAYER                                        │
│  - Original files (PDF, DOCX, TXT, XLSX)                   │
│  - Metadata: department, sensitivity, owner, version       │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  📑 CHUNKS LAYER                                           │
│  - Documents split into smaller pieces                     │
│  - Each chunk has: number, text, importance, quality       │
│  - Vector embeddings for semantic search                   │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  🔍 RETRIEVAL METHODS                                      │
│  1. Direct database queries                                │
│  2. REST API endpoints (easiest)                           │
│  3. AI-powered semantic search                             │
│  4. Keyword search                                         │
│  5. Question & Answer                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Method 1: REST API (EASIEST - Start Here!)

### Best For: Everyone - no coding required!

**Step 1: Open Interactive API**
```
http://localhost:8000/docs
```

**Step 2: Try any endpoint:**

1. **View Documents**
   - Endpoint: `GET /api/v1/documents/`
   - Click "Try it out" → "Execute"
   - See all documents in database

2. **Search Database**
   - Endpoint: `POST /api/v1/search/semantic`
   - Body: `{"query": "your search term", "top_k": 5}`
   - See most relevant chunks

3. **Ask Question**
   - Endpoint: `POST /api/v1/query/process`
   - Body: `{"query": "your question", "k": 5}`
   - Get relevant chunks with scores

4. **Generate Answer**
   - Endpoint: `POST /api/v1/generation/generate`
   - Provide query and context
   - Get AI-powered response

5. **Validate Quality**
   - Endpoint: `POST /api/v1/validation/validate-single`
   - Check answer quality with scores

---

## ✅ Method 2: Python Script (Ready to Run)

### Best For: Automation and batch processing

**Run the script:**
```bash
python scripts/retrieve_answers.py
```

**What it does:**
1. Shows database summary
2. Lists all documents
3. Demonstrates keyword search
4. Answers sample questions
5. Validates responses

**Output example:**
```
📊 DATABASE SUMMARY
✅ Total Documents: 3
✅ Total Chunks: 156

📄 Documents in Database:
   1. company-about.md
      - ID: abc123...
      - Department: HR
      - Chunks: 45
      - Status: active
```

---

## ✅ Method 3: Direct Database Queries (Python)

### Best For: Custom applications and integrations

**Example code:**

```python
from sqlalchemy.orm import Session
from src.database.models import Document, DocumentChunk
from src.database.database import SessionLocal

# Get database connection
db: Session = SessionLocal()

# ========== RETRIEVE ALL DOCUMENTS ==========
documents = db.query(Document).all()
for doc in documents:
    print(f"📄 {doc.name}")
    print(f"   ID: {doc.id}")
    print(f"   Chunks: {len(doc.chunks)}")
    print(f"   Department: {doc.department}")

# ========== GET CHUNKS FROM A DOCUMENT ==========
chunks = db.query(DocumentChunk).filter(
    DocumentChunk.document_id == document_id
).order_by(DocumentChunk.chunk_number).all()

for chunk in chunks:
    print(f"Chunk {chunk.chunk_number}: {chunk.chunk_text}")

# ========== SEARCH FOR TEXT ==========
results = db.query(DocumentChunk).filter(
    DocumentChunk.chunk_text.ilike("%salary%")
).all()

for result in results:
    print(f"Found in chunk {result.chunk_number}: {result.chunk_text}")

# Close connection
db.close()
```

---

## ✅ Method 4: cURL Commands (Terminal)

### Best For: Quick testing and scripting

**List all documents:**
```bash
curl http://localhost:8000/api/v1/documents/
```

**Search for something:**
```bash
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "company policy",
    "top_k": 5
  }'
```

**Ask a question:**
```bash
curl -X POST http://localhost:8000/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the benefits?",
    "k": 5
  }'
```

**Generate AI answer:**
```bash
curl -X POST http://localhost:8000/api/v1/generation/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the benefits?",
    "context": ["Employees get health insurance, 401k matching..."],
    "provider": "openai"
  }'
```

---

## ✅ Method 5: Python Requests (Programmatic)

### Best For: Integration into Python applications

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# ========== GET ALL DOCUMENTS ==========
response = requests.get(f"{BASE_URL}/documents/")
documents = response.json()
print(f"Found {documents['total']} documents")

# ========== SEMANTIC SEARCH ==========
response = requests.post(
    f"{BASE_URL}/search/semantic",
    json={"query": "salary policy", "top_k": 5}
)
results = response.json()
for result in results['results']:
    print(f"Score: {result['similarity_score']:.2f}")
    print(f"Text: {result['text']}")

# ========== QUERY AND GET CHUNKS ==========
response = requests.post(
    f"{BASE_URL}/query/process",
    json={"query": "What is the vacation policy?", "k": 5}
)
query_results = response.json()
print(f"Found {query_results['result_count']} results")
for r in query_results['search_results']:
    print(f"- {r['document_title']}: {r['text'][:100]}...")

# ========== GENERATE ANSWER ==========
context = [r['text'] for r in query_results['search_results']]
response = requests.post(
    f"{BASE_URL}/generation/generate",
    json={
        "query": "What is the vacation policy?",
        "context": context,
        "provider": "openai"
    }
)
answer = response.json()
print(f"Answer: {answer['response']}")
print(f"Confidence: {answer['confidence']:.2%}")

# ========== VALIDATE QUALITY ==========
response = requests.post(
    f"{BASE_URL}/validation/validate-single",
    json={
        "response_text": answer['response'],
        "query": "What is the vacation policy?",
        "context_chunks": context
    }
)
validation = response.json()
print(f"Quality Score: {validation['overall_score']:.2f}")
```

---

## 🗂️ Database Schema

### Documents Table
```
documents:
  - id (UUID)
  - name (Document name)
  - department (Department)
  - sensitivity (Level: public/internal/confidential)
  - status (active/archived/deprecated)
  - upload_date (When uploaded)
  - file_size_bytes (File size)
  - owner_email (Document owner)
  - chunks[] (Connected chunks)
```

### Chunks Table
```
document_chunks:
  - id (UUID)
  - document_id (Parent document)
  - chunk_number (Sequential number)
  - chunk_text (Actual text)
  - importance_score (0-1)
  - quality_score (0-1)
  - tokens_count (Word count)
  - embedding_generated (Boolean)
```

### Embeddings Table
```
chunk_embeddings:
  - chunk_id (From chunks)
  - embedding_vector (Vector [1536 dimensions])
  - embedding_model (text-embedding-3-small)
  - status (ready/processing/failed)
```

---

## 📊 Complete Workflow Diagram

```
USER HAS QUESTION
       ↓
       ├─→ METHOD 1: REST API
       │   └─→ POST /api/v1/query/process
       │       └─→ Returns: Relevant chunks with scores
       │
       ├─→ METHOD 2: Python Script
       │   └─→ python scripts/retrieve_answers.py
       │       └─→ Shows: Database summary, search, Q&A
       │
       ├─→ METHOD 3: Direct Python Query
       │   └─→ QueryChunk from database
       │       └─→ Returns: Raw chunk data
       │
       ├─→ METHOD 4: cURL
       │   └─→ curl http://localhost:8000/...
       │       └─→ Returns: JSON response
       │
       └─→ METHOD 5: Python Requests
           └─→ requests.post()
               └─→ Returns: JSON parsed data

RETRIEVE RELEVANT CHUNKS
       ↓
OPTIONAL: GENERATE AI ANSWER
       ├─→ POST /api/v1/generation/generate
       └─→ Returns: AI-powered response
       ↓
OPTIONAL: VALIDATE QUALITY
       ├─→ POST /api/v1/validation/validate-single
       └─→ Returns: Quality score (0-1)
       ↓
RETURN TO USER
```

---

## 🚀 Quick Start Checklist

- [ ] Open [http://localhost:8000/docs](http://localhost:8000/docs)
- [ ] Upload a PDF/DOCX/TXT using POST /api/v1/documents/upload
- [ ] Wait for processing to complete
- [ ] Click GET /api/v1/documents/ to see uploaded document
- [ ] Click POST /api/v1/query/process and ask a question
- [ ] View results in the response
- [ ] (Optional) Generate AI answer with POST /api/v1/generation/generate
- [ ] (Optional) Validate answer with POST /api/v1/validation/validate-single

---

## 📈 Advanced: Combining Methods

### Complete Q&A Pipeline:

```python
import requests

# Step 1: User asks question
question = "What is the company's vacation policy?"

# Step 2: Search database for relevant information
search_response = requests.post(
    "http://localhost:8000/api/v1/query/process",
    json={"query": question, "k": 5}
)
search_results = search_response.json()

# Step 3: Extract context chunks
context_chunks = [
    result['text'] 
    for result in search_results['search_results']
]

# Step 4: Generate AI response
gen_response = requests.post(
    "http://localhost:8000/api/v1/generation/generate",
    json={
        "query": question,
        "context": context_chunks,
        "provider": "openai"
    }
)
answer = gen_response.json()

# Step 5: Validate answer quality
val_response = requests.post(
    "http://localhost:8000/api/v1/validation/validate-single",
    json={
        "response_text": answer['response'],
        "query": question,
        "context_chunks": context_chunks
    }
)
validation = val_response.json()

# Step 6: Return to user
print(f"Question: {question}")
print(f"Answer: {answer['response']}")
print(f"Quality: {validation['overall_score']:.0%}")
print(f"Sources: {len(search_results['search_results'])} documents")
```

---

## 🆘 Common Questions

### Q1: Where is my data stored?
**A:** SQLite database at `rag_dev.db` in project root. Tables: documents, document_chunks, chunk_embeddings.

### Q2: How do I retrieve just document names?
**A:** `GET /api/v1/documents/` or query: `db.query(Document.name).all()`

### Q3: How do I search for specific text?
**A:** Use `POST /api/v1/search/semantic` endpoint with keyword.

### Q4: Can I get answers in multiple languages?
**A:** Yes! Use LLM providers that support your language (OpenAI, Groq, etc.)

### Q5: How do I export my data?
**A:** Use Python script to query and export to CSV/JSON:
```python
import csv
from src.database.models import Document, DocumentChunk  
from src.database.database import SessionLocal

db = SessionLocal()
chunks = db.query(DocumentChunk).all()

with open('export.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Document', 'Chunk', 'Text'])
    for c in chunks:
        writer.writerow([c.document_id, c.chunk_number, c.chunk_text])
```

### Q6: How do I delete documents?
**A:** `DELETE /api/v1/documents/{document_id}` or Python: `db.delete(doc); db.commit()`

### Q7: Can I retrieve query history?
**A:** Yes! `GET /api/v1/query/history` (see API docs for full endpoint)

### Q8: How do I improve search accuracy?
**A:** Adjust `score_threshold` (lower = more results), use better keywords, upload high-quality documents

---

## 📚 Available Resources

| Resource | Link | Purpose |
|----------|------|---------|
| API Docs | http://localhost:8000/docs | Interactive testing |
| Health Check | http://localhost:8000/health | Server status |
| Full Guide | docs/RETRIEVAL_GUIDE.md | Detailed instructions |
| Python Script | scripts/retrieve_answers.py | Runnable demo |
| Quick Start | docs/QUICK_START_RETRIEVAL.md | Quick reference |

---

## ✨ Summary

You have **5 ways** to retrieve answers:

1. **REST API (Swagger UI)** - Best for quick testing, no code required
2. **Python Script** - Best for automation and demos
3. **Direct Database** - Best for custom applications
4. **cURL** - Best for shell scripting
5. **Python Requests** - Best for programmatic integration

**Start with Method 1 (REST API)** - it's the easiest!

---

**Last Updated**: March 2, 2026  
**Status**: Production Ready ✅

For more details, see the documentation in `docs/` folder.
