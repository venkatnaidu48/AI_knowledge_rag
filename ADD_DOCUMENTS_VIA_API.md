# 📤 How to Add Documents to Your RAG System via API

## 🎯 Quick Start (30 seconds)

```bash
# Method 1: Using cURL (simplest)
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@my_document.pdf" \
  -F "department=HR" \
  -F "sensitivity=internal"
```

**Response:**
```json
{
  "success": true,
  "document_id": "doc-abc123",
  "name": "my_document.pdf",
  "chunks_created": 42,
  "file_size_bytes": 256000,
  "quality_score": 0.95
}
```

✅ **Document now searchable in your RAG system!**

---

## 📚 Complete Guide

### Prerequisites
- RAG application running (`python run.py`)
- Server accessible at `http://localhost:8000`
- Document files ready to upload (.pdf, .docx, .txt, etc.)

### Endpoint Details

**URL:** `POST http://localhost:8000/api/v1/documents/upload`

**Request Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | Binary | ✅ Yes | Document file (.pdf, .docx, .txt, .xlsx, .xls) |
| `department` | String | ❌ No | Department classification (e.g., "Finance", "HR", "Sales") |
| `sensitivity` | String | ❌ No | Security level: "public", "internal", "confidential" (default: "internal") |
| `owner_email` | String | ❌ No | Email of document owner |

---

## 🔥 Method 1: cURL (Command Line)

### Basic Upload
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@financial_report.pdf"
```

### With Metadata
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@financial_report.pdf" \
  -F "department=Finance" \
  -F "sensitivity=internal" \
  -F "owner_email=john@company.com"
```

### Multiple Files (one at a time)
```bash
for file in *.pdf; do
  curl -X POST "http://localhost:8000/api/v1/documents/upload" \
    -F "file=@$file"
done
```

### Save Response to File
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf" \
  -o upload_response.json
```

---

## 🐍 Method 2: Python (Recommended for Automation)

### Simple Upload
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/documents/upload",
    files={"file": open("document.pdf", "rb")}
)

result = response.json()
print(f"✅ Uploaded: {result['document_id']}")
print(f"📝 Chunks created: {result['chunks_created']}")
```

### With Metadata
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/documents/upload",
    files={"file": open("financial_report.pdf", "rb")},
    data={
        "department": "Finance",
        "sensitivity": "internal",
        "owner_email": "finance@company.com"
    }
)

result = response.json()
if result["success"]:
    print(f"✅ Document uploaded successfully!")
    print(f"   ID: {result['document_id']}")
    print(f"   Chunks: {result['chunks_created']}")
    print(f"   Quality: {result['quality_score']:.0%}")
else:
    print(f"❌ Upload failed: {result['errors']}")
```

### Batch Upload Multiple Documents
```python
import requests
import os
from pathlib import Path

# Directory containing documents
docs_folder = "path/to/documents"

for filename in os.listdir(docs_folder):
    if filename.endswith(('.pdf', '.docx', '.txt')):
        filepath = os.path.join(docs_folder, filename)
        
        print(f"Uploading {filename}...")
        
        response = requests.post(
            "http://localhost:8000/api/v1/documents/upload",
            files={"file": open(filepath, "rb")},
            data={
                "department": "General",
                "sensitivity": "internal"
            }
        )
        
        result = response.json()
        if result["success"]:
            print(f"  ✅ {result['chunks_created']} chunks created")
        else:
            print(f"  ❌ Error: {result['errors']}")
```

### Upload with Error Handling
```python
import requests
import json
from pathlib import Path

def upload_document(file_path, department=None, sensitivity="internal"):
    """Upload a document to the RAG system"""
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return None
    
    try:
        print(f"📤 Uploading: {Path(file_path).name}")
        
        with open(file_path, "rb") as f:
            response = requests.post(
                "http://localhost:8000/api/v1/documents/upload",
                files={"file": f},
                data={
                    "department": department or "Uncategorized",
                    "sensitivity": sensitivity
                },
                timeout=60  # 60 second timeout
            )
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print(f"✅ Success!")
                print(f"   Document ID: {result['document_id']}")
                print(f"   Chunks: {result['chunks_created']}")
                print(f"   Quality Score: {result['quality_score']:.1%}")
                return result
            else:
                print(f"❌ Upload failed: {result.get('errors', 'Unknown error')}")
                return None
        else:
            print(f"❌ Server error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        return None
    except requests.exceptions.Timeout:
        print("❌ Upload timeout. File too large?")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

# Usage examples
if __name__ == "__main__":
    # Single document
    upload_document(
        "financial_report_2026.pdf",
        department="Finance",
        sensitivity="internal"
    )
    
    # Multiple documents
    for doc in ["policy.pdf", "handbook.docx", "report.txt"]:
        upload_document(doc)
```

---

## 🔍 Method 3: Verify Upload Worked

### List All Documents
```bash
curl http://localhost:8000/api/v1/documents/list
```

**Response:**
```json
{
  "total": 124,
  "documents": [
    {
      "id": "doc-abc123",
      "name": "financial_report_2026.pdf",
      "uploaded_at": "2026-04-18T10:00:00",
      "chunks": 42,
      "status": "PROCESSED"
    },
    ...
  ]
}
```

### Get Specific Document Details
```bash
curl http://localhost:8000/api/v1/documents/doc-abc123
```

### Query the Document (Test that it's searchable)
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key financial metrics?",
    "context": {"document_ids": ["doc-abc123"]}
  }'
```

---

## 💡 Real-World Examples

### Example 1: HR Uploads New Policy

```python
import requests

# HR creates new work-from-home policy
response = requests.post(
    "http://localhost:8000/api/v1/documents/upload",
    files={"file": open("WFH_Policy_2026.pdf", "rb")},
    data={
        "department": "HR",
        "sensitivity": "internal",
        "owner_email": "hr.manager@company.com"
    }
)

result = response.json()
print(f"Policy uploaded: {result['document_id']}")

# ✅ Now employees can ask: "What's the new work-from-home policy?"
# ✅ System instantly returns the policy from the newly uploaded document!
```

### Example 2: Finance Uploads Quarterly Report

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/documents/upload",
    files={"file": open("Q1_2026_Financial_Report.xlsx", "rb")},
    data={
        "department": "Finance",
        "sensitivity": "confidential",  # More restrictive
        "owner_email": "cfo@company.com"
    }
)

# ✅ Now financial analysts can ask: "What was Q1 revenue?"
# ✅ System retrieves the answer from the just-uploaded report!
```

### Example 3: Batch Upload All Company Documents

```python
import requests
import os

documents_to_upload = {
    "annual_report_2025.pdf": {"department": "Finance", "sensitivity": "public"},
    "employee_handbook.docx": {"department": "HR", "sensitivity": "internal"},
    "security_policy.txt": {"department": "Security", "sensitivity": "confidential"},
    "sales_strategy.pdf": {"department": "Sales", "sensitivity": "internal"},
}

for filename, metadata in documents_to_upload.items():
    print(f"Uploading {filename}...")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/documents/upload",
            files={"file": open(filename, "rb")},
            data=metadata
        )
        
        if response.json()["success"]:
            print(f"  ✅ {response.json()['chunks_created']} chunks created")
        else:
            print(f"  ❌ Failed: {response.json()['errors']}")
    except FileNotFoundError:
        print(f"  ❌ File not found: {filename}")

print("✅ Batch upload complete!")
```

---

## ⏱️ What Happens Internally (Timeline)

When you upload a document via the API:

```
T+0.0s: File received by API endpoint
        ↓
T+0.1s: File stored temporarily in memory
        ↓
T+0.2s: Document metadata extracted and stored in DB
        ↓
T+1.0s: Document text parsed and cleaned
        ↓
T+2.0s: Text split into 512-char chunks with 100-char overlap
        ↓
T+3.5s: Each chunk converted to 384-dim embedding vector
        ↓
T+4.0s: Embeddings added to FAISS index
        ↓
T+4.5s: Document status updated to "PROCESSED"
        ↓
T+5.0s: API returns success response
        ↓
T+5.1s: ✅ Document is NOW SEARCHABLE!

Total time: ~5 seconds from upload to searchable
```

---

## 📊 Database Changes After Upload

**Before Upload:**
```
documents table: 123 rows
document_chunks table: 51,737 rows
chunk_embeddings table: 51,737 rows
FAISS index: 51,737 vectors
```

**After Uploading 1 Document (~25 chunks):**
```
documents table: 124 rows ← +1 new document
document_chunks table: 51,762 rows ← +25 new chunks
chunk_embeddings table: 51,762 rows ← +25 new embeddings
FAISS index: 51,762 vectors ← +25 new vectors
```

**Next Query Result:**
```
User asks: "Tell me about the new policy"
System searches: All 51,762 embeddings (includes NEW ones! ✅)
Returns: Chunks from newly uploaded document
```

---

## 🔐 Security Considerations

### Current State
⚠️ **Upload endpoint is NOT currently protected by authentication**

Add protection like this:

```python
# In src/api/routes/documents.py, add authentication requirement:

from src.api.middleware.auth import get_current_user

@router.post("/upload")
async def upload_document(
    file: UploadFile,
    current_user = Depends(get_current_user)  # ← Add this
):
    # Now only authenticated users can upload
    ...
```

### File Type Validation
✅ Supported formats: `.pdf`, `.docx`, `.txt`, `.xlsx`, `.xls`
❌ Rejected formats: `.exe`, `.bat`, `.sh` (for security)

### Size Limits
- Max file size: Check your API configuration
- Large files (>500MB) may need streaming upload

---

## 🚀 Next Steps After Upload

Once document is uploaded and searchable:

### Step 1: Verify It Works
```bash
# Query using the new document
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is mentioned in the new policy?"}'
```

### Step 2: Monitor Quality
```bash
# Check chunk quality and hallucination risk
curl http://localhost:8000/api/v1/documents/doc-abc123/quality
```

### Step 3: Track Usage
```python
# Get stats on which documents are being queried
curl http://localhost:8000/api/v1/analytics/documents
```

---

## 🎓 Complete Python Script (Copy-Paste Ready)

Save this as `upload_documents.py`:

```python
#!/usr/bin/env python
"""
Complete document upload script with error handling and progress tracking
"""

import requests
import json
import time
from pathlib import Path
from typing import Optional, Dict, List

class RAGDocumentUploader:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.upload_endpoint = f"{api_url}/api/v1/documents/upload"
        self.list_endpoint = f"{api_url}/api/v1/documents/list"
    
    def upload(
        self,
        file_path: str,
        department: Optional[str] = None,
        sensitivity: str = "internal",
        owner_email: Optional[str] = None
    ) -> Optional[Dict]:
        """Upload a single document"""
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return None
        
        print(f"📤 Uploading: {file_path.name} ({file_path.stat().st_size / 1024:.1f} KB)")
        
        try:
            with open(file_path, "rb") as f:
                data = {"sensitivity": sensitivity}
                if department:
                    data["department"] = department
                if owner_email:
                    data["owner_email"] = owner_email
                
                response = requests.post(
                    self.upload_endpoint,
                    files={"file": f},
                    data=data,
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"   ✅ Uploaded successfully!")
                    print(f"      ID: {result['document_id']}")
                    print(f"      Chunks: {result['chunks_created']}")
                    print(f"      Quality: {result['quality_score']:.0%}")
                    return result
                else:
                    print(f"   ❌ Server error: {result.get('errors')}")
                    return None
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text}")
                return None
        
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Cannot connect to {self.api_url}")
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def upload_batch(
        self,
        folder_path: str,
        department: Optional[str] = None
    ) -> List[Dict]:
        """Upload all documents from a folder"""
        
        folder = Path(folder_path)
        if not folder.is_dir():
            print(f"❌ Folder not found: {folder_path}")
            return []
        
        supported_formats = {".pdf", ".docx", ".txt", ".xlsx", ".xls"}
        files = [f for f in folder.iterdir() if f.suffix.lower() in supported_formats]
        
        if not files:
            print(f"❌ No supported documents found in {folder_path}")
            return []
        
        print(f"📚 Found {len(files)} documents to upload\n")
        
        results = []
        for i, file_path in enumerate(files, 1):
            print(f"[{i}/{len(files)}]", end=" ")
            result = self.upload(file_path, department=department)
            if result:
                results.append(result)
            time.sleep(0.5)  # Rate limiting
        
        return results
    
    def list_documents(self) -> Optional[List[Dict]]:
        """List all uploaded documents"""
        try:
            response = requests.get(self.list_endpoint)
            if response.status_code == 200:
                data = response.json()
                return data.get("documents", [])
        except Exception as e:
            print(f"❌ Error listing documents: {e}")
        return None
    
    def print_stats(self):
        """Print current system statistics"""
        try:
            response = requests.get(self.list_endpoint)
            if response.status_code == 200:
                data = response.json()
                print("\n" + "="*60)
                print("📊 SYSTEM STATISTICS")
                print("="*60)
                print(f"Total Documents: {data.get('total', 0)}")
                print(f"Total Chunks: {data.get('total_chunks', 'N/A')}")
                print(f"Total Embeddings: {data.get('total_embeddings', 'N/A')}")
                print("="*60 + "\n")
        except Exception as e:
            print(f"Error: {e}")

# Usage
if __name__ == "__main__":
    uploader = RAGDocumentUploader()
    
    # Upload single document
    uploader.upload(
        "financial_report.pdf",
        department="Finance",
        sensitivity="internal"
    )
    
    # Upload all documents from folder
    # uploader.upload_batch("path/to/documents", department="General")
    
    # List documents
    docs = uploader.list_documents()
    if docs:
        print(f"Total documents in system: {len(docs)}")
```

**Run it:**
```bash
python upload_documents.py
```

---

## 🎯 Summary

| Method | Best For | Complexity |
|--------|----------|-----------|
| **cURL** | Quick tests, one-off uploads | ⭐ Easy |
| **Python Script** | Automation, batch uploads | ⭐⭐ Medium |
| **API Direct** | Integrations with other systems | ⭐⭐⭐ Complex |

**Start with:** cURL for testing, Python for production automation.

Your RAG system is now ready to continuously grow with new documents! 🚀
