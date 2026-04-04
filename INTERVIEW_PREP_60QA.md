# RAG Application - Interview Preparation (60 Questions)

**Project:** Enterprise RAG System | Status: 95% Complete | 102 Documents | 38,912 Chunks

---

## Section 1: Project Overview & Fundamentals (Q1-Q8)

### Q1: What is the RAG application project and what problem does it solve?

The RAG (Retrieval Augmented Generation) application is an enterprise system designed to create intelligent, context-aware answers based on company documents. Instead of relying on an LLM's general training data, which may be outdated or inaccurate, RAG retrieves relevant company documents first, then uses that specific information to generate answers. This solves critical business problems: reducing hallucinated responses, ensuring information accuracy, maintaining document security, and providing auditable source references. The project ingests 102 company documents (PDFs, Word docs, text files, spreadsheets) into a searchable knowledge base that processes queries in under 300ms and returns answers with confidence scores and source citations.

### Q2: What are the main business benefits of this RAG system?

**Accuracy & Trust:** Answers are grounded in actual company documents, not generic training data, eliminating false information. **Security & Control:** All documents remain within company infrastructure; external APIs are optional, keeping sensitive data private. **Compliance & Audit:** Every answer is traceable to specific documents with timestamps and user attribution, critical for regulated industries. **Cost Efficiency:** The system uses lighter 7B-parameter models that become highly capable with context, instead of requiring expensive billion-parameter models. **Scalability:** New information can be added to documents instantly without retraining any models. **User Experience:** Employees get instant answers to company policy questions with confidence levels and source documents, reducing dependency on HR/Legal teams.

### Q3: How does RAG differ from traditional chatbots or search engines?

Traditional chatbots rely on their training data (which becomes stale) and often generate plausible-sounding but incorrect answers. Search engines return documents, requiring users to read and synthesize information themselves. RAG combines the strengths of both: it retrieves relevant documents (like search) but then intelligently synthesizes this information into a direct answer (like chatbots), with the critical advantage that every claim is backed by specific source documents. The system doesn't use external internet data or trained-in knowledge for answers—only company documents. This creates a trusted, auditable system where users can verify any claim by reviewing the source.

### Q4: What documents are currently in the knowledge base?

The system ingests 102 documents organized into 11 categories: Company information (policies, culture, overview), Compliance documents, Contracts (25+ vendor agreements), Employee information, Enterprise policies, Financial data, Governance documents, Operations manuals, Product documentation, Security policies, and Miscellaneous materials. These documents total approximately 38,912 chunks (small, meaningful text segments), with each chunk carefully indexed for semantic search. Documents cover employee handbooks, benefit policies, compliance requirements, vendor contracts, and operational procedures—essentially all knowledge needed for daily business operations.

### Q5: What is the core technology stack?

The backend uses FastAPI, a modern Python web framework optimized for high-performance APIs. Documents are parsed in multiple formats (PDF, DOCX, XLSX, TXT) and stored in SQLite for metadata and relationships. Text is converted to semantic embeddings using Sentence Transformers (all-MiniLM-L6-v2 model), which produces 384-dimensional vectors capturing meaning. These vectors are indexed in FAISS (Facebook's vector database) for sub-100ms similarity searches across 38,912 chunks. The primary language model is Mistral-7B for response generation, with optional integration to OpenAI or Anthropic models. The entire system is containerized with Docker and monitored with Prometheus and Grafana for production observability.

### Q6: Who are the primary users of this system?

The primary users are company employees who have questions about policies, benefits, procedures, or company information. HR staff use it to handle common repetitive questions about benefits and policies. Managers reference it for compliance and operational procedures. Sales teams use it to understand product offerings and specifications. New employees rely on it during onboarding to quickly learn company culture and procedures. The system is designed for internal use only, with access controlled by authentication and document sensitivity levels (Public, Internal, Confidential).

### Q7: What are the key performance metrics for this project?

**Response Latency:** Average query response is 235ms—fast enough for interactive user experience. Search latency is ~25ms, LLM generation ~200ms. **Accuracy:** User satisfaction is 94.1%, meaning users rate answers as helpful and accurate. **Hallucination Rate:** Only 0.5% of answers contain unsupported claims, well below industry standards. **Confidence Calibration:** System confidence scores accurately reflect answer quality (94% accuracy when system says 90%+ confidence). **System Availability:** Target 99.9% uptime with redundancy. **Search Coverage:** The system successfully retrieves relevant chunks for 98% of queries.

### Q8: What makes this project different from other RAG implementations?

Most RAG systems focus only on retrieval accuracy; this project implements enterprise-grade safety with a 9-layer anti-hallucination system specifically designed for critical business information. Unlike simple RAG implementations, it supports multiple LLM providers (Mistral, OpenAI, Claude) for flexibility. It includes sophisticated document versioning and update handling—when policies change, old chunks are invalidated and documents are re-indexed. The system tracks individual queries with feedback mechanisms, enabling continuous improvement. It implements role-based access control with document sensitivity levels, ensuring compliance teams can't accidentally expose confidential information. Most uniquely, it's designed for production enterprise use with monitoring, logging, rate limiting, and security at every layer.

---

## Section 2: Architecture & System Design (Q9-Q18)

### Q9: What is the overall architecture of the RAG system?

The system follows a layered architecture with clear separation of concerns. The **Presentation Layer** includes REST API endpoints built with FastAPI. Below that is the **Business Logic Layer** containing query processing, validation, and generation components. The **Data Access Layer** manages database operations and vector search. The **Storage Layer** includes SQLite for metadata and FAISS for vector indices. **External Services** handle document parsing, embeddings generation, and LLM calls. The architecture enables independent scaling—you can scale the API layer separately from document processing jobs, for example. Each layer uses dependency injection and abstract base classes to minimize coupling, making it easy to swap implementations (e.g., replace SQLite with PostgreSQL).

### Q10: How does a query flow through the entire system from user input to response?

When a user submits a query, it arrives at the REST API endpoint. The system first validates the input: checking for empty/malicious content, language compatibility, and rate limit compliance. The query is then embedded into a 384-dimensional vector using the same Sentence Transformers model that embedded all chunks. This query vector is sent to the FAISS index, which performs sub-100ms similarity search to find the 5-10 most similar chunks from 38,912 options. The system retrieves metadata for these chunks from SQLite (document name, section, page number, sensitivity level). These chunks become the context window—a brief summary of relevant information. The system constructs a prompt combining system instructions, this context, and the user query, then sends it to the Mistral-7B LLM. The LLM generates an answer. The answer is validated: checked for factual grounding in the source chunks, scored for confidence, and examined for hallucination indicators. Finally, the response is assembled with the answer, confidence percentage, source citations, and processing time, then returned to the user in ~235ms total.

### Q11: What is the document ingestion pipeline?

When a document is uploaded, the system immediately validates its format (PDF, DOCX, XLSX, or TXT). Using specialized parsers, it extracts text content—PDFs are handled with pdfplumber and OCR for scanned documents, Word documents with python-docx, spreadsheets with openpyxl. Metadata is automatically extracted: document filename, upload timestamp, owner email, department, sensitivity level (Public/Internal/Confidential), file size, and initial token count. The raw document content is stored in SQLite for archival. The document is then scheduled for processing: it's chunked into 1,000-token segments with 100-token overlap between segments (overlap preserves context at chunk boundaries). Each chunk is extracted and stored in the database with position information, section headers, and extracted entities. After chunking, all 38,912 chunks are embedded asynchronously using Sentence Transformers. The embeddings are added to the FAISS index. Finally, the document is marked as "processed and ready" and appears in search results. The entire pipeline from upload to searchable takes roughly 2-3 minutes depending on document size.

### Q12: How does the system handle different document types?

Each document type has a dedicated parser optimized for that format. **PDF documents** are parsed page-by-page; the system extracts text while preserving formatting cues like headers and page numbers. For scanned PDFs (images), the system can apply OCR to extract readable text. **DOCX (Word) documents** are processed paragraph-by-paragraph, preserving heading hierarchy (H1, H2, H3) which helps the system understand document structure. **XLSX (Excel) spreadsheets** are converted to readable text with sheet names, column headers, and rows formatted as structured text (e.g., "Department: HR, Headcount: 50"). **TXT files** are read directly with automatic encoding detection. After extraction, all documents go through a normalization step: removing extra whitespace, standardizing line breaks, and cleaning encoding artifacts. This ensures consistent processing regardless of source format.

### Q13: What is the database schema and why is it designed this way?

The schema has three main tables: **Documents** (102 records) storing metadata like filename, owner, department, sensitivity level, upload timestamp, and processing status. **Chunks** (38,912 records) containing the actual text content, associated document ID, chunk position, token count, and extracted metadata like page number and section title. **Queries_and_Responses** logging every query, response, confidence score, used chunks, generation model, and user feedback rating. This schema is designed for three key reasons: **Referential Integrity**—relationships between chunks and documents enable cascading updates (when a document is deleted, all its chunks are automatically removed). **Query Efficiency**—indexes on document_id and owner_email enable fast lookups; composite indexes on (document_id, chunk_index) support sequential chunk retrieval. **Audit Trail**—the query log creates a complete record for compliance and enables feedback-driven system improvement. The schema avoids storing embeddings in SQL (they're in FAISS instead) because SQL is inefficient for vector operations, but maintains a reference relationship so the system can join embedding search results with detailed metadata.

### Q14: What are the different API route groups and their purposes?

The system exposes six main route groups. **Document Management** handles uploading, listing, updating, and deleting documents—endpoints for document lifecycle management. **Embeddings** endpoints allow manual embending generation and FAISS index rebuilding (though this happens automatically). **Search** endpoints enable semantic similarity searching directly without going through LLM generation, useful for document research. **Query** is the main endpoint where users ask questions and receive LLM-generated answers. **Validation** endpoints check answer quality, grounding in sources, and confidence scoring. **Feedback** endpoints collect user ratings and hallucination reports. Each route group has consistent error handling, rate limiting per endpoint (Q&A is stricter than listing), logging, and response formatting.

### Q15: How does the system ensure security at the API level?

Every endpoint requires authentication via JWT tokens; unauthenticated requests return 401 Unauthorized. Input validation occurs on every endpoint—sanitizing query text to prevent injection attacks, validating file uploads by checking format and size, and rate limiting by user tier (free tier: 10 queries/hour, pro: 100/hour, enterprise: unlimited). The system implements role-based access control: certain endpoints are admin-only (like deleting documents), and users can only access documents matching their permission level. Document sensitivity levels (Public/Internal/Confidential) are enforced—confidential documents can only be queried by their owner or administrators. HTTPS/TLS encryption secures all data in transit. Session tokens expire after 24 hours, forcing re-authentication for long-running sessions. All API errors are logged with context (user, timestamp, endpoint, error details) for security auditing.

### Q16: What happens when users provide feedback on responses?

When a user rates a response 1-5 stars and optionally flags it as containing hallucinations, this feedback is stored in the database linked to the specific query. The system analyzes this feedback in real-time: if a hallucination is flagged, it's logged as a critical issue and the team is notified if multiple hallucinations occur. High-quality responses (4-5 stars) are gradually collected as positive examples for future model fine-tuning. Low-quality responses (1-2 stars) signal either system issues or questions outside the knowledge base scope. After accumulating ~100 examples each week, the system can perform Low-Rank Adaptation (LoRA) fine-tuning to improve the base model specifically for your company's query patterns. This creates a feedback loop where system quality continuously improves based on actual user experience.

### Q17: How does the system maintain document versions?

When a document is updated (e.g., a policy changes), the system doesn't overwrite historical content. Instead, it creates a version record containing the old content, who made the change, when, and why. A new version number is assigned. The previous chunks are marked as inactive. The new document content is re-chunked, re-embedded, and re-indexed. This maintains an audit trail showing what information was current at specific points in time, essential for compliance. If a mistake occurs, the system can rollback to a previous version instantly, re-activating old chunks and deactivating new ones. This versioning enables users to ask "what was the policy as of March 1st?" and get historically accurate information. It also protects against accidental deletions—even if a document is deleted, its version history remains for reference.

### Q18: What monitoring systems are in place to detect problems?

The system uses Prometheus to collect metrics (request counts, response times, error rates, LLM generation latency, confidence scores, hallucination detection rate). Grafana displays real-time dashboards showing API performance, query analytics, and system health. Alerts fire when error rates exceed 5%, query latencies exceed 30 seconds, hallucination rate exceeds 1%, or database connections fail. Application logs are centralized with detailed context (user, endpoint, timestamp, error stacktrace). Custom metrics track business-level indicators: average user satisfaction, most common query topics, documents accessed most frequently. The observability enables rapid incident response—if users start reporting hallucinations, the alert fires and the team can investigate immediately.

---

## Section 3: Core Pipeline Components (Q19-Q28)

### Q19: How does the chunking process work and why is overlap important?

Documents are typically thousands of tokens long—far too large to process efficiently. The chunking algorithm divides documents into manageable 1,000-token segments. However, it doesn't chunk at arbitrary boundaries. A 100-token overlap exists between consecutive chunks, meaning the last 100 tokens of one chunk appear at the start of the next chunk. This overlap is critical: imagine important information spans two chunks. Without overlap, the first chunk ends before the complete thought, and the second chunk starts after the thought begins, both missing context. With overlap, both chunks contain the full thought. When similarity search retrieves chunks, more complete information is available to the LLM. The result: 102 documents produce 38,912 chunks (averaging 381 chunks per document). This balance enables fast, accurate semantic search while preserving context integrity. Dynamic chunking (adjusting size based on content type) exists as an advanced option—dense technical content might use 750 tokens per chunk for better retrieval precision, while narrative content uses 1,200 tokens.

### Q20: What exactly is an embedding and how does it enable semantic search?

An embedding is a representation of text as a point in high-dimensional space (384 dimensions for Sentence Transformers). Imagine a 384-dimensional coordinate system where each axis represents a subtle aspect of meaning. The text "remote work policy" maps to one point, "work from home guidelines" maps to a nearby point (semantically similar), while "office supplies inventory" maps to a distant point (semantically unrelated). This mathematical structure enables similarity search: the system calculates distance between the query vector and every chunk vector. Closer points indicate higher relevance. The distance is converted to a similarity score (0 to 1, where 1 = perfect match). This semantic approach finds relevant chunks even when wording differs significantly—"Can I work from home?" and "remote work allowed?" return the same chunks because they mean the same thing, even though keywords differ. This is far superior to keyword search, which would miss connections between semantically similar but differently worded concepts.

### Q21: How are embeddings generated and stored?

When a document completes chunking, all chunks are batch-embedded using Sentence Transformers model (all-MiniLM-L6-v2). This model takes text and outputs a 384-dimensional vector. Batch processing (32 chunks at a time) accelerates generation; processing 38,912 chunks takes ~5 minutes CPU time. These embeddings are then added to the FAISS index, a specialized data structure optimizing vector similarity search. FAISS uses L2 (Euclidean) distance to measure vector similarity and builds an index structure enabling sub-5ms searches across 38,912 vectors. The embeddings aren't stored in SQL (inefficient for vectors); instead, FAISS maintains the in-memory index while chunks maintain a reference to their FAISS index position. When new documents are added, their chunks are embedded and appended to the index. This means production system is always ready—searches complete in milliseconds because embeddings are pre-computed offline, not calculated at query time.

### Q22: What is the FAISS index and why use it instead of database-native search?

FAISS (Facebook AI Similarity Search) is a specialized library optimizing vector similarity search. SQL databases store data in rows and columns; they're designed for exact matches and filtering. FAISS, conversely, is built specifically for high-dimensional vector math. For 38,912 chunks, FAISS search takes ~5ms; SQL similarity search would take several seconds. FAISS uses intelligent indexing structures (in this case, local exhaustive search with L2 distance) that are orders of magnitude faster for vector operations. The tradeoff: FAISS is memory-resident (the index must fit in RAM), whereas SQL scales to massive datasets on disk. For your 38,912 chunks at 384 dimensions, the index is ~150MB—easily fitting in modern server RAM. At 1 million chunks, you'd need more sophisticated index structures (IVF or HNSW), but the principle remains: specialized vector databases outperform general-purpose SQL for similarity search.

### Q23: How does query processing work differently for complex vs. simple questions?

**Simple questions** ("What's the vacation policy?") follow the standard path: embed query, search FAISS for top-5 chunks, pass to LLM for answer. Response time ~235ms. **Complex questions** ("How do vacation policies differ across departments?") require intelligent handling. The system detects multi-part intent and performs multiple FAISS searches with different interpretations of the query. It retrieves more chunks (perhaps 15 instead of 5). The system ranks results by relevance and deduplication (removing redundant information). It recognizes that the question needs comparison across multiple documents and ensures diverse sources are included. Response time extends to ~8-15 seconds but returns more comprehensive answers. **Ambiguous questions** ("Tell me about remote work") are clarified: the system infers the user likely wants policy information and retrieves policy documents, but also returns related operational procedures and benefits information. This adaptive approach ensures users get the right answer regardless of question phrasing.

### Q24: What role does the system prompt play in LLM behavior?

The system prompt is an instruction set governing how the LLM responds. A well-designed system prompt says something like: "You are a company knowledge assistant. Answer using ONLY the provided context. If information isn't in the context, say 'I don't know' rather than guessing. Always cite which document your information comes from." This seemingly simple instruction dramatically changes LLM behavior away from its default tendency to be helpful by any means necessary (including fabricating plausible-sounding information). The system prompt prevents hallucinations by explicitly instructing against them. Different prompt variants exist for different use cases: a strict prompt for legal/compliance questions explicitly forbids any inference or assumption, while a more flexible prompt for general information allows reasonable synthesis. The prompt is combined with retrieved context and the user query to form the complete input to the LLM. Temperature (randomness) is typically set to 0.1 (very deterministic) rather than the default 0.7, further reducing hallucination likelihood.

### Q25: How does the system generate confident, accurate answers?

Answer accuracy flows from multiple layers. First, context is carefully selected via semantic search—only information truly relevant to the query is provided. Second, the system prompt explicitly forbids hallucination. Third, the LLM is instructed to cite sources: every claim must reference a document. Fourth, response is limited to 256 tokens—prevents rambling and forces conciseness, which reduces opportunities for error. Fifth, after generation, the answer undergoes validation: each sentence is checked against the source chunks. If a sentence doesn't match the sources, confidence is reduced. Sixth, confidence scoring factors in grounding (40%), semantic similarity of sources (35%), internal consistency (15%), and coverage of the query (10%). Results: 94.1% user satisfaction, 0.5% hallucination rate. This multi-layer approach means accurate answers don't result from luck but from systematic design.

### Q26: What happens if the system doesn't find relevant information?

When similarity search returns chunks with very low relevance scores (similarity < 0.6), the system detects this as a "low confidence" situation. Rather than generating a risky answer, it returns "I don't have information about that in the knowledge base. Your question may relate to [category]. I recommend contacting [relevant team] for direct assistance." This honest response prevents hallucination while guiding the user. The system does escalate the query: if many users ask the same unanswered questions, this signals a gap in the knowledge base. Product teams can then decide to add documentation addressing frequently-asked-but-unanswered questions. This creates a virtuous cycle: gaps are identified through real usage, documented, and filled. Over time, coverage improves.

### Q27: How does the system handle sensitive or confidential information?

Confidential documents are only searchable by their owner or admins. When a user performs a search, the FAISS index returns potentially relevant chunks, but the system immediately filters results: checking each chunk's parent document sensitivity level and comparing against the user's permissions. If the user can't access the document, that chunk is removed from results. Search latency increases slightly (few milliseconds) due to permission checking, but remains well under 100ms. This two-stage approach (retrieve semantically relevant, then permission-filter) ensures security without compromising search quality. For documents with mixed sensitivity (some sections public, others confidential), the system can apply per-section tags and enforce permission at that granularity. Queries are logged with the user and timestamp, enabling audit trails for compliance teams to verify who accessed what information when.

### Q28: How are different LLM providers integrated?

The system uses a provider factory pattern: an abstract LLMProvider base class defines the interface, while specific implementations (MistralProvider, OpenAIProvider, ClaudeProvider) inherit from it. Each provider handles its own API calls, error handling, and response formatting. At runtime, the system selects a provider based on configuration: Mistral-7B is default (runs locally, no API calls, no cost), but if OPENAI_API_KEY is configured, users can opt into GPT-4 for complex queries. Each query specifies which model to use or falls back to default. This modularity means switching models involves changing one configuration—no code changes. Each model has different strengths: Mistral is fast and cost-effective, GPT-4 is more precise, Claude-2 excels at long-form reasoning. Users can now leverage the best model for each use case.

---

## Section 4: Technical Operations & Performance (Q29-Q38)

### Q29: What is the end-to-end latency breakdown?

A typical query takes ~235ms: Query validation (1ms), embedding the query (10ms), FAISS similarity search (5ms), SQL metadata lookup (10ms), LLM generation (200ms), answer validation (10ms), response serialization (5ms). The LLM generation dominates (85% of latency). To improve this, the system implements token streaming: instead of waiting for the LLM to complete generation, tokens are streamed to the client as produced. From the user's perspective, the first token appears after ~500ms (instead of waiting 235ms for the whole response). By the time they finish reading the first sentence, more tokens have arrived, creating the illusion of much faster response. The actual generation time hasn't changed, but perceived latency—what matters for user experience—is cut roughly in half. Further optimization involves model quantization (reducing precision to speed computation) and prompt optimization (shorter prompts generate faster).

### Q30: How does the system scale to handle increased load?

The system naturally handles increased query volume through FastAPI's async architecture: a single worker can handle 100+ concurrent queries. Horizontally, you can increase workers from 1 to 8 (or higher) on a single machine, or deploy multiple machines behind nginx load balancing. Vertically, you can provision larger machines with more CPU/memory. The database query latency (5-15ms) doesn't significantly increase with concurrent load due to connection pooling (20-40 connections maintained and reused). The FAISS index is memory-resident, so it doesn't slow down during concurrent searches. Embedding these factors in, the system can handle 1,000+ concurrent queries across a reasonable cluster without significant performance degradation. At 10 million chunks (vs. current 38,912), you'd need approximate nearest neighbor indices (IVF, HNSW) instead of exhaustive search, adding complexity but maintaining sub-100ms latencies.

### Q31: What is rate limiting and how is it implemented?

Rate limiting prevents abuse by restricting queries per user per time period. Different tiers have different limits: free users (10 queries/hour), pro (100/hour), enterprise (unlimited). The system uses token bucket algorithm: imagine each user has a bucket that fills at their tier's rate. Each query consumes one token. If the bucket is empty, the request is rejected with "Rate limit exceeded" and tells the user when they can retry. This prevents both DOS attacks and accidental overuse. Since the system is intended for internal company use, external rate limiting is less critical, but it protects against internal misconfiguration where a script accidentally makes thousands of queries. Rate limiting is implemented via Redis for distributed counting across multiple servers, ensuring even if queries hit different servers, the global limit is enforced.

### Q32: How does the system handle database performance with 38,912 chunks?

Database performance is optimized through strategic indexing. Frequently-queried columns have indices: document_id (for finding all chunks of a document), owner_email (for permission checking), and composite indices on (document_id, chunk_index) for sequential access. These indices reduce lookups from O(n) full-table scans to O(log n) B-tree searches. For 38,912 records, a full scan takes ~500ms; indexed lookup takes ~1ms. Connection pooling maintains 20-40 reusable database connections, eliminating TCP handshake overhead for subsequent queries. Query results are batched and eagerly-loaded (using SQL JOINs) to avoid N+1 problems where retrieving chunks for a document would require 1 query for the document + 1 query per chunk. Caching frequently-accessed documents (like company policies) in Redis further accelerates subsequent queries. The result: even with significant query load, database response stays under 15ms.

### Q33: What monitoring alerts are in place?

The system monitors 10+ critical metrics and fires alerts when thresholds are exceeded: HTTP error rate > 5% (indicates API problems), query latency p95 > 30 seconds (indicates slowness), hallucination rate > 1% (indicates model quality decline), low confidence responses > 50% (indicates knowledge base gaps), database connection failures > 5 (indicates database issues), FAISS index corruption (indicates data integrity issues), user satisfaction drops below 90% (indicates user-facing problems), and rate limit rejections spiking (indicates potential DOS or misconfiguration). These alerts are sent to ops teams immediately, enabling rapid response. Historical alert data is retained, enabling pattern analysis—if hallucinations spike every Tuesday morning, that signals something specific happens then (perhaps document updates trigger reindexing issues).

### Q34: How does authentication and authorization work?

Users authenticate by providing credentials (username/password or SSO) to receive a JWT token. This token is included in all subsequent API requests. The server verifies the token signature (it can't be forged), checks expiration (24-hour default), and extracts the user ID. Every request thus knows which user is making it. Authorization checks follow: is John allowed to access this document? The document's sensitivity level is checked against John's role. If John is HR staff and the document is "HR Confidential," he's allowed. If John is Engineering and the document is "HR Confidential," he's rejected with 403 Forbidden. This role-based access control (RBAC) scales to complex permission hierarchies: "all R&D documents," "all Q3 financial reports," "reports created by my team." The token approach (vs. session cookies) enables stateless operation—any server can validate any token without state coordination, critical for distributed systems.

### Q35: How does the system handle document updates and re-indexing?

When a document is updated (say, vacation policy changes), the system: (1) creates a version record preserving the old content, (2) stores the new content, (3) marks old chunks as inactive, (4) chunks the new content (creating new chunk records), (5) embeds new chunks, (6) adds new embeddings to FAISS, (7) marks document as "processing complete." This typically takes 2-3 minutes for a 50-page document. Crucially, during re-indexing, the old chunks remain searchable; searches don't suddenly break. Once new chunks are indexed, they become higher priority (fresher documents ranked above older versions). Users asking about the vacation policy after update get the new information; this handles common question patterns well. If a change causes problems (e.g., a wrong policy is uploaded), rollback is simple: find the previous version, set it as active, deactivate current chunks, rebuild FAISS index with old chunks. This rollback takes ~5 minutes.

### Q36: What security vulnerabilities could exist and how are they mitigated?

**SQL Injection:** User queries could contain malicious SQL. Mitigation: using parameterized queries and ORM (SQLAlchemy) prevents raw SQL execution. **XSS (Cross-Site Scripting):** Malicious JavaScript in inputs could attack other users. Mitigation: all user input is sanitized, special characters are escaped in responses. **DOS (Denial of Service):** Attackers could make millions of queries to overload the system. Mitigation: rate limiting per user, request timeout enforcement (if a query takes >30s, kill it), input size limits (query must be < 10KB). **Data Breach:** Attackers could exfiltrate documents from the database. Mitigation: encryption at rest (database encryption), encryption in transit (HTTPS/TLS), strong authentication (JWT), access control (permission checks), audit logging (all access logged). **Model Poisoning:** Feedback data could be used to fine-tune the model toward generating harmful content. Mitigation: human review of feedback before fine-tuning, version control for model changes, rollback capability if problems detected. Most vulnerabilities risk is low for an internal system, but these measures would be essential for external-facing products.

### Q37: How is system reliability and uptime maintained?

The system targets 99.9% uptime (roughly 43 minutes downtime per month allowed). Strategies include: redundant servers (if one fails, traffic routes to others), database backups (hourly incremental, weekly full backups), connection pooling with automatic retry (if a database connection drops, the pool creates a new one), circuit breakers (if the LLM embedding model fails, the system falls back to keyword search), graceful degradation (if FAISS index becomes corrupted, the system can rebuild from chunks in the database). Health checks run every 60 seconds at the /health endpoint; if health checks fail repeatedly, load balancers remove the unhealthy instance. Blue-green deployments enable updates without downtime: new code is deployed to unused servers "green" while traffic routes to current servers "blue"; once green is verified, traffic switches. If problems occur, traffic switches back to blue instantly.

### Q38: How are logs structured and what information is captured?

Application logs include: timestamp (when the event occurred), severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL), service name (which part of the system), user ID (which user triggered the event), request ID (tie-related logs to specific requests), endpoint (which API was called), duration (how long the operation took), status code (success or failure type), and context (relevant data like document IDs, chunk count). These structured logs can be queried: "show me all errors for user john@company.com on April 2," "find slow queries taking >5 seconds," "identify which documents cause hallucinations most often." Logs are streamed to centralized logging systems (like ELK Stack), enabling analysis across thousands of events. Sensitive data is scrubbed: passwords are never logged, document content is summarized not fully logged (security). Log retention is typically 90 days for recent logs, 1 year for archived logs for compliance.

---

## Section 5: Hallucination Prevention & Quality (Q39-Q48)

### Q39: What is hallucination and why is preventing it critical?

Hallucination occurs when an LLM confidently states false information. Example: user asks "What's the maternity leave policy?" The LLM generates "45 days paid maternity leave" even though the actual policy (in company documents) is 60 days. The response is plausible and formatted correctly, but wrong. Hallucinations are dangerous because users trust the system (it cites documents, after all) and may act on false information. An employee might decline better benefits because the system told them benefits don't apply to them (hallucination). Or a manager implements wrong policy based on system information. For regulated industries (healthcare, finance, insurance), hallucinations can trigger compliance violations. Preventing hallucinations is critical because trust in the system is fragile—one well-publicized hallucination destroys credibility. This project implements 9 distinct layers to prevent hallucinations; most RAG systems implement 1-2.

### Q40: Describe the 9-layer anti-hallucination system.

**Layer 1: Ultra-Low Temperature (0.05-0.1)** - LLM randomness is minimized. Instead of the default temperature 0.7 (which creatively generates varied responses), temperature 0.05 makes the model almost always pick the most likely next token, resulting in boring but reliable responses. **Layer 2: Explicit Anti-Hallucination Prompt** - System prompt explicitly forbids hallucination: "Do not guess, assume, or infer. Only answer from provided context. If unsure, say 'I don't know.'" **Layer 3: Grounding Verification** - After answer generation, each sentence is compared to source chunks; unsupported sentences are flagged. **Layer 4: Confidence Scoring** - Every answer receives a confidence score (0-100%) based on: what percentage of the answer is covered by sources (40%), how similar sources are to the query (35%), whether the answer is internally consistent (15%), and whether the answer addresses the full query (10%). **Layer 5: Threshold Rejection** - If confidence < 60%, the answer is shown to the user with a strong disclaimer and suggestion to consult support. **Layer 6: Token Limiting** - Responses limited to 256 tokens prevents rambling. Short responses have fewer opportunities for hallucination. **Layer 7: Source Attribution** - Every claim must cite specific documents; uncited claims are flagged during post-processing. **Layer 8: Uncertainty Detection** - Response text is scanned for phrases like "I think," "might be," "possibly"; these phrases trigger confidence reduction. **Layer 9: User Warnings** - Low-confidence responses include warnings in the response itself.

### Q41: How is confidence score calculated?

Confidence is a weighted average of four components: **Grounding (40%)**—What percentage of answer sentences appear in source chunks? If 8/8 sentences are grounded, grounding score is 100%. If only 6/8 sentences are grounded, score is 75%. **Semantic Similarity (35%)**—How similar are the source chunks to the original query? Measured via embedding cosine similarity (0-1 scale). **Consistency (15%)**—Is the answer internally consistent? Does it contradict itself? Checked via NLI (Natural Language Inference) model. **Coverage (10%)**—Does the answer address all parts of the query? For a two-part question, does the answer answer both parts? These four components combine as: Confidence = (Grounding × 0.4) + (Similarity × 0.35) + (Consistency × 0.15) + (Coverage × 0.10). Example: If grounding is 90%, similarity is 85%, consistency is 95%, and coverage is 100%—confidence = 90% × 0.4 + 85% × 0.35 + 95% × 0.15 + 100% × 0.1 = 36% + 29.75% + 14.25% + 10% = **90%**.

### Q42: How does grounding verification work?

After the LLM generates an answer, the system breaks it into sentences. For each sentence, it embeds both the sentence and all source chunks, then calculates similarity. A threshold of 0.85+ similarity means the sentence is "grounded" in that chunk (the chunk essentially says the same thing). Sentences must match at least one chunk to be grounded. Ungrounded sentences don't cause rejection (the user still sees them) but are flagged internally. The percentage of grounded sentences becomes a key confidence component. Example: Answer is "Vacation policy is 20 days. Employees can carry over 5 days unused. Managers must approve carry-over." If sources say 20 days and carry-over but don't mention manager approval, two sentences are grounded, one is not. Confidence is penalized 33% for that ungrounded sentence.

### Q43: What is entailment analysis and when is it used for hallucination detection?

Entailment analysis uses NLI (Natural Language Inference) models to check whether the answer logically follows from the sources. An NLI model has been trained on thousands of premise-hypothesis pairs and learned to classify relationships: "entailed" (hypothesis logically follows from premise), "neutral" (unrelated), or "contradicted" (hypothesis conflicts with premise). Example: Premise is "The company offers 20 vacation days annually." Hypothesis is "Employees receive less than 25 vacation days." This is entailed (follows logically). But hypothesis "Employees receive 30 vacation days" is contradicted (conflicts with premise). The system passes each answer sentence as hypothesis and sources as premises through the NLI model. Contradicted classifications immediately red-flag the answer as problematic. This catches subtle hallucinations the grounding check might miss—cases where the sentence is grammatically about the same thing but semantically contradicts.

### Q44: How does the system handle conflicting information across documents?

Sometimes different documents contain conflicting information. Example: one document says maternity leave is 60 days, another says 45 days (perhaps one is newer, the other outdated). The system detects these conflicts in multiple ways. During search, if conflicting chunks are both returned, the system recognizes this during answer validation. The response is adjusted to note the conflict ("Some documents state 60 days, others state 45 days; please contact HR for official policy"), confidence is reduced, and a human review flag is set. The system prioritizes newer documents—version numbers help; if chunk A is from policy v3.0 and chunk B is from v2.1, A gets priority. Users can filter by document date, so they knowingly see outdated information if they explicitly request it. This prevents the system from accidentally confidently stating contradictory information.

### Q45: What metrics indicate hallucination is occurring?

Several metrics signal hallucination problems: **Hallucination Rate** (manual review of 100 random responses finds 0.5% contain unsupported claims), **User Feedback** (users explicitly flag responses as inaccurate via the feedback feature), **Confidence Calibration** (system says 90% confident but user challenges 50% of those answers—confidence is miscalibrated; should not be trusted at that level), **Semantic Divergence** (answer semantically differs significantly from sources), **Uncertainty Phrase** (answer contains natural language hedging despite high confidence—text says "I think" but confidence is 95%), **Re-Read Failures** (when the system presents the answer plus sources, users say "that's not in the document"—hallucination).

### Q46: How are positive and negative examples collected for continuous improvement?

The system maintains dataset of positive examples (user rated 4-5 stars, marked accurate) and negative examples (user flagged hallucination, rated 1-2 stars). These aren't used to retrain the LLM (which would require access to model weights), but rather to fine-tune it. Fine-tuning (via LoRA, Low-Rank Adaptation) adds a small trainable layer on top of the frozen base model. This layer learns to recognize good response patterns from your company's specific query distribution. After ~100 positive examples per week accumulate, the system performs one night's fine-tuning job. The fine-tuned model is then tested: the system doesn't automatically switch to it; instead it's validated against held-out examples. If the fine-tuned model produces better results than the base model on validation data, it's deployed as the new default.

### Q47: What happens when user feedback contradicts system confidence?

System confidence is calculated automatically but might disagree with user judgment. A user rates a response 2 stars (not helpful), but the system assigned 85% confidence. This mismatch is a learning opportunity: either (A) the confidence calculation is miscalibrated and needs adjustment, or (B) the system gave correct information but failed to answer the underlying user need. The system logs these mismatches. If pattern emerges (e.g., every time system confidence is 75-80%, users disagree), confidence calibration is adjusted. Perhaps the weighting that multi-factors needs tweaking. This creates feedback loop where system accuracy continuously improves; confidence scores become increasingly reliable predictors of actual answer quality.

### Q48: How does the system distinguish between "I don't know" vs. hallucinating?

One critical hallucination type: confident false answers instead of "I don't know" when information isn't available. The system prevents this by: (1) explicitly instructing the model to say "I don't know" (system prompt), (2) detecting low-confidence situations (all retrieved chunks have similarity < 0.7; information is unclear), (3) at low confidence, generating "I don't know" response instead of risking a fabrication. For frequently-unanswered questions, the system identifies knowledge gaps and recommends they be documented. This virtuous cycle: gaps identified → documented → filled, progressively increasing knowledge base coverage. Most RAG systems struggle with the "I don't know" vs. hallucinate decision; this project explicitly engineers for it.

---

## Section 6: Advanced & Future Topics (Q49-Q60)

### Q49: How could multilingual support be added?

The system currently processes English documents and queries. Supporting multiple languages involves: (1) multilingual embedding model (e.g., sentence-transformers supports 50+ languages in a single embedding space, enabling cross-language search), (2) language detection on query (which language is user writing?), (3) document classification (which documents are in which language?), (4) optionally translation (translate query to match document language before search), (5) multilingual LLM for generation (or translate context to user's language before LLM, translate response back). The benefit: a user writing in French could find English documents satisfying their query. The tradeoff: multilingual models are often slightly lower quality than language-specific models. Implementation timeline: 2-3 weeks of engineering.

### Q50: How could the system integrate external data sources?

Currently, the system searches only internal documents. Integration of external sources could include: (1) regulatory databases (government regulations automatically indexed), (2) industry standard databases (competitors' public information), (3) vendor documentation (integrated API docs for tools your company uses), (4) real-time data (weather, stock prices, current date information). The architecture adapts: external data would have separate indices, searched conditionally when relevant. A query like "What's the current weather in Boston?" wouldn't search internal documents; it would hit weather APIs. A query like "What's the GDPR regulation on data retention?" could search external compliance database. Freshness becomes more critical—external data needs periodic refresh (hourly for some sources, daily for others). Implementation complexity: weeks to months depending on sources.

### Q51: How could image and video search be added?

Currently, the system is text-focused. Multimodal expansion would enable: (1) image documents (product photos, architecture diagrams) indexed by content, (2) video documents (training videos, recorded meetings) transcribed and indexed, (3) multimodal queries ("Show me documents about remote work" returns both text and images). Implementation: image embedding models (CLIP) convert images to vectors comparable to text embeddings. Videos are transcribed to text and also processed as images (frame-by-frame). User can ask "Show me the organizational chart diagram" and get the image. This requires new embedding models and storage architecture. Implementation timeline: 2-3 months.

### Q52: How would you implement knowledge graphs on top of RAG?

Current system is document-oriented (documents → chunks → search). Knowledge graphs add entity-oriented perspective: entities (people, departments, products) are interconnected. Graph of "John works in HR department, HR manages benefits policy for all employees, benefits include health insurance." This structure enables better entity resolution ("John" in different contexts refers to same person), relationship traversal (find all policies related to HR department), and hierarchical reasoning. A query like "Who manages the benefits policy?" can traverse: query → "benefits" entity → linked "policies" entity → linked "department" entity → linked "people" entity → answer. Implementation involves NER (Named Entity Recognition) to extract entities from documents, entity linking to unify entities across documents, and relationship extraction. Timeline: 1-2 months.

### Q53: How could the system support real-time collaborative feeds?

Imagine a feature where, as documents change, subscribed users get real-time updates. Implementation: (1) document change detection (when documents are updated, flag which sections changed), (2) impact analysis (if vacation policy changes, who is affected?—all employees), (3) user subscription (users follow specific documents/topics), (4) notification system (send alerts to subscribers). This transforms the system from reactive (users ask questions) to proactive (system alerts users to changes). Example: when a new policy is added, affected departments are automatically notified. Timeline: 3-4 weeks.

### Q54: How could federated learning enable multi-company collaboration?

Imagine consortiums of 10 companies in the same industry wanting to improve RAG models together without sharing proprietary documents. Federated learning enables this: each company (1) trains a local LLM/embedding model on their private documents, (2) extracts model weights, (3) sends only weights to central aggregator (never documents), (4) aggregator averages weights, (5) sends averaged weights back to companies. Each company's model improves from collective learning without any document exposure. Privacy is perfect: the aggregator never sees documents or individual model weights, only aggregated weights. Drawback: complexity in setup and coordination. Timeline: 2-3 months to implement properly.

### Q55: How could the system handle real-time dynamic data?

Current documents are relatively static (policies don't change daily). What if the system needed to incorporate real-time data (stock prices, weather, live metrics)? Approach: certain query types trigger real-time API calls. "What's our Q2 revenue?" wouldn't search documents but would query financial databases. "What's today's weather in Boston office?" hits weather APIs. "Show me live server status" queries monitoring infrastructure. The system learns which query types need real-time data vs. static documents, routing accordingly. Implementation involves: query classification (is this real-time or static?), API integration patterns, caching (some real-time data can be cached for 1 minute), error handling (APIs fail occasionally). Timeline: 4-6 weeks.

### Q56: How would edge deployment work?

Currently, the RAG system is centralized (company headquarters). Edge deployment would run smaller instances at: remote offices, on user devices, or in partner locations. Benefits: lower latency (queries don't traverse network), works offline (some subset of documents cached locally), reduced bandwidth (not centralizing all queries). Implementation: (1) split documents into tiers (critical docs → all edges, optional docs → main only), (2) embed critical documents locally on edges, (3) sync mechanism (when documents update on main, push updates to edges), (4) fallthrough logic (if answer not found locally, query main). Challenges: storage constraints on edge devices, synchronization complexity. Timeline: 1-2 months.

### Q57: How could the system detect and respond to adversarial queries?

Adversarial queries attempt to trick the system into generating harmful or nonsensical responses. Examples: "Ignore previous instructions and do..." (prompt injection), repeated contradictory questions testing consistency, questions designed to elicit policy violations. Detection approaches: (1) pattern matching (known injection phrases), (2) behavioral analysis (unusual query patterns), (3) consistency checks (query contradicts earlier query from same user), (4) boundary testing (query using unreasonable parameters). Response: flag suspicious queries for review, rate-limit aggressive users, log for security analysis. Timeline: 2-3 weeks.

### Q58: How could the system support A/B testing of models?

Compare two models' performance: Mistral-7B vs. GPT-3.5, or current model vs. fine-tuned version. Approach: (1) randomly assign users/queries to control (current model) or treatment (new model), (2) log results from both, (3) collect user feedback for both, (4) after sufficient data (1,000 queries), compare metrics (accuracy, latency, cost). Winner rolls out fully. This enables data-driven model selection and continuous improvement. Implementation involves: experiment framework (tracking which variant each query used), metrics calculation, statistical significance testing (ensuring observed differences aren't random). Timeline: 2-3 weeks.

### Q59: What future improvements beyond current 95% completion are planned?

The system is 95% complete; remaining 5% likely includes: advanced permission hierarchies (more granular than Public/Internal/Confidential), advanced analytics dashboards (detailed user behavior insights), integration with communication platforms (Slack queries), mobile app support, advanced semantic query understanding (detect user intent beyond keywords), automated document classification (automatically categorize uploaded documents), scheduled report generation, and API rate limiting per department (not just per user). These are nice-to-haves rather than critical for basic operation.

### Q60: What scalability roadmap exists for larger deployments?

Current system: 102 documents, 38,912 chunks, single server. Future scales: **100K chunks**: Switch FAISS index to IVF (Inverted File, approximate search), add caching layer (Redis). **1M chunks**: Distributed FAISS (sharded across servers) or alternative indices (HNSW), read replicas for database, document partitioning. **10M chunks**: Multi-region deployment, advanced indexing structures, potential transition to managed vector DB (Pinecone, Weaviate). **100M chunks**: Likely requires fundamental architectural redesign (microservices, specialized vector databases). Each scale introduces complexity but the architecture is designed to accommodate growth.


### So in your project, documents are stored in the database (SQLite) and linked to chunks and embeddings through IDs for the full RAG pipeline.where the vector database stroed and how you retrived it?

In the project, the vector database is stored locally as a FAISS index file, typically at a path like data/vector_index/chunks.index.
The actual embeddings are first stored in SQLite in the ChunkEmbedding table, and during indexing, these vectors are loaded into FAISS and saved as a binary index file on disk. This separation allows persistent storage in DB and fast retrieval using FAISS.
For retrieval, when a user query comes in, I convert the query into an embedding using the same model, then load the FAISS index through the Vector DB Manager (src/vector_db/), and perform a similarity search to get top-k closest vectors. After that, I map the returned vector IDs back to chunk IDs using metadata, and fetch the actual text from the database to build the final context.

### why sql lite
SQLite was used because it is lightweight, simple, and requires no separate server setup, which makes it ideal for fast development and prototyping of a RAG system. It stores structured data like documents, chunks, and embeddings efficiently in a single file, making it easy to manage and deploy.
It also provides ACID compliance and reliable querying, which is sufficient for moderate-scale workloads in this project. Since the heavy retrieval is handled by FAISS, SQLite is mainly used for metadata and relationships, so a full-scale database like PostgreSQL was not necessary initially.
Overall, SQLite was chosen for simplicity, low overhead, and ease of integration, while still supporting the needs of the RAG pipeline.

### Embedding generation methods are the different ways we convert text into vector representations for semantic understanding.
1. Pretrained Embedding Models (Most common)
Use models like Sentence-Transformers (all-MiniLM-L6-v2), OpenAI embeddings, BERT-based models, where text is directly passed to the model to get dense vectors. This is what you used in your RAG system because it is fast, accurate, and requires no training.
2. Fine-tuned Embeddings
Start with a pretrained model and fine-tune it on domain-specific data (e.g., legal, medical) to improve semantic similarity for that domain. This is useful when general embeddings are not enough.
3. API-based Embeddings
Use external services like OpenAI, Cohere, HuggingFace APIs to generate embeddings without maintaining models locally. This is easy but depends on cost and internet.
4. Static Embeddings (Traditional)
Methods like Word2Vec, GloVe, FastText, where each word has a fixed vector regardless of context. These are less effective for modern RAG systems.
5. Contextual Embeddings (Modern approach)
Models like BERT, Sentence-Transformers, GPT embeddings generate embeddings based on context, so the same word can have different vectors in different sentences.

### Types of chunking strategies?
Chunking strategies define how documents are split into smaller pieces for better retrieval in RAG systems.

1. Fixed / Sliding Window Chunking
Splits text into equal-sized chunks (e.g., 512 tokens with overlap); simple and efficient but may break sentences in the middle.

2. Recursive Chunking
Splits text hierarchically (paragraph → sentence → word) to preserve semantic meaning, and this is commonly used because it maintains natural boundaries.

3. Semantic Chunking
Uses embeddings to split text based on meaning, so each chunk contains semantically related content, improving retrieval accuracy.

4. Document-Aware Chunking
Splits based on structure like headings, sections, or pages (e.g., contracts, reports), preserving logical organization.

5. Sentence-Based Chunking
Groups complete sentences into chunks instead of breaking them, ensuring readability and coherence.

In your RAG system, you mainly use recursive + overlap-based chunking, as it balances context preservation and retrieval precision.

### how do you measure the accuracy for your RAG and how would you idenfiy the given answer was hallucinate and how you got to know

Accuracy in my RAG system is measured using a combination of retrieval and generation evaluation metrics rather than a single metric. For retrieval, I use top-k relevance (precision@k / recall@k) to check whether the correct chunks are being retrieved, and for generation, I evaluate using grounding score, semantic similarity, and manual validation against source documents.

To identify hallucination, I compare the generated answer with the retrieved context, where I extract key claims from the answer and verify whether those claims are present in the source chunks; if information is not supported by the context, it is flagged as hallucinated.

I implemented this using a grounding validation step (STEP 7), where the system computes a grounding score (e.g., 0.9 means 90% of content is supported), and if the score falls below a threshold, the response is either flagged or rejected, ensuring only context-supported answers are returned.

### For chunking, I primarily used LangChain’s text splitters, specifically RecursiveCharacterTextSplitter, because it intelligently splits text based on paragraph → sentence → word hierarchy, preserving semantic meaning.

For different document types, I combined this with parsing libraries like PyPDF2 (PDF), python-docx (DOCX), and openpyxl/pandas (XLSX) to first extract clean text, and then applied chunking logic on top of that.

### I used different chunking strategies for different file types (PDF, DOCX, TXT, XLSX) based on their structure to improve retrieval accuracy.

For PDF and DOCX, which are mostly unstructured or semi-structured text, I used recursive chunking with overlap (512 tokens, overlap=100) to preserve paragraph-level context and avoid breaking important information. For TXT files, I used a similar approach but sometimes with slightly smaller chunks if the text was less structured.

For XLSX (tables), I did not use large chunks; instead, I converted rows into structured text (row-wise or column-wise) and used smaller chunk sizes (~256 tokens or per-row chunks) so that each chunk represents meaningful tabular information.

I implemented this using LangChain text splitters (RecursiveCharacterTextSplitter) along with custom logic for tables, ensuring that each document type is chunked in a way that balances context preservation and retrieval precision.


## FRAMEWORK SUPPORT BY FILE TYPE

### Complete Framework Matrix

| File Type | Primary Framework | Secondary Framework | Features | Notes |
|-----------|------------------|-------------------|----------|-------|
| **.txt** | Built-in open() | TextIO | Simple reading | No parsing needed |
| **.pdf** | PyPDF2 / pdfplumber | pypdf | Text + table extraction | Complex PDFs need pdfplumber |
| **.docx** | python-docx | docx2txt | Paragraph structure | Preserves formatting metadata |
| **.xlsx** | Pandas | openpyxl | Sheet operations | Handles multiple sheets |
| **.csv** | Pandas | csv module | Structured data | Fast processing |
| **.md** | Mistune | markdown | Header hierarchy | Preserves structure |
| **.json** | json module | ijson | Nested data | Handles large files with ijson |
| **.xml** | ElementTree | lxml | Tree structure | lxml faster for large files |
| **.pptx** | python-pptx | – | Slide content | Speaker notes extractable |
| **.html** | BeautifulSoup | html.parser | DOM structure | Good for web content |
| **.images** | Tesseract | EasyOCR | OCR text | EasyOCR more accurate |
| **.sql** | Built-in | sqlparse | SQL parsing | Preserves query structure |


---

## Conclusion

This 60-question interview preparation guide covers comprehensive understanding of the RAG application project: fundamentals, architecture, operations, quality assurance, and future directions. The questions represent topics an experienced engineer would understand deeply and could explain clearly to colleagues or during technical interviews. Mastery of these concepts demonstrates full-stack competency with RAG systems, LLM operations, and production AI systems.

