# 🎓 Academe - Multi-Agent Academic AI Assistant

A production-grade, full-stack AI application that transforms how students interact with dense academic materials through Retrieval-Augmented Generation (RAG), multi-agent orchestration, and adaptive learning.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
![LangChain](https://img.shields.io/badge/LangChain-0.3-blue)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Production Deployment](#production-deployment)
- [Testing](#testing)
- [Performance](#performance)
- [Development Highlights](#development-highlights)
- [Documentation](#documentation)

---

## Overview

### The Problem

Students struggle with dense academic textbooks and research papers. Traditional approaches require hours of effort to understand complex concepts, with no adaptive support for different learning levels or learning styles.

### The Solution

Academe is an AI-powered academic assistant that:

1. **Understands Your Materials**: Upload textbooks and papers; the system creates a searchable knowledge base using vector embeddings
2. **Adapts to Your Level**: Provides explanations ranging from beginner ("explain like I'm 5") to PhD-level technical depth
3. **Multi-Modal Support**: Combines concept explanations, code examples, practice problems, and research synthesis
4. **Learns From You**: Tracks your progress and identifies weak areas for targeted improvement
5. **Cites Sources**: All document-based answers include page references and citations

---

## Key Features

### Multi-Agent System Architecture

Specialized AI agents handle different tasks:

- **Router Agent**: Analyzes queries and routes to the appropriate specialist
- **Concept Explainer**: Provides adaptive explanations with multiple difficulty levels
- **Code Helper**: Generates, explains, and debugs code with best practices
- **Research Agent**: Synthesizes information from multiple sources with citations
- **Practice Generator**: Creates tailored quizzes and practice problems

### Advanced RAG Pipeline

- **Hybrid Search**: BM25 (keyword) + vector (semantic) with weighted score fusion
- **Cross-Encoder Reranking**: BAAI/bge-reranker-base re-scores candidates for precision
- **Adaptive Chunking**: Auto-detects document type (textbook/paper/notes/code) and adjusts chunk size
- **Contextual Embeddings**: Document title and section prepended before embedding for richer vectors
- **Sliding Window Context**: Adjacent chunks included in LLM context for fuller answers
- **Query Rewriting + HyDE**: LLM resolves pronouns; optional hypothetical-document retrieval
- **Self-RAG**: LLM verifies retrieval quality; reformulates and retries if context is insufficient
- **Query Decomposition**: Complex multi-part questions split into atomic sub-queries for better coverage
- **Multi-Query Expansion**: 3 alternative phrasings per query for broader recall
- **Semantic Response Cache**: Per-user scoped; similar past queries return cached answers instantly (~1ms vs ~1s)
- **Retrieval Feedback Loop**: Thumbs up/down tracking identifies weak queries and documents
- **Proposition-Based Indexing**: Chunks decomposed into atomic factual statements for precise retrieval
- **Knowledge Graph**: Entity-relationship extraction with multi-hop graph traversal across documents
- **Retrieval Profiles**: Named presets (`fast` / `balanced` / `deep`) auto-selected by query complexity
- **Request Budget**: Per-query caps on LLM calls, retries, and latency prevent cost/latency explosions
- **Deterministic Fallback**: Ordered degradation chain for every external dependency (LLM, reranker, Pinecone)
- **Per-Stage Value Metrics**: Tracks whether each pipeline stage changed the result, with aggregate counters
- **Redis Response Cache**: Optional Redis-backed per-user semantic cache that persists across restarts and multi-instance deployments
- **Document Mode**: Answers drawn from uploaded materials with source citations
- **Knowledge Mode**: Falls back to LLM general knowledge when documents don't cover the topic
- **arXiv Fallback**: Research agent searches arXiv papers when no documents are uploaded or RAG retrieval fails
- **End-to-End Feedback Loop**: Frontend thumbs up/down → feedback API → MongoDB → Pandas analytics identifying weak documents and underperforming query types
- **RAG Analytics (Pandas)**: MongoDB aggregation pipelines + Pandas for satisfaction trends, weak document detection, query type performance, and actionable recommendations
- **arXiv MCP Server**: Standalone MCP tool server exposing paper search for external clients (Claude Desktop, etc.)

### Personalized Learning

- **Adaptive Difficulty**: Automatically adjusts explanation complexity
- **Progress Tracking**: Monitors concept mastery across topics
- **Weak Area Identification**: Recommends review materials based on quiz performance
- **Learning Style Support**: Visual, code-based, or theoretical explanations

### Production-Ready Features

- **Real-Time Streaming**: WebSocket support for token-by-token responses
- **Async Processing**: Celery background workers for document indexing
- **Observability Stack**: Prometheus + Grafana for metrics and visualization
- **Auto-Scaling Ready**: Docker Compose orchestration with configurable workers

---

## Architecture

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│              Next.js Frontend (Vercel CDN)                   │
│         React + TypeScript + Redux + WebSockets              │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTPS/WSS
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                        │
│                    Nginx Reverse Proxy                       │
│              (Load Balancing + SSL Termination)              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│                  FastAPI Backend (EC2)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        LangGraph Multi-Agent System (Cyclic)          │ │
│  │                                                        │ │
│  │  ┌──────────┐    ┌─────────────┐    ┌───────────┐    │ │
│  │  │  Router  │───▶│   Agent     │───▶│ Response  │    │ │
│  │  │  Agent   │    │  Executor   │◀───│  Grader   │    │ │
│  │  └──────────┘    └─────────────┘    └───────────┘    │ │
│  │       │           (dispatches to)     ▲  │  │        │ │
│  │       │low        ┌──────────────┐    │  │  │reroute │ │
│  │       │conf.      │Concept│Code  │    │  │  ▼        │ │
│  │       ▼           │Research│Prac.│  refine ┌──────┐  │ │
│  │  ┌──────────┐    └──────────────┘    │  │Re-    │  │ │
│  │  │ Clarify  │                        │  │Router │  │ │
│  │  │  Query   │                        │  └──────┘  │ │
│  │  └──────────┘                                      │ │
│  └────────────────────────────────────────────────────┘ │
│                           │                                 │
│              ┌────────────┴────────────┐                    │
│              ▼                         ▼                    │
│     ┌─────────────────┐      ┌─────────────────┐            │
│     │  RAG Pipeline   │      │  Memory System  │            │
│     │  - Chunking     │      │  - User Prefs   │            │
│     │  - Reranking    │      │  - Progress     │            │
│     └─────────────────┘      └─────────────────┘            │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│  Data Layer      │            │  Vector Layer    │
│                  │            │                  │
│  MongoDB Atlas   │            │  Pinecone DB     │
│  - Users         │            │  - Embeddings    │
│  - Conversations │            │  - Semantic      │
│  - Documents     │            │    Search        │
│  - Progress      │            │  - Hybrid        │
│                  │            │    Retrieval     │
└──────────────────┘            └──────────────────┘
         │
         ▼
┌──────────────────┐
│  Task Queue      │
│                  │
│  Celery + Redis  │
│  - Document      │
│    Processing    │
│  - Async Tasks   │
└──────────────────┘
```

### Component Interaction Flow

```
User Query → Check Docs → Router ──[confidence gate]──→ Agent Executor
                                        │                     │
                                   low confidence         RAG Search + LLM
                                        │                     │
                                        ▼                     ▼
                                  Clarify Query        Response Grader
                                        │              ╱     │     ╲
                                        ▼          PASS   REFINE  REROUTE
                                    [Response]      │       │       │
                                                    ▼       ▼       ▼
                                                  [END]  [Agent]  [Re-Router]
                                                          (loop)   → Agent
```

For detailed architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Technology Stack

### Backend Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.115 | High-performance async REST API |
| **LLM Orchestration** | LangChain 0.3 + LangGraph 0.2 | Multi-agent workflow management |
| **Vector Database** | Pinecone | Semantic search and embeddings |
| **Database** | MongoDB 7.0 | User data, conversations, documents |
| **Cache/Queue** | Redis 7 + Celery 5.3 | Task queue and caching |
| **Embeddings** | OpenAI text-embedding-3-small | Document vectorization (1536d) |
| **LLM Provider** | Google Gemini 2.5 Flash | Primary language model |

### Frontend Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | Next.js 14 | React with server-side rendering |
| **Language** | TypeScript | Type-safe development |
| **State Management** | Redux Toolkit + RTK Query | Centralized state and API caching |
| **Styling** | Tailwind CSS | Utility-first responsive design |
| **Real-Time** | WebSocket | Streaming LLM responses |

### DevOps & Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **IaC** | Terraform | Infrastructure as Code for AWS |
| **Containerization** | Docker + Docker Compose | Service orchestration |
| **CI/CD** | GitHub Actions | Automated testing and deployment |
| **Hosting** | AWS EC2  + Vercel | Backend and frontend hosting |
| **Monitoring** | Prometheus + Grafana | Metrics collection and visualization |
| **Reverse Proxy** | Nginx | Load balancing and routing |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose
- MongoDB 7.0+ (or use Docker)
- Redis 7.0+ (or use Docker)

### Local Development

```bash
# Clone repository
git clone https://github.com/Klarline/academe.git
cd academe

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
# - GOOGLE_API_KEY (required — Gemini, user-facing assistant)
# - OPENAI_API_KEY (required — gpt-4o-mini for query rewriting, HyDE, RAGAS evaluation)
# - MONGODB_URI (default: mongodb://localhost:27017)
# - JWT_SECRET_KEY (generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))')
# - PINECONE_API_KEY (optional, uses mock mode if not provided)

# Start infrastructure services
cd ../infrastructure/docker
docker-compose up -d mongodb redis

# Start backend (from project root)
cd ../../
./scripts/start_api.sh

# Frontend setup (new terminal)
cd frontend
npm install
cp .env.example .env.local

# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Start frontend
npm run dev
```

**Access application**: http://localhost:3000

### Docker Compose (All Services)

```bash
# Navigate to docker directory
cd infrastructure/docker

# Start all services (including monitoring)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

**Access Points:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/academe123)

```bash
# Stop all services
docker-compose down
```

---

## Production Deployment

### Terraform Deployment (Recommended)

Deploy complete infrastructure to AWS in ~10 minutes:

```bash
# Prerequisites
# - AWS account with credentials configured (aws configure)
# - SSH key created and imported to AWS
# - Docker Hub account for pulling images

# Configure deployment
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize and deploy
terraform init
terraform plan    # Review resources to be created
terraform apply   # Type 'yes' to confirm

# Wait 5-8 minutes for automated setup
# Test deployment
curl http://$(terraform output -raw ec2_public_ip):8000/health
```

**What gets deployed:**
- EC2 instance (t3.small: 2 vCPU, 2GB RAM, 50GB storage)
- Security groups (SSH restricted to your IP, HTTP/HTTPS open)
- Elastic IP (consistent public address)
- Automated Docker setup with all services
- Nginx reverse proxy configuration

For complete deployment guide, see [terraform/README.md](terraform/README.md).

### Manual AWS Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for step-by-step EC2 setup without Terraform.

### Frontend Deployment (Vercel)

```bash
cd frontend
npm install -g vercel
vercel login
vercel --prod

# Configure environment variables in Vercel dashboard:
# - NEXT_PUBLIC_API_URL: http://YOUR_EC2_IP:8000
# - NEXT_PUBLIC_WS_URL: ws://YOUR_EC2_IP:8000
```

---

## Testing

### Run Tests

```bash
cd backend

# All unit tests
pytest tests/unit/ -v

# With coverage report
pytest tests/unit/ --cov=core --cov=api --cov-report=html

# View HTML coverage report
open htmlcov/index.html

# Run specific test file
pytest tests/unit/test_auth_service.py -v
```

### CI/CD Testing

Every push triggers automated testing:
- 449 unit tests across all modules
- Code quality checks (Black, isort, flake8)
- Security scanning (Bandit, Safety)
- Docker multi-stage builds
- Coverage reporting to Codecov

---

## Performance

### Response Time Benchmarks

- **Chat Queries**: <200ms p95 latency (excluding LLM inference)
- **Document Upload**: 6-10 seconds per PDF (async processing via Celery)
- **Semantic Search**: <100ms for top-10 results from 10k+ chunks
- **Health Checks**: <50ms response time

---

## Architecture

### Multi-Agent System (LangGraph)

The system uses **LangGraph** for state management and agent coordination:

**Agent Workflow** (cyclic, self-correcting):
1. **Check Documents** — identifies whether the user has uploaded materials
2. **Router Agent** — analyzes user intent and query type with confidence score
3. **Confidence Gate** — if confidence < 0.4, generates a clarification question instead of guessing
4. **Agent Executor** — dispatches to the appropriate specialist:
   - Conceptual questions → **Concept Explainer**
   - Code-related → **Code Helper**
   - Multi-source research → **Research Agent**
   - Practice/assessment → **Practice Generator**
5. **Response Grader** — LLM evaluates response quality (grounded? complete? correct agent?):
   - **PASS** → return to user
   - **REFINE** → loop back to agent with feedback (max 2 iterations)
   - **WRONG_AGENT** → re-route to a different specialist (max 1 re-route)
6. Response formatted and streamed to user

**State Management**:
```python
class WorkflowState(TypedDict, total=False):
    question: str
    user_id: str
    route: str                        # "concept", "code", "research", "practice"
    routing_confidence: float
    response: str
    refinement_count: int             # loop control (max 2)
    reroute_count: int                # loop control (max 1)
    grader_feedback: Optional[str]    # feedback for refinement
    grader_verdict: Optional[str]     # "pass", "refine", "reroute"
    previous_agents: List[str]        # agents already tried
```

### RAG Pipeline Implementation

**Document Ingestion**:
1. **Upload** → PDF/TXT/MD parsing with PyPDF2
2. **Type Detection** → Auto-classify as textbook, paper, notes, or code from content signals
3. **Adaptive Chunking** → Per-type chunk size (textbook 1200, paper 800, notes 600) with optional parent-child split
4. **Contextual Embedding** → Prepend document title + section before embedding with OpenAI text-embedding-3-small (1536 dims)
5. **Proposition Extraction** → Decompose chunks into atomic factual statements for fine-grained retrieval
6. **Knowledge Graph Extraction** → Extract entity-relationship triples (subject → predicate → object) from chunks
7. **Storage** → Pinecone vector database with chunk metadata; propositions and KG triples in MongoDB

**Retrieval** (12-step pipeline):
1. **Cache Check** → Return cached answer if semantically similar query exists for this user (cosine > 0.95)
2. **Query Rewriting** → LLM resolves pronouns and expands abbreviations using conversation history
3. **Query Decomposition** → Split complex multi-part questions into atomic sub-queries
4. **Multi-Query Expansion** → Generate 3 alternative phrasings, retrieve for each, merge results
5. **Adaptive Retrieval** → Query-type-aware BM25/vector weights (definition, comparison, code, procedural)
6. **Hybrid Search** → BM25 (10%) + vector (90%) weighted score fusion
7. **Cross-Encoder Reranking** → BAAI/bge-reranker-base re-scores top-20 → top-5
8. **Self-RAG Verification** → LLM judges context sufficiency; reformulates + retries if insufficient
9. **Context Expansion** → Sliding window (±1 neighbor chunks) or parent-child expansion
10. **Knowledge Graph Augmentation** → Multi-hop graph traversal adds related facts to LLM context

**Generation**:
1. **Prompt Engineering** → Include expanded context + KG relationships + system instructions
2. **LLM Inference** → Google Gemini 2.5 Flash (user-facing), OpenAI gpt-4o-mini (infrastructure)
3. **Streaming** → Token-by-token response via WebSocket
4. **Citation Extraction** → Parse and format source references
5. **Cache Store** → Save answer in user's cache partition for future similar queries

### Database Schema

**MongoDB Collections**:
- `users`: User accounts, preferences, learning profiles
- `conversations`: Chat history with agent metadata
- `documents`: Uploaded materials with processing status
- `chunks`: Document chunks with embeddings metadata
- `practice_sessions`: Quiz attempts and performance data
- `progress`: Concept mastery tracking per user
- `rag_metrics`: Retrieval performance metrics over time
- `retrieval_feedback`: User thumbs up/down on RAG answers
- `rag_responses`: Query/answer/sources stored per message for feedback linkage
- `propositions`: Atomic factual statements with source chunk back-references
- `knowledge_graph`: Entity-relationship triples for multi-hop reasoning

**Pinecone Index**:
- Dimensions: 1536 (OpenAI text-embedding-3-small)
- Metric: Cosine similarity
- Metadata: document_id, page_number, chunk_text, source

---

## Development Highlights

### Database Design Decisions

**Why MongoDB over PostgreSQL**:
1. Flexible schema for evolving agent response formats
2. Native JSON support for LLM outputs
3. Horizontal scaling for conversation history
4. Better performance for document-heavy workloads

**Indexing Strategy**:
- Compound index on `(user_id, created_at)` for conversation queries
- Text index on document content for search
- TTL index for session cleanup

### RAG System Deep Dive

**Adaptive Chunking**:
- Auto-detects document type (textbook, paper, notes, code) from structural signals
- Per-type profiles: textbook 1200 chars / 300 overlap, paper 800/200, notes 600/100, code 1000/150
- Parent-child mode: large parent windows → small retrieval children with parent expansion at context time
- Metadata preservation: page numbers, section headings, document titles

**Hybrid Search**:
- BM25 for keyword matching (lazy-built, in-memory cached per user)
- Vector similarity for semantic search (contextual embeddings with doc title + section prefix)
- Weighted score fusion (0.1 BM25 + 0.9 vector) — tunable per query type via AdaptiveRetriever
- Cross-encoder reranking (BAAI/bge-reranker-base) for final precision

**Query Optimization**:
- LLM-based query rewriting to resolve pronouns and expand abbreviations
- HyDE (Hypothetical Document Embeddings) for better semantic retrieval
- Adaptive retrieval adjusts strategy based on query type (definition, comparison, code, procedural)
- Multi-query expansion: 3 alternative phrasings retrieved and merged for broader recall
- Query decomposition: complex multi-part questions split into atomic sub-queries

**Self-Correction & Caching**:
- Self-RAG: LLM verifies if retrieved context is sufficient; reformulates query and retries (up to 2x) if not
- Semantic response cache: per-user cosine similarity lookup (threshold 0.95), TTL-based expiry, hit/miss stats, auto-invalidation on document changes
- Retrieval feedback loop: thumbs up/down stored in MongoDB; identifies weak documents and tracks satisfaction rate

**Proposition-Based Indexing**:
- Chunks decomposed into atomic factual statements using LLM (gpt-4o-mini)
- Each proposition is self-contained and de-contextualized (pronouns resolved)
- Back-references to source chunk for context expansion at generation time
- Sentence-level fallback when LLM is unavailable

**Knowledge Graph**:
- Entity-relationship triples extracted from chunks (subject → predicate → object)
- In-memory BFS traversal from query entities for multi-hop reasoning
- Graph context appended to LLM prompt alongside retrieved chunks
- Enables questions that span multiple documents and concepts

**Context Expansion**:
- Sliding window: retrieves ±1 adjacent chunks from the same document
- Parent-child: retrieves small children, expands to full parent text for LLM context
- Knowledge graph: multi-hop traversal adds structured relationships to context
- Deduplication across overlapping windows

**Evaluation Framework**:
- Level 1 (retrieval-only): Precision@k, Recall@k, MRR via RetrievalEvaluator
- Level 2 (end-to-end): RAGAS metrics — faithfulness, relevancy, context precision/recall
- MetricsTracker: continuous logging to MongoDB with trend analysis

---

## Project Structure

```
academe/
├── docs/                      # Technical documentation
│   ├── ARCHITECTURE.md        # System design and architecture
│   ├── ARCHITECTURE_TIERS.md  # Tier 1/2/3 feature classification
│   ├── DESIGN_DECISIONS.md    # Rationale for every major choice
│   └── DEPLOYMENT.md          # Deployment guide
├── scripts/                   # Development & deployment automation
│   ├── start_all.sh           # Start all services locally
│   ├── start_api.sh           # Backend only
│   ├── start_frontend.sh      # Frontend only
│   ├── start_worker.sh        # Celery worker
│   ├── deploy_terraform.sh    # Automated Terraform deployment
│   ├── monitor_deployment.sh  # Health check monitoring
│   ├── configure_nginx.sh     # Nginx reverse proxy setup
│   └── add_nginx_metrics.sh   # Prometheus metrics configuration
├── infrastructure/            # Infrastructure as Code
│   ├── terraform/             # AWS deployment configuration
│   └── docker/                # Container configurations
│       └── docker-compose.yml # Service orchestration
├── monitoring/                # Observability configuration
│   └── prometheus.yml         # Metrics collection (Backend, MongoDB, Redis)
├── backend/
│   ├── api/                   # FastAPI REST API
│   │   ├── main.py            # Application entry point
│   │   ├── v1/                # API version 1
│   │   ├── endpoints/     # Route handlers (auth, chat, documents, analytics)
│   │   │   └── deps.py        # Dependencies (authentication)
│   │   └── services/          # Business logic layer
│   ├── core/                  # Core business logic
│   │   ├── agents/            # 5 specialized AI agents (research agent with arXiv fallback)
│   │   ├── auth/              # JWT authentication service
│   │   ├── config/            # Configuration management
│   │   ├── database/          # MongoDB repositories
│   │   ├── documents/         # Adaptive chunking, type detection, parent-child
│   │   ├── evaluation/        # Retrieval evaluator, RAGAS, metrics tracker
│   │   ├── graph/             # LangGraph cyclic workflow (router → agent → grader loop)
│   │   ├── memory/            # Adaptive context management
│   │   ├── models/            # Pydantic data models
│   │   ├── rag/               # RAG pipeline, request budget, retrieval profiles, analytics
│   │   ├── vectors/           # Embeddings & semantic search
│   │   ├── celery_config.py   # Task queue configuration
│   │   └── tasks.py           # Background job definitions
│   ├── tests/                 # Comprehensive test suite
│   │   ├── unit/              # 449+ unit tests
│   │   │   ├── agents/        # Agent behavior tests
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_chunking_features.py  # Adaptive chunking, parent-child, context
│   │   │   ├── test_database.py
│   │   │   ├── test_documents.py
│   │   │   ├── test_graph.py
│   │   │   ├── test_rag_advanced.py       # Self-RAG, cache, decomposition, feedback
│   │   │   ├── test_propositions_and_kg.py  # Proposition indexing, knowledge graph
│   │   │   ├── test_analytics.py          # RAG analytics module tests
│   │   │   ├── test_feedback_endpoint.py  # Feedback API endpoint tests
│   │   │   ├── test_mcp_arxiv.py          # arXiv MCP server tests
│   │   │   └── test_vectors.py
│   │   └── evaluation/        # RAG evaluation suite
│   │       ├── test_retrieval_evaluator.py
│   │       └── chunking_test_cases.py
│   ├── requirements.txt       # Python dependencies
│   ├── mcp_servers/           # MCP tool servers (standalone)
│   │   └── arxiv_server.py    # arXiv paper search MCP server
│   └── .env.example           # Environment template
├── frontend/
│   ├── app/                   # Next.js 14 app router
│   ├── components/            # React components
│   ├── hooks/                 # Custom React hooks
│   ├── store/                 # Redux state management
│   ├── lib/                   # Utilities and constants
│   └── types/                 # TypeScript definitions
├── .github/
│   └── workflows/
│       ├── ci.yml             # CI pipeline
│       └── docker.yml         # Docker build automation
└── README.md
```

---

## API Documentation

### Key Endpoints

**Authentication**:
```
POST   /api/v1/auth/register       # User registration
POST   /api/v1/auth/login          # User login
POST   /api/v1/auth/refresh        # Token refresh
```

**Chat & Agents**:
```
POST   /api/v1/chat/message        # Send message to agent system
POST   /api/v1/chat/feedback       # Submit thumbs up/down on responses
WS     /api/v1/ws/chat/{user_id}   # WebSocket streaming
GET    /api/v1/chat/conversations  # List conversations
```

**Documents**:
```
POST   /api/v1/documents/upload    # Upload PDF/DOCX
GET    /api/v1/documents/          # List user documents
DELETE /api/v1/documents/{id}      # Delete document
GET    /api/v1/documents/{id}/chunks # View document chunks
```

**Practice**:
```
POST   /api/v1/practice/generate   # Generate practice problems
POST   /api/v1/practice/sessions   # Save quiz attempt
GET    /api/v1/practice/stats      # User performance statistics
```

**Research**:
```
POST   /api/v1/research/query      # Multi-source research
GET    /api/v1/research/sources    # List available sources
```

**Monitoring**:
```
GET    /health                      # Service health check
GET    /metrics                     # Prometheus metrics
```

**Analytics**:
```
GET    /api/v1/analytics/report    # RAG performance report (satisfaction, weak docs, recommendations)
```

---

## Configuration

### Environment Variables

**Backend** (`backend/.env`):

```bash
# Required
GOOGLE_API_KEY=your_google_api_key              # Gemini — user-facing assistant
OPENAI_API_KEY=your_openai_key                  # gpt-4o-mini — query rewriting, HyDE, RAGAS eval
MONGODB_URI=mongodb://localhost:27017           # MongoDB connection
JWT_SECRET_KEY=your_32_char_minimum_secret      # JWT signing key

# Optional - Vector Database
PINECONE_API_KEY=your_pinecone_key             # Pinecone API (uses mock if not set)
PINECONE_INDEX_NAME=academe-prod               # Pinecone index name

# Optional - Alternative LLM Providers
ANTHROPIC_API_KEY=your_claude_key              # Claude API (alternative to Gemini)
LLM_PROVIDER=gemini                             # gemini|claude|openai

# Optional - Advanced
CELERY_BROKER_URL=redis://localhost:6379/0     # Celery broker
LOG_LEVEL=INFO                                  # Logging level
```

**Frontend** (`frontend/.env.local`):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000       # Backend API URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000          # WebSocket URL
```

---

## Monitoring & Observability

### Prometheus Metrics

**Automatically Collected**:
- `http_requests_total`: Total requests by endpoint and status
- `http_request_duration_seconds`: Latency percentiles (p50, p95, p99)
- `http_requests_in_progress`: Concurrent requests
- Custom: Agent selection distribution, RAG retrieval times

### Health Checks

**Endpoint**: `/health`

**Response**:
```json
{
  "status": "healthy",
  "version": "0.5.0",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-02-19T01:23:45Z"
}
```

**Docker Health Checks**:
- Backend: HTTP check every 30s
- MongoDB: Ping check every 10s
- Redis: CLI ping every 10s

---

## Documentation

### Guides

- **[RAG Architecture](docs/RAG_ARCHITECTURE.md)** - Retrieval pipeline: hybrid search, adaptive chunking, contextual embeddings, knowledge graph, proposition indexing
- **[Architecture Tiers](docs/ARCHITECTURE_TIERS.md)** - Feature classification into Tier 1 (baseline), Tier 2 (quality), Tier 3 (research) with profile mapping
- **[Design Decisions](docs/DESIGN_DECISIONS.md)** - Rationale and tradeoffs for every major architectural choice
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions for AWS, MongoDB Atlas, and Vercel
- **[Architecture Documentation](docs/ARCHITECTURE.md)** - System design, technical decisions, and data flow
- **[Terraform README](infrastructure/terraform/README.md)** - Infrastructure as Code deployment guide

---

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite: `pytest tests/unit/ -v`
4. Ensure no new warnings or deprecations
5. Update documentation as needed
6. Submit pull request with clear description

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- **Frameworks**: LangChain, LangGraph, FastAPI, Next.js
- **Infrastructure**: AWS, Vercel, GitHub Actions
- **Inspiration**: The viral "granny mode" technique that sparked the multi-level explanation idea, addressing real challenges in academic learning

---

**Built with FastAPI, Next.js, LangChain, and deployed on AWS + Vercel**

*Transforming academic learning through AI-powered personalized assistance*