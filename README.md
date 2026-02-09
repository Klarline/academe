# 🎓 Academe - Academic AI Assistant

Built with LangGraph • Powered by Google Gemini • Production-Ready REST API

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.45-green.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-teal.svg)](https://fastapi.tiangolo.com/)

**Full-Stack Multi-Agent Learning System with Real-Time Streaming**

A production-ready AI assistant that helps students understand complex academic concepts through personalized, memory-adaptive responses. Features both CLI and REST API interfaces, real-time streaming, 5 specialized agents, RAG-powered document understanding, and intelligent memory that learns from your progress.

---

## Key Features

### Full-Stack Architecture
- **CLI Interface** - Rich terminal UI for local use
- **REST API** - 30 production-ready HTTP endpoints
- **⚡ Real-Time Streaming** - SSE and WebSocket support with token-by-token responses
- **JWT Authentication** - Secure token-based auth with refresh tokens
- **Interactive API Docs** - Auto-generated Swagger UI at `/docs`

### 5 Specialized AI Agents
- **Concept Explainer** - Adaptive explanations that adjust to your level and learning history
- **Code Helper** - Generates code with extra comments for concepts you struggle with
- **Research Agent** - Searches your documents with semantic search and provides citations
- **Practice Generator** - Auto-focuses practice questions on your weak areas
- **Router** - Intelligently routes queries to the most appropriate agent

### Intelligent Memory System
- **Tracks your learning** - Monitors which concepts you've studied and mastered
- **Detects weak areas** - Identifies topics where you struggle (< 60% accuracy)
- **Adapts responses** - Agents automatically adjust explanations based on your history
- **LLM-powered filtering** - Uses AI to identify which past concepts are relevant

### Production-Grade Technology
- **Real-time streaming** - LangGraph's astream_events API for true token-by-token delivery
- **Async processing** - Celery + Redis for non-blocking operations
- **Semantic search** - sentence-transformers for accurate document retrieval
- **RAG pipeline** - Upload PDFs and get context-aware answers with citations
- **Progress tracking** - Dashboard showing mastery levels and study analytics
- **WebSocket support** - Bidirectional chat with mid-stream cancellation

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (for MongoDB and Redis)
- ~2GB disk space

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/academe.git
cd academe

# 2. Create conda environment
conda create -n academe python=3.11
conda activate academe

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 5. Start services
docker-compose up -d  # MongoDB
docker run -d -p 6379:6379 redis  # Redis

# 6. Start Celery worker (Terminal 1)
./scripts/start_worker.sh
```

### Option A: Run CLI Interface
```bash
# Terminal 2
python src/cli/main.py
```

### Option B: Run REST API
```bash
# Terminal 2
./start_api.sh

# Open browser to:
# - API Docs: http://localhost:8000/docs
# - API: http://localhost:8000
```

---

## REST API

### Quick API Example

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","username":"test","password":"Test1234"}'

# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email_or_username":"test","password":"Test1234"}'

# Send chat message (batch)
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"What is PCA?","use_memory":true}'

# Stream chat message (real-time SSE)
curl -X POST http://localhost:8000/api/v1/chat/message/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain gradient descent","use_memory":true}'
```

### API Endpoints (30 total)

**Authentication (6 endpoints)**
- POST `/api/v1/auth/register` - Create account
- POST `/api/v1/auth/login` - Get JWT token
- POST `/api/v1/auth/refresh` - Refresh token
- POST `/api/v1/auth/change-password` - Update password
- POST `/api/v1/auth/logout` - Logout
- GET `/api/v1/auth/validate` - Validate token

**Users (4 endpoints)**
- GET `/api/v1/users/me` - Get profile
- PUT `/api/v1/users/me` - Update preferences
- GET `/api/v1/users/me/stats` - User statistics
- POST `/api/v1/users/me/complete-onboarding` - Complete setup

**Chat (6 endpoints)**
- POST `/api/v1/chat/message` - Send message (batch)
- POST `/api/v1/chat/message/stream` - Send message (SSE streaming)
- GET `/api/v1/chat/conversations` - List conversations
- GET `/api/v1/chat/conversations/{id}/messages` - Get messages
- POST `/api/v1/chat/conversations` - Create conversation
- DELETE `/api/v1/chat/conversations/{id}` - Delete conversation

**Documents (4 endpoints)**
- POST `/api/v1/documents/upload` - Upload PDF/TXT/MD
- GET `/api/v1/documents/` - List documents
- DELETE `/api/v1/documents/{id}` - Delete document
- POST `/api/v1/documents/search` - Semantic search

**Progress (5 endpoints)**
- GET `/api/v1/progress/dashboard` - Complete analytics
- GET `/api/v1/progress/concepts` - Concept progress
- GET `/api/v1/progress/sessions` - Study sessions
- POST `/api/v1/progress/practice/generate` - Generate questions
- GET `/api/v1/progress/weak-areas` - Identify weaknesses

**WebSocket (2 endpoints)**
- WS `/api/v1/ws/chat` - Real-time chat with cancellation
- WS `/api/v1/ws/notifications` - Push notifications

**System (3 endpoints)**
- GET `/health` - Health check
- GET `/` - API info
- GET `/docs` - Swagger UI

### Streaming Support

**Three streaming methods available:**

1. **Batch** - Complete response at once
2. **SSE (Server-Sent Events)** - One-way token streaming (~500ms to first token)
3. **WebSocket** - Bidirectional with mid-stream cancellation

### Interactive API Testing

Visit `http://localhost:8000/docs` for Swagger UI:
- Try all endpoints interactively
- Auto-generated documentation
- Request/response examples
- Authentication testing

**Postman Collection:** Import `Academe_API.postman_collection.json` for pre-configured requests

---

## Usage Examples

### CLI Usage

**Basic Chat:**
```
You: What is gradient descent?
AI: [Adapts explanation based on your level and learning history]
```

**Document Q&A:**
```
Upload: Murphy's PML Chapter 7
You: What does the author say about eigenvalues?
AI: [Searches your PDF, provides answer with page citations]
```

**Adaptive Practice:**
```
You: Generate practice questions on linear algebra
AI: [Auto-focuses on eigenvalues if that's your weak area]
   - Generates 5 questions from YOUR documents
   - MCQ with proper options A-D
   - Focuses on concepts you're struggling with
```

### API Usage

**Frontend Integration Example:**
```javascript
// Real-time streaming with EventSource
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/chat/message/stream',
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.chunk) {
    displayToken(data.chunk); // Show word-by-word
  }
};
```

**WebSocket with Cancellation:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat');

// Authenticate
ws.send(JSON.stringify({
  type: 'auth',
  token: YOUR_JWT_TOKEN
}));

// Send message
ws.send(JSON.stringify({
  type: 'message',
  content: 'What is PCA?'
}));

// Cancel mid-stream
ws.send(JSON.stringify({
  type: 'cancel'
}));
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────┐
│         Client Applications             │
│  (CLI, Web, Mobile, Third-party APIs)   │
└────────────┬────────────────────────────┘
             │
             ├─────────────┬──────────────┐
             │             │              │
         Terminal      REST API      WebSocket
             │             │              │
             v             v              v
┌────────────────────────────────────────────┐
│          Service Layer (Async)             │
│  ChatService, DocumentService              │
└────────────┬───────────────────────────────┘
             │
             v
┌────────────────────────────────────────────┐
│        Core Business Logic                 │
│                                            │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ LangGraph│  │ Memory   │  │   RAG   │ │
│  │ Workflow │  │ System   │  │Pipeline │ │
│  └──────────┘  └──────────┘  └─────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │     5 Specialized Agents             │ │
│  │  Router | Explainer | Code | etc.    │ │
│  └──────────────────────────────────────┘ │
└────────────┬───────────────────────────────┘
             │
             v
┌────────────────────────────────────────────┐
│         Data & Storage Layer               │
│  MongoDB | Pinecone | Redis | Files       │
└────────────────────────────────────────────┘
```

### Multi-Agent Workflow
```
User Query
    ↓
Document Check → Router (LLM-based routing)
    ↓
┌─────────┬─────────┬──────────┬──────────┐
│ Concept │  Code   │ Research │ Practice │
│Explainer│ Helper  │  Agent   │Generator │
└─────────┴─────────┴──────────┴──────────┘
    ↓
Memory Update (Celery - async)
    ↓
MongoDB (Progress tracking)
```

### Tech Stack
- **Orchestration:** LangGraph 0.2.45
- **LLM:** Google Gemini 2.5 Flash
- **API Framework:** FastAPI 0.115.5
- **Vector DB:** Pinecone (semantic search)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384 dims)
- **Database:** MongoDB 7.0
- **Task Queue:** Celery 5.3.4 + Redis 5.0.1
- **CLI:** Rich 13.7.0
- **Validation:** Pydantic 2.10.4
- **ASGI Server:** Uvicorn 0.32.0

---

## Project Metrics

### Code Statistics
- **Total Lines:** ~20,300 lines of production Python
- **Core Logic:** ~17,500 lines (agents, memory, RAG, database)
- **API Layer:** ~2,800 lines (30 endpoints, services, auth)
- **Test Coverage:** 7 comprehensive test files
- **Documentation:** ~5,000 lines across guides

### Performance
- **Time to first token:** 500ms-1s (streaming)
- **Batch response:** 2-5s (complete answer)
- **Document processing:** 2-3s per MB
- **Semantic search:** <200ms

### Features
- 5 specialized AI agents
- 30 REST + WebSocket endpoints
- Real-time streaming (SSE + WebSocket)
- JWT authentication
- RAG with Pinecone
- Async task processing
- Progress tracking & analytics
- Zero placeholders - all real implementations

---

## Testing

### API Testing

**Option 1: Swagger UI (Easiest)**
```bash
./start_api.sh
# Open http://localhost:8000/docs
# Click "Try it out" on any endpoint
```

**Option 2: Postman**
```bash
# Import the collection
# File: Academe_API.postman_collection.json
# Set environment variable: base_url = http://localhost:8000
```

**Option 3: curl**
```bash
# Health check
curl http://localhost:8000/health

# Full authentication + chat flow
# (See API_TESTING_GUIDE.md for complete examples)
```

### CLI Testing
```bash
# Run test suite
pytest tests/

# Test specific components
python tests/test_memory_integration.py
python tests/test_real_embeddings.py
python tests/test_workflow.py
```

---

## Project Structure

```
academe/
├── src/                     # All source code
│   ├── core/               # Business logic (agents, memory, RAG)
│   │   ├── agents/        # 5 AI agents
│   │   ├── auth/          # JWT authentication
│   │   ├── config/        # Settings and LLM setup
│   │   ├── database/      # MongoDB repositories
│   │   ├── documents/     # PDF processing & chunking
│   │   ├── evaluation/    # RAGAS framework
│   │   ├── graph/         # LangGraph workflow
│   │   ├── memory/        # Context management
│   │   ├── models/        # Pydantic models
│   │   ├── onboarding/    # User onboarding flow
│   │   ├── rag/           # RAG pipeline
│   │   ├── vectors/       # Embeddings & semantic search
│   │   ├── utils/         # Utility modules
│   │   ├── celery_config.py
│   │   └── tasks.py       # Background tasks
│   │
│   ├── cli/               # CLI interface
│   │   ├── interfaces/   # Rich UI components
│   │   └── main.py       # CLI entry point
│   │
│   └── api/               # REST API
│       ├── services/     # Service wrappers
│       │   ├── chat_service.py
│       │   └── document_service.py
│       ├── v1/
│       │   ├── endpoints/  # API routes
│       │   │   ├── auth.py
│       │   │   ├── users.py
│       │   │   ├── chat.py
│       │   │   ├── documents.py
│       │   │   ├── progress.py
│       │   │   └── websocket.py
│       │   ├── deps.py     # Dependencies (JWT)
│       │   └── api.py      # Router aggregator
│       └── main.py         # FastAPI app
│
├── tests/                  # Test suite
├── scripts/               # Helper scripts
│   └── start_worker.sh   # Celery worker startup
├── start_api.sh           # API startup script
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # MongoDB setup
└── .env.example          # Configuration template
```

---

## Use Cases

### For Students
- **Understand complex concepts** - Explanations adapted to your level
- **Study from your materials** - Upload textbooks, get personalized Q&A
- **Track your progress** - See mastery levels and weak areas
- **Practice effectively** - Auto-generated questions from your documents
- **Learn adaptively** - System remembers what you struggle with

### For Developers
- **Learn LangGraph** - Production multi-agent system implementation
- **Study RAG** - Complete pipeline from upload to semantic search
- **Understand streaming** - Real LangGraph astream_events implementation
- **See FastAPI patterns** - Professional 3-layer architecture
- **Explore async Python** - Celery task processing
- **Study authentication** - JWT with refresh tokens

### For Interviews
- **Full-stack portfolio piece** - CLI + REST API + real-time features
- **Production patterns** - Error handling, validation, logging
- **Scalable architecture** - Service layer, zero code duplication
- **Advanced features** - WebSocket, streaming, cancellation
- **Real implementations** - No placeholders or mock data

---

## Development

### Running Both Interfaces

**Terminal 1 - Services:**
```bash
docker-compose up -d  # MongoDB
docker run -d -p 6379:6379 redis
```

**Terminal 2 - Celery Worker:**
```bash
./scripts/start_worker.sh
```

**Terminal 3 - API Server:**
```bash
./start_api.sh
# API at http://localhost:8000
```

**Terminal 4 - CLI (Optional):**
```bash
python src/cli/main.py
# Rich terminal interface
```

### Adding New Features

**Add New Agent:**
1. Create agent in `src/core/agents/new_agent.py`
2. Add node in `src/core/graph/nodes.py`
3. Update router in `src/core/agents/router.py`
4. Add to workflow in `src/core/graph/workflow.py`
5. Expose via API in `src/api/v1/endpoints/`

**Add New API Endpoint:**
1. Add route in `src/api/v1/endpoints/your_module.py`
2. Create service wrapper if needed in `src/api/services/`
3. Register in `src/api/v1/api.py`
4. Test in Swagger UI

---

## Documentation

### API Documentation
- Swagger UI: `http://localhost:8000/docs` (when running)
- ReDoc: `http://localhost:8000/redoc` (alternative docs)
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Technical Highlights

### Architecture Decisions

**3-Layer Design:**
- **API Layer** - HTTP/WebSocket interfaces, validation, auth
- **Service Layer** - Async wrappers, business logic orchestration
- **Core Layer** - Multi-agent system, memory, RAG, database

**Benefits:**
- Zero code duplication (CLI and API share same core)
- Easy to add new interfaces (mobile, desktop, etc.)
- Testable in isolation
- Industry-standard pattern

### Real-Time Streaming

**Implementation:**
```python
# Uses LangGraph's astream_events API
async for event in workflow.astream_events(state, version="v2"):
    if event["event"] == "on_chat_model_stream":
        # Real tokens as LLM generates them!
        yield {"chunk": event["data"]["chunk"].content}
```

**Performance:**
- **Before:** 3-5 second wait → complete response
- **After:** 500ms to first token → progressive display
- **Result:** 3-5x better perceived performance

### Memory System

**Adaptive Response Example:**
```python
# User's history: eigenvalues (35% accuracy - weak area)

# System provides context-aware explanation:
"Since eigenvalues is still challenging, I'll explain 
gradient descent without assuming that knowledge..."

# vs. for proficient users:
"Like eigenvalues showing principal directions, 
gradient descent finds optimal directions..."
```

---

## Contributing

This is a personal portfolio project for internship applications, but feedback and suggestions are welcome!

**To provide feedback:**
1. Open an issue on GitHub
2. Email suggestions
3. Fork and submit PRs

---

## Acknowledgments

- LangChain Team for the excellent LangGraph framework
- Google for providing free-tier Gemini API access
- Machine Learning course that inspired this project
- The viral "granny mode" technique that sparked the multi-level explanation idea

---

**Built with ❤️ for learners who struggle with complex concepts - Production-ready full-stack AI for academic learning**