# Documentation Index

Welcome to the RAG Application Documentation. This directory contains comprehensive guides for understanding, developing, deploying, and maintaining the RAG system.

## 📚 Documentation Files

### Getting Started
- **[README.md](../README.md)** - Project overview, features, and quick start guide
- **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - System architecture and data flow diagrams

### Development
- **[DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)** - Development setup, workflow, and best practices
- **[Contributing Guide](CONTRIBUTING.md)** - Contribution guidelines and code standards

### Deployment & Operations
- **[DEPLOYMENT_GUIDE.md.py](DEPLOYMENT_GUIDE.md.py)** - Production deployment, Docker setup, and monitoring

## 🎯 Quick Navigation

### By Role

**Developers**
- Start with: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
- Then review: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)
- Reference: Contributing guidelines in this directory

**DevOps/Operations**
- Start with: [DEPLOYMENT_GUIDE.md.py](DEPLOYMENT_GUIDE.md.py)
- Monitor: Application logs and Prometheus metrics
- Scale: Using Docker Compose configuration

**Architects**
- Review: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)
- Understand: System design patterns and scaling strategies

### By Topic

**LLM Providers**
- Supported: OpenAI, Mistral, HuggingFace, Groq
- Configuration: See DEPLOYMENT_GUIDE.md.py
- Adding new provider: See DEVELOPMENT_WORKFLOW.md

**API Documentation**
- Interactive: http://localhost:8000/docs (Swagger UI)
- Alternative: http://localhost:8000/redoc (ReDoc)
- Full spec: See API routes in src/api/routes/

**Testing**
- Unit tests: tests/unit/
- Integration tests: tests/integration/
- Performance tests: tests/performance/
- Run: `pytest` or `make test`

**Response Validation**
- 5-validator system: Relevance, Coherence, Length, Grounding, Completeness
- Implementation: src/validation/validators.py
- Scoring logic: src/validation/scorer.py

## 🏗️ System Architecture Overview

```
┌─────────────────┐
│  Client/Users   │
└────────┬────────┘
         │
    ┌────▼──────────────────────────────┐
    │   FastAPI Application             │
    │  ┌──────────────────────────────┐ │
    │  │   42 REST API Endpoints      │ │
    │  │  (Documents, Embeddings,     │ │
    │  │   Search, Query, Generation, │ │
    │  │   Validation)                │ │
    │  └──────────────────────────────┘ │
    └────┬──────────────────────────────┘
         │
    ┌────┴─────────────────────────┐
    │                              │
    ▼                              ▼
┌──────────────┐          ┌──────────────────┐
│  Document    │          │  LLM Engine      │
│  Processor   │          │  ┌────────────┐  │
│  & Search    │          │  │ OpenAI     │  │
│  (FAISS)     │          │  │ Mistral    │  │
│              │          │  │ HuggingFace│  │
│              │          │  │ Groq       │  │
└──────┬───────┘          └────────┬───────┘
       │                          │
       │         ┌────────────────┴──────────────────┐
       │         │                                   │
       ▼         ▼                                   ▼
  ┌────────────────────────┐         ┌──────────────────────────┐
  │  Vector Database       │         │  Response Validator      │
  │  & Knowledge Base      │         │  (5 Validators)          │
  │  (PostgreSQL + FAISS)  │         │  - Relevance             │
  │                        │         │  - Coherence             │
  │                        │         │  - Length                │
  │                        │         │  - Grounding             │
  │                        │         │  - Completeness          │
  └────────────────────────┘         └──────────────────────────┘
```

## 🔗 Key Components

### API Layer (src/api/routes/)
- **documents.py**: Document upload and management
- **embeddings.py**: Embedding generation and caching
- **search.py**: Semantic and hybrid search
- **query.py**: Query processing and history
- **generation.py**: LLM-powered response generation
- **validation.py**: Response validation and scoring

### Core Processing (src/)
- **document_processor/**: PDF, DOCX, TXT, XLSX parsing
- **embedding/**: Sentence transformers and embedding management
- **generation/**: LLM providers and hallucination detection
- **validation/**: Response quality validators

### Infrastructure
- **config/settings.py**: Environment-based configuration
- **database/**: SQLAlchemy models and sessions
- **monitoring/**: Prometheus metrics and logging

## 📈 Pipeline Workflow

```
1. Document Upload
   ↓
2. Chunking & Processing
   ↓
3. Embedding Generation
   ↓
4. Vector Database Storage
   ↓
5. User Query
   ↓
6. Semantic Search with Ranking
   ↓
7. LLM Generation (Multi-provider with fallback)
   ↓
8. Response Validation (5-validator scoring)
   ↓
9. Delivery to User
```

## 🐳 Docker Deployment

Services:
- **FastAPI**: Application server
- **PostgreSQL**: Primary database
- **Redis**: Caching and sessions
- **Ollama**: Local Mistral LLM (optional)

Configuration: See [DEPLOYMENT_GUIDE.md.py](DEPLOYMENT_GUIDE.md.py)

## 📝 Logging & Monitoring

- **Application Logs**: logs/rag_app.log
- **Log Level**: Configurable via LOG_LEVEL environment variable
- **Prometheus Metrics**: http://localhost:8001/metrics (if enabled)
- **Health Check**: http://localhost:8000/health

## ❓ FAQ & Troubleshooting

See [DEPLOYMENT_GUIDE.md.py](DEPLOYMENT_GUIDE.md.py) for:
- Common issues and solutions
- Performance tuning
- Scaling configuration
- Best practices

## 🔐 Security Considerations

- Environment variables for secrets (never commit .env)
- API key management for LLM providers
- Database credential rotation
- CORS configuration in settings
- Rate limiting and request validation

## 📞 Support & Contributions

For questions, issues, or contributions:
1. Check documentation above
2. Review code comments and docstrings
3. Check [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
4. Open an issue with reproduction steps

---

**Last Updated**: March 2, 2026  
**Version**: 1.0.0  
**Status**: Production Ready ✅
