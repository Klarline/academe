# 🎓 Academe - Multi-Agent Academic AI Assistant

A production-grade, full-stack AI application that transforms how students interact with dense academic materials through Retrieval-Augmented Generation (RAG), multi-agent orchestration, and adaptive learning.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
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
- [Future Enhancements](#future-enhancements)

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

### Hybrid RAG Pipeline

- **Document Mode**: Answers drawn from uploaded materials with source citations
- **Knowledge Mode**: Falls back to LLM general knowledge when documents don't cover the topic
- **Configurable Behavior**: User can control fallback preferences

### Personalized Learning

- **Adaptive Difficulty**: Automatically adjusts explanation complexity
- **Progress Tracking**: Monitors concept mastery across topics
- **Weak Area Identification**: Recommends review materials based on quiz performance
- **Learning Style Support**: Visual, code-based, or theoretical explanations

### Production-Ready Features

- **Real-Time Streaming**: WebSocket support for token-by-token responses
- **Async Processing**: Celery background workers for document indexing
- **Health Monitoring**: Prometheus metrics and automated health checks
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
│  │           LangGraph Multi-Agent System                 │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │ │
│  │  │  Router  │→ │ Concept  │  │   Code   │              │ │
│  │  │  Agent   │  │Explainer │  │  Helper  │              │ │
│  │  └──────────┘  └──────────┘  └──────────┘              │ │
│  │  ┌──────────┐  ┌──────────┐                            │ │
│  │  │ Research │  │ Practice │                            │ │
│  │  │  Agent   │  │Generator │                            │ │
│  │  └──────────┘  └──────────┘                            │ │
│  └────────────────────────────────────────────────────────┘ │
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
User Query → Router → [Agent Selection] → RAG Search → Generate Response
                ↓                              ↓
         [Code Helper]                   [Vector DB]
         [Concept Explainer]             [Document Chunks]
         [Research Agent]                [Reranking]
         [Practice Generator]                 ↓
                ↓                         [Top K Results]
           [Response]  ←──────────────  [Context + LLM]
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
| **Embeddings** | Sentence-Transformers | Document vectorization |
| **LLM Provider** | Google Gemini 2.0 Flash | Primary language model |

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
| **Monitoring** | Prometheus | Metrics collection and health checks |
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
# - GOOGLE_API_KEY (required)
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

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

# View logs
docker-compose logs -f backend

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
- 217 unit tests across all modules
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

**Agent Workflow**:
1. **Router Agent** analyzes user intent and query type
2. Routes to specialist agent based on classification:
   - Conceptual questions → **Concept Explainer**
   - Code-related → **Code Helper**
   - Multi-source research → **Research Agent**
   - Practice/assessment → **Practice Generator**
3. Specialist agent processes query with RAG context
4. Response formatted and streamed to user

**State Management**:
```python
class AgentState(TypedDict):
    messages: list[BaseMessage]
    current_agent: str
    context: dict
    user_preferences: dict
    conversation_history: list
```

### RAG Pipeline Implementation

**Document Processing**:
1. **Upload** → PDF/DOCX parsing with PyPDF2/python-docx
2. **Chunking** → Semantic chunking with overlap (500 tokens, 50 overlap)
3. **Embedding** → Sentence-transformers (all-MiniLM-L6-v2)
4. **Storage** → Pinecone vector database with metadata

**Retrieval**:
1. **Query Embedding** → Convert user query to vector
2. **Semantic Search** → Top-K similarity search (K=5-10)
3. **Reranking** → Optional reranking for precision
4. **Context Assembly** → Format chunks with citations

**Generation**:
1. **Prompt Engineering** → Include retrieved context + system instructions
2. **LLM Inference** → Google Gemini 2.0 Flash (default)
3. **Streaming** → Token-by-token response via WebSocket
4. **Citation Extraction** → Parse and format source references

### Database Schema

**MongoDB Collections**:
- `users`: User accounts, preferences, learning profiles
- `conversations`: Chat history with agent metadata
- `documents`: Uploaded materials with processing status
- `chunks`: Document chunks with embeddings metadata
- `practice_sessions`: Quiz attempts and performance data
- `progress`: Concept mastery tracking per user

**Pinecone Index**:
- Dimensions: 384 (sentence-transformers model output)
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

**Chunking Strategy**:
- **Semantic Chunking**: Preserves context within chunks
- **Chunk Size**: 500 tokens (optimal for retrieval vs context window)
- **Overlap**: 50 tokens to prevent information loss at boundaries
- **Metadata Preservation**: Page numbers, section headings, document titles

**Hybrid Search** (Planned):
- BM25 for keyword matching
- Vector similarity for semantic search
- Reciprocal Rank Fusion for result combination

**Evaluation Framework** (RAGAS):
- Context Precision: How relevant are retrieved chunks
- Context Recall: Coverage of relevant information
- Faithfulness: Answer grounded in context
- Answer Relevancy: Response addresses query

---

## Project Structure

```
academe/
├── docs/                      # Technical documentation
│   ├── ARCHITECTURE.md        # System design and architecture
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
│   │   │   ├── endpoints/     # Route handlers (auth, chat, documents)
│   │   │   └── deps.py        # Dependencies (authentication)
│   │   └── services/          # Business logic layer
│   ├── core/                  # Core business logic
│   │   ├── agents/            # 5 specialized AI agents
│   │   ├── auth/              # JWT authentication service
│   │   ├── config/            # Configuration management
│   │   ├── database/          # MongoDB repositories
│   │   ├── documents/         # Document processing & chunking
│   │   ├── evaluation/        # RAGAS quality metrics
│   │   ├── graph/             # LangGraph workflow orchestration
│   │   ├── memory/            # Adaptive context management
│   │   ├── models/            # Pydantic data models
│   │   ├── rag/               # RAG pipeline implementation
│   │   ├── vectors/           # Embeddings & semantic search
│   │   ├── celery_config.py   # Task queue configuration
│   │   └── tasks.py           # Background job definitions
│   ├── tests/                 # Comprehensive test suite
│   │   └── unit/              # 217+ unit tests
│   │       ├── agents/        # Agent behavior tests
│   │       ├── test_auth_service.py
│   │       ├── test_database.py
│   │       ├── test_documents.py
│   │       └── test_graph.py
│   ├── requirements.txt       # Python dependencies
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

---

## Configuration

### Environment Variables

**Backend** (`backend/.env`):

```bash
# Required
GOOGLE_API_KEY=your_google_api_key              # Google Gemini API
MONGODB_URI=mongodb://localhost:27017           # MongoDB connection
JWT_SECRET_KEY=your_32_char_minimum_secret      # JWT signing key

# Optional - Vector Database
PINECONE_API_KEY=your_pinecone_key             # Pinecone API (uses mock if not set)
PINECONE_INDEX_NAME=academe-prod               # Pinecone index name

# Optional - Alternative LLM Providers
ANTHROPIC_API_KEY=your_claude_key              # Claude API
OPENAI_API_KEY=your_openai_key                 # OpenAI API
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

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions for AWS, MongoDB Atlas, and Vercel
- **[Architecture Documentation](docs/ARCHITECTURE.md)** - System design, technical decisions, and data flow
- **[Terraform README](terraform/README.md)** - Infrastructure as Code deployment guide

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