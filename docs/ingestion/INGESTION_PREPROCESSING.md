# Document Ingestion and Preprocessing

## Overview

The document ingestion and preprocessing pipeline is responsible for converting raw documents in various formats into structured, validated, and chunked text segments ready for embedding and retrieval. This is a critical component of the RAG system that ensures data quality and optimal search performance.

## Architecture

The preprocessing pipeline consists of three main components:

```
Raw Documents → Extraction → Validation → Chunking → Storage
                (extractor)  (processor)   (chunker)   (database)
```

### Components

1. **TextExtractor** (`extractor.py`) - Format-specific text extraction
2. **DocumentProcessor** (`processor.py`) - Orchestrates the full pipeline
3. **TextChunker** (`chunker.py`) - Splits text into meaningful chunks
4. **Database Models** - Persistent storage of documents and chunks

---

## Step 1: Text Extraction

### Supported Formats

The system supports extraction from multiple document formats:

| Format | Method | Handler |
|--------|--------|---------|
| PDF | `extract_pdf()` | pdfplumber + PyPDF2 |
| DOCX/DOC | `extract_docx()` | python-docx |
| TXT | `extract_txt()` | Native file I/O |
| XLSX/XLS | `extract_xlsx()` | openpyxl |

### PDF Extraction

**Process:**
- Uses `pdfplumber` as primary extractor (better formatting preservation)
- Falls back to `PyPDF2` if needed
- Extracts metadata (title, author, page count)
- Preserves page markers (`--- Page N ---`) for reference

**Output:**
```python
{
    "success": True,
    "text": "extracted text...",
    "metadata": {
        "total_pages": 45,
        "title": "Document Title",
        "author": "Author Name"
    },
    "format": "pdf"
}
```

### DOCX Extraction

**Process:**
- Extracts text from all paragraphs in order
- Extracts and formats table data with `|` separators
- Preserves document structure

**Output Includes:**
- Total paragraphs count
- Total tables count
- Formatted table rows

### TXT Extraction

**Process:**
- Reads plain text files with UTF-8 encoding
- Falls back to latin-1 encoding if UTF-8 fails
- Handles encoding errors gracefully

**Output Includes:**
- Line count
- Detected encoding (if fallback used)

### XLSX Extraction

**Process:**
- Iterates through all sheets in workbook
- Extracts cell values with sheet headers
- Formats rows with `|` separators

**Output Includes:**
- Sheet count
- Formatted sheet data with headers

**Example Output:**
```
=== Sheet: Employees ===
Name | Department | Salary
Jack Wilson | Sales | $85,000
Jane Smith | Engineering | $125,000
```

### File Validation

Each extracted file receives metadata:

```python
{
    "file_path": "/path/to/document.pdf",
    "file_name": "document.pdf",
    "file_size_bytes": 1024576
}
```

---

## Step 2: Duplicate Detection

Before processing, files are checked for duplicates using MD5 hashing:

```python
def calculate_md5(file_path: str) -> str:
    """Calculate MD5 hash of entire file"""
    # Processes file in 4KB chunks for memory efficiency
```

**Process:**
1. Calculate MD5 hash of incoming file
2. Query database for existing documents with same hash
3. Reject if duplicate found (prevents index bloat)

**Benefits:**
- Prevents processing identical documents multiple times
- Reduces storage and computational overhead
- Maintains data integrity

---

## Step 3: Text Quality Validation

Extracted text undergoes comprehensive quality assessment:

### Quality Metrics

```python
validate_text_quality(text, min_length=100) → Dict

Returns:
{
    "quality_score": 0.0-1.0,      # Overall quality rating
    "is_valid": True/False,         # Pass/fail (score > 0.5)
    "issues": [...],                # Specific problems found
    "text_length": int,             # Character count
    "line_count": int,              # Total lines
    "avg_line_length": float        # Average characters per line
}
```

### Quality Checks

| Check | Rule | Penalty |
|-------|------|---------|
| **Length** | Min 100 characters | -0.3 if too short |
| **Special Chars** | Max 50% ratio | -0.2 if exceeds |
| **Encoding** | <10 replacement chars | -0.3 if corrupted |
| **Line Length** | 5-1000 chars avg | -0.1 if unusual |

### Example Quality Check

```python
{
    "quality_score": 0.85,
    "is_valid": True,
    "issues": [],
    "text_length": 15420,
    "line_count": 156,
    "avg_line_length": 98.8
}
```

**Documents fail validation if:**
- Quality score ≤ 0.5
- Major encoding corruption detected
- Text too short to be meaningful
- Insufficient readable content

---

## Step 4: Text Chunking

Chunked text is split into manageable segments optimized for embedding and retrieval.

### Chunking Strategies

#### 1. Semantic Chunking (Default - Best Quality)

**Approach:**
- Splits at meaningful boundaries (paragraphs, headers)
- Respects semantic document structure
- Attempts to keep chunks near target size without breaking meaning

**Algorithm:**
1. Split text by paragraph breaks (`\n\n`)
2. For large paragraphs, split by sentence boundaries
3. Accumulate sentences until approaching target size
4. Save chunk and start new one

**Advantages:**
- Preserves context and meaning
- Better for heterogeneous documents
- Improves retrieval relevance

**Example:**
```
Original:
"Machine learning is a subset of AI. 
It uses algorithms to learn patterns. 
Deep learning goes deeper with neural networks."

Chunks:
[
  "Machine learning is a subset of AI. It uses algorithms to learn patterns.",
  "Deep learning goes deeper with neural networks."
]
```

#### 2. Sentence-Aware Chunking (Balanced)

**Approach:**
- Groups complete sentences to avoid broken context
- Good balance between quality and robustness
- Works well for unstructured text

**Algorithm:**
1. Split text into sentences using regex: `(?<=[.!?])\s+`
2. Accumulate sentences until target size reached
3. Move to next chunk and repeat

**Advantages:**
- Fewer fragmented concepts
- Works on most text types
- Relatively fast

#### 3. Fixed-Size Chunking (Simple but Crude)

**Approach:**
- Splits text into fixed character segments
- Uses overlap for context preservation
- Simplest implementation

**Configuration:**
```python
chunk_size = 512 (tokens, ~2KB chars)
chunk_overlap = 100 (tokens, ~400 chars overlap)
```

**Advantages:**
- Predictable output
- Fastest processing
- Good for homogeneous data

**Disadvantages:**
- May split mid-sentence
- Overlapping content redundancy
- Less context-aware

### Chunking Configuration

From `config/settings.py`:

```python
CHUNK_SIZE = 512              # Target tokens per chunk
CHUNK_OVERLAP = 100           # Token overlap between chunks
MIN_CHUNK_SIZE = 100          # Minimum characters per chunk
CHARS_PER_TOKEN_APPROX = 4    # Used for rough token estimation
```

**Conversion Reference:**
- 1 token ≈ 4 characters (rough estimate)
- 512 tokens ≈ 2,048 characters
- Configured via `TextChunker` initialization

### Token Counting

Approximate token counting (without tiktoken for speed):

```python
def count_tokens_approx(text: str) -> int:
    return max(1, len(text) // 4)  # Divide by 4 for estimate
```

**Note:** For production accuracy, integrate tiktoken:
```python
import tiktoken
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
tokens = len(encoding.encode(text))
```

### Chunk Metadata Calculation

Each chunk receives metadata for better retrieval:

```python
calculate_chunk_metadata(chunk_text, chunk_number) → Dict

Returns:
{
    "tokens_count": int,           # Approximate token count
    "section_title": str,          # First few words (section hint)
    "hierarchy_level": int,        # 0=body, 1=h1, 2=h2, 3=h3
    "importance_score": float      # 0.0-1.0 importance rating
}
```

**Hierarchy Detection:**
- Level 1: Text starting with `# ` (markdown H1)
- Level 2: Text starting with `## ` (markdown H2)
- Level 3: Text starting with `### ` (markdown H3)
- Level 0: Regular body text

---

## Step 5: Database Storage

Processed documents and chunks are stored in SQLAlchemy ORM models:

### Document Model

```python
class Document:
    id: str              # UUID primary key
    name: str            # Unique document name
    version: str         # Version string (e.g., "1.0")
    
    # Dates
    upload_date: DateTime
    effective_date: DateTime (optional)
    expires_date: DateTime (optional)
    last_modified: DateTime
    
    # Organization
    department: str (indexed)
    owner_email: str
    
    # Classification
    sensitivity: Enum["public", "internal", "confidential"]
    category: str (indexed)
    
    # File Info
    storage_path: str
    file_size_bytes: int
    hash_md5: str (unique, indexed)
    
    # Status
    status: Enum["active", "archived", "deprecated"]
    processing_status: Enum["pending", "indexed", "failed"]
    error_message: str (if failed)
    
    # Relations
    chunks: List[DocumentChunk]  # Cascade-deleted
    versions: List[DocumentVersion]
```

### DocumentChunk Model

```python
class DocumentChunk:
    id: str              # UUID primary key
    document_id: str     # FK to Document (indexed)
    
    # Content
    chunk_text: str      # The actual text segment
    chunk_number: int    # Order in document (1, 2, 3...)
    tokens_count: int    # Approximate token count
    
    # Metadata
    section_title: str   # Section/topic name
    hierarchy_level: int # 0-3, higher = deeper in structure
    importance_score: float (0.0-1.0)
    quality_score: float (0.0-1.0)
    
    context_before: str (optional)
    context_after: str (optional)
    
    language: str        # Default "en"
    
    # Embedding Status
    embedding_generated: bool
    embedding_timestamp: DateTime
    embedding_model: str
    
    backup_embedding_generated: bool
    backup_embedding_model: str
    
    # Relations
    document: Document
    embeddings: List[ChunkEmbedding]
```

---

## Full Processing Pipeline

### Step-by-Step Execution

The `DocumentProcessor.process_document()` method orchestrates the complete pipeline:

```python
DocumentProcessor.process_document(
    file_path: str,              # Path to document file
    document_name: str,          # Display name
    department: str = None,      # Optional department
    sensitivity: str = "internal",  # Classification level
    owner_email: str = None      # Optional owner
) → Dict[success, document_id, chunks_created, errors]
```

### Detailed Flow

1. **Duplicate Check**
   - Calculate MD5 hash of incoming file
   - Query database for existing documents
   - Return error if duplicate found

2. **Text Extraction**
   - Detect file format from extension
   - Call appropriate extractor method
   - Return extracted text + metadata

3. **Quality Validation**
   - Run comprehensive quality checks
   - Return error if quality score ≤ 0.5
   - Calculate quality metrics for later retrieval

4. **Document Record Creation**
   - Create `Document` record in database
   - Store metadata (dept, owner, sensitivity)
   - Store file hash and path
   - Set `processing_status = "indexed"`

5. **Text Chunking**
   - Apply semantic chunking strategy
   - Generate chunks respecting boundaries
   - Filter by minimum size (100 chars)
   - Verify chunks created successfully

6. **Chunk Records Creation**
   - For each chunk, create `DocumentChunk` record
   - Calculate chunk-specific metadata
   - Set `embedding_generated = False`
   - Store quality and hierarchy info

7. **Database Commit**
   - Commit all records in transaction
   - Return success status
   - Report chunks created

### Result Structure

```python
{
    "success": True,
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "document_name": "Company_Policy_2024.pdf",
    "chunks_created": 45,
    "extraction_metadata": {
        "total_pages": 12,
        "title": "Company Policy",
        "author": ""
    },
    "quality_score": 0.92,
    "errors": []
}
```

### Error Handling

Each step can fail gracefully:

```python
{
    "success": False,
    "document_id": None,
    "document_name": "invalid.pdf",
    "chunks_created": 0,
    "errors": [
        "Duplicate document found: existing_doc.pdf (ID: xxx)",
        "Extraction failed: PDF is corrupted",
        "Text quality too low: corruption detected",
        "No valid chunks created from text"
    ]
}
```

**Errors are accumulated** - multiple issues are all reported, allowing for detailed troubleshooting.

---

## Additional Features

### Chunk Retrieval

Get all chunks for a processed document:

```python
processor.get_document_chunks(document_id) → List[DocumentChunk]
```

Returns chunks ordered by `chunk_number` (1, 2, 3...).

### Document Deletion

Remove document and cascade-delete all chunks:

```python
processor.delete_document(document_id) → bool
```

**Features:**
- Cascade deletion removes all related chunks
- Removes embeddings (related via FK)
- Handles cascade cleanly

### Document Versioning

The system tracks document versions for rollback:

```python
class DocumentVersion:
    document_id: str
    version: str              # "1.0", "1.1", "2.0", etc.
    chunks_count: int
    embeddings_count: int
    file_hash: str
    storage_path: str
    status: Enum["active", "archived", "deprecated"]
    rollback_available: bool
    notes: str (optional)
```

---

## Integration Points

### Downstream Components

After preprocessing, chunks flow to:

1. **Embedding Pipeline** (`src/embedding/`)
   - Chunks marked `embedding_generated = False`
   - Ready for embedding generation
   - Creates `ChunkEmbedding` records

2. **Vector Database** (`src/vector_db/`)
   - Stores embeddings in FAISS index
   - Enables semantic search

3. **Query Pipeline** (`src/query_pipeline/`)
   - Retrieves relevant chunks based on queries
   - Uses chunk metadata for ranking

### Configuration

From `config/settings.py`:

```python
CHUNK_SIZE = 512                    # Target tokens
CHUNK_OVERLAP = 100                 # Token overlap
MIN_CHUNK_SIZE = 100                # Minimum characters
SUPPORTED_FILE_TYPES = [
    "pdf", "docx", "doc", "txt", "xlsx", "xls"
]
```

---

## Best Practices

### For Document Upload

1. **Validate file format** - Ensure it's in supported list
2. **Provide metadata** - Department, owner, sensitivity level
3. **Use meaningful names** - Names must be unique
4. **Check quality** - Monitor quality scores in results

### For Chunk Configuration

1. **Adjust chunk size** by document type:
   - Technical docs: 512 tokens (more detail)
   - Legal docs: 512-768 tokens (complex sentences)
   - News articles: 256 tokens (short, punchy)

2. **Control overlap** based on use case:
   - High overlap (100-150 tokens): Important context preservation
   - Low overlap (25-50 tokens): Performance priority

### For Quality Assurance

1. Monitor quality scores - aim for > 0.8
2. Review error messages for pattern issues
3. Test extraction with sample documents first
4. Consider format-specific preprocessing (e.g., OCR for scanned PDFs)

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| PDF extraction (10 pages) | ~1-2s | Depends on image-heavy content |
| DOCX extraction (20KB) | ~0.2s | Generally fast |
| TXT extraction (500KB) | ~0.1s | Very fast |
| Quality validation | ~0.05s | Per document |
| Semantic chunking | ~0.5s | Per 50KB text |
| Database commit | ~0.2s | Per 50 chunks |

**Total for typical 2MB PDF:** ~3-5 seconds

---

## Troubleshooting

### "Duplicate document found"
- File was already processed
- Check database for existing document
- Delete old version if needed (cascade removes chunks)

### "Extraction failed"
- File format unsupported
- File corrupted or invalid
- Check logs for specific error

### "Text quality too low"
- Document has encoding issues
- Too many special characters
- Maybe corrupted or binary

### "No valid chunks created"
- Text too short after extraction
- All chunks fell below minimum size
- Document may be corrupted

### Empty quality_score or errors
- Transaction rolled back
- Check database connection
- Verify write permissions

---

## Summary

The ingestion and preprocessing pipeline:

✅ Extracts text from 6+ document formats  
✅ Detects and prevents duplicate processing  
✅ Validates text quality comprehensively  
✅ Chunks text intelligently with configurable strategies  
✅ Stores rich metadata for retrieval optimization  
✅ Provides detailed error reporting  
✅ Handles edge cases gracefully  
✅ Supports document versioning and rollback  

This foundation ensures that all data flowing into the embedding and retrieval pipeline is of high quality and properly structured for optimal RAG performance.
