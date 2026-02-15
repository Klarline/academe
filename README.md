# 🎓 Academe - Academic AI Assistant with RAG and Multi-Agent System

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![LangChain](https://img.shields.io/badge/LangChain-0.3-blue)

A full-stack academic AI assistant that helps students understand complex academic concepts through retrieval-augmented generation (RAG), multi-agent orchestration, and personalized learning experiences.

## Overview

Academe addresses a critical challenge in education: understanding dense academic textbooks and research papers. The system combines RAG-based document search with general LLM knowledge to provide comprehensive, citable answers adapted to your learning preferences.

- **Document Mode**: When you have uploaded materials, answers come from your textbooks/papers with citations
- **General Knowledge Mode**: When documents don't cover the topic, uses LLM knowledge (configurable fallback behavior)

### Key Features

- **Full-Stack Application**: Complete REST API backend with Next.js frontend, CLI interface, and WebSocket streaming
- **Hybrid RAG System**: Answers from your documents with automatic fallback to general knowledge (user-configurable)
- **Multi-Agent Orchestration**: Specialized agents for concept explanation, code generation, document research, and practice problems
- **Personalized Learning**: Adaptive explanations based on learning level (beginner/intermediate/advanced) and preferred style
- **Progress Tracking**: Monitor concept mastery, identify weak areas, and receive targeted recommendations  
- **Citation Support**: All document-based answers include source attribution with page numbers
- **Multiple Interfaces**: FastAPI REST API with WebSocket support, and Rich-based CLI
- **Background Processing**: Celery-based async tasks for memory updates and document indexing

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 6.0+
- Redis 7.0+ (for background tasks)
- Pinecone account (optional, system works with mock mode)

### Quick Start (Recommended)
```bash
# 1. Clone and configure
git clone https://github.com/yourusername/academe.git
cd academe
cp .env.example .env
# Edit .env and add your API keys (GOOGLE_API_KEY, MONGODB_URI, JWT_SECRET_KEY)

# 2. Install dependencies
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# 3. Start services
docker-compose up -d              # Start MongoDB and Redis
./scripts/start_all.sh            # Start API + Frontend

# Optional: Start background worker in separate terminal
./scripts/start_worker.sh
```

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup (Advanced)

For more control over individual services:

**Backend**
```bash
cd backend

# Setup environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your configuration

# Start database
docker-compose up -d mongodb

# Run tests (optional)
pytest tests/unit/ -v

# Start API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Or run CLI
python3 cli/main.py
```

**Frontend**
```bash
cd frontend

npm install
cp .env.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000

# Development
npm run dev

# Production
npm run build && npm start
```

**Celery Worker (Optional)**
```bash
cd backend
celery -A core.celery_config worker --loglevel=info
```

## Architecture

### System Components

**Application Layer**
- LangGraph workflow orchestration for multi-agent coordination
- Five specialized agents: Router, Concept Explainer, Code Helper, Research Agent, Practice Generator
- State-based execution with conditional routing

**AI/ML Layer**
- RAG pipeline with document processing, chunking, and vector storage
- Semantic search using sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
- Pinecone vector database for scalable similarity search
- Multi-provider LLM support (Gemini 2.5 Flash, Claude Sonnet 4, GPT-4o)

**Data Layer**
- MongoDB for structured data (users, conversations, documents, progress)
- Filesystem storage for uploaded documents
- Redis for async task queue (Celery)

### Technology Stack

**Backend**
- Python 3.11+
- FastAPI (async REST API)
- LangChain + LangGraph (LLM orchestration)
- sentence-transformers (embeddings)
- PyMongo (database)
- Pydantic V2 (validation)
- Celery + Redis (background tasks)
- pytest (testing)

**Frontend**
- Next.js 14 (React framework)
- TypeScript (type safety)
- Redux Toolkit (state management)
- Tailwind CSS (styling)

**Infrastructure**
- MongoDB 6.0
- Pinecone (vector database)
- Redis (task queue)
- Docker Compose (local development)

## Technical Highlights

### RAG Implementation

The RAG system processes documents through a multi-stage pipeline:

1. **Document Processing**: Extract text from PDFs using PyPDF2, normalize formatting, detect content types (equations, code, tables)
2. **Adaptive Chunking**: Split documents using strategy based on type (textbooks: 1200 chars semantic, papers: 800 chars recursive, notes: 1000 chars recursive)
3. **Embedding Generation**: Convert chunks to 384-dimensional vectors using sentence-transformers with batch processing
4. **Vector Storage**: Index in Pinecone with metadata (page numbers, section titles, content flags)
5. **Semantic Search**: Cosine similarity search with optional reranking for improved precision
6. **Context Building**: Format retrieved chunks with source citations
7. **Generation**: LLM generates answer using context and user preferences

**Performance**: 1.85 second average response time, 100% success rate on test queries

### Multi-Agent System

Specialized agents handle different tasks:

- **Router Agent**: Analyzes queries using structured LLM output to route to appropriate agent
- **Concept Explainer**: Provides multi-level explanations from simple analogies (ELI5/"granny mode") to advanced mathematical rigor
- **Code Helper**: Generates code examples with RAG-enhanced search of user's documents for relevant code snippets
- **Research Agent**: Answers questions from uploaded documents with full citation support
- **Practice Generator**: Creates custom practice problems and quizzes based on studied concepts

LangGraph orchestrates workflow with state management, conditional routing, and memory integration.

### Background Task Processing

Celery workers handle async tasks:
- **Memory updates**: Process learning progress after each interaction
- **Document indexing**: Generate embeddings and vector database updates asynchronously
- **Progress tracking**: Update concept mastery and weak area detection
- **Task prioritization**: High-priority queue for memory, medium for documents

This keeps the API responsive while handling computationally expensive operations in the background.

## Performance Metrics

### Response Times
- Average query response: 1.85 seconds
- Document upload (100-page PDF): 15 seconds
- Embedding generation: 50ms per text
- Vector search: 200ms
- Success rate: 100% on test queries

### Scalability
- Current capacity: 50-100 concurrent requests per server
- Documents per user: 1000+
- Vector database: 1M+ vectors supported
- Tested with: 217 unit tests, 100% pass rate

## Project Structure

```
academe/
├── scripts/                   # Deployment and startup scripts
│   ├── start_all.sh           # Start backend + frontend together
│   ├── start_api.sh           # Start FastAPI server only
│   ├── start_frontend.sh      # Start Next.js only
│   └── start_worker.sh        # Start Celery worker for background tasks
├── backend/
│   ├── api/                   # FastAPI REST API
│   │   ├── main.py            # Application entry point
│   │   ├── v1/                # API version 1
│   │   │   ├── endpoints/     # Route handlers (auth, chat, documents, etc.)
│   │   │   └── deps.py        # Dependencies (authentication)
│   │   └── services/          # Business logic layer
│   ├── cli/                   # Command-line interface
│   │   ├── main.py            # CLI entry point
│   │   └── interfaces/        # UI components (Rich-based)
│   ├── core/                  # Core business logic
│   │   ├── agents/            # AI agents (5 specialized agents)
│   │   ├── auth/              # Authentication service (JWT, bcrypt)
│   │   ├── config/            # Configuration and settings
│   │   ├── database/          # MongoDB repositories
│   │   ├── documents/         # Document processing and chunking
│   │   ├── evaluation/        # RAGAS quality metrics
│   │   ├── graph/             # LangGraph workflow orchestration
│   │   ├── memory/            # Context and memory management
│   │   ├── models/            # Pydantic data models
│   │   ├── rag/               # RAG pipeline implementation
│   │   ├── utils/             # Utility functions
│   │   ├── vectors/           # Embeddings and semantic search
│   │   ├── celery_config.py   # Celery task queue configuration
│   │   └── tasks.py           # Background task definitions
│   ├── tests/                 # Test suite
│   │   ├── unit/              # Unit tests (217 tests)
│   │       ├── agents/        # Agent tests (5 test files)
│   │       ├── test_auth_service.py
│   │       ├── test_config.py
│   │       ├── test_database.py
│   │       ├── test_models.py
│   │       ├── test_documents.py
│   │       ├── test_graph.py
│   │       └── test_vectors.py
│   ├── run_ragas_simple.py    # RAGAS evaluation script
│   └── requirements.txt       # Python dependencies
│   └── .env.example           # Environment configuration template
├── frontend/
│   ├── app/                   # Next.js app router
│   ├── components/            # React components
│   ├── hooks/                 # Custom React hooks
│   ├── store/                 # Redux state management
│   ├── lib/                   # Utilities and constants
│   └── types/                 # TypeScript definitions
├── document_storage/          # Uploaded document files (organized by user_id)
├── docker-compose.yml         # Service orchestration (MongoDB, Redis)
└── README.md                  # This file
```

## Usage Examples

### CLI Usage

```bash
# Start CLI
python3 backend/cli/main.py

# Register or login
> register
Email: student@university.edu
Username: student
Password: ********

# Upload a document
> upload
File path: /path/to/ml_textbook.pdf
Title: Machine Learning Textbook Chapter 3

# Ask questions
> ask
Question: What is principal component analysis?

# Get practice problems
> practice
Topic: Linear Algebra
Difficulty: Intermediate
```

### API Usage

```python
import requests

# Register
response = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "student@university.edu",
    "username": "student",
    "password": "SecurePass123"
})

token = response.json()["access_token"]

# Upload document
files = {"file": open("textbook.pdf", "rb")}
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/api/v1/documents/upload",
    files=files,
    headers=headers
)

# Ask question
response = requests.post(
    "http://localhost:8000/api/v1/chat/message",
    json={"question": "What is PCA?", "conversation_id": "conv_123"},
    headers=headers
)

answer = response.json()["response"]
sources = response.json()["sources"]
```

### WebSocket Streaming

```javascript
const ws = new WebSocket("ws://localhost:8000/api/v1/ws/chat?token=" + token);

ws.send(JSON.stringify({
    question: "Explain gradient descent",
    conversation_id: "conv_123"
}));

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "token") {
        console.log(data.content);  // Stream tokens as they arrive
    }
};
```

## Configuration

### Environment Variables

**Backend (.env)**
```bash
# LLM Configuration
LLM_PROVIDER=openai                    # Options: gemini, claude, openai
OPENAI_API_KEY=your_key_here           # Required for openai

# Database
MONGODB_URI=mongodb://admin:password@localhost:27017/
MONGODB_DB_NAME=academe

# Security
JWT_SECRET_KEY=your_secure_random_key  # Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Background Tasks (Optional)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Logging
LOG_LEVEL=INFO
```

**Frontend (.env.local)**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Development

### Running Tests

```bash
cd backend

# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_auth_service.py -v

# Run with coverage
pytest tests/unit/ --cov=core --cov-report=html

# Expected: 217 passed, 2 skipped, 2 warnings
```

### Code Quality

```bash
# Syntax validation
python3 -m py_compile core/**/*.py

# Type checking (if mypy installed)
mypy core/

# Linting (if pylint installed)
pylint core/
```

### Running Evaluation

```bash
# Start MongoDB
docker-compose up -d mongodb

# Run RAGAS evaluation
cd backend
python3 run_ragas_simple.py

# Expected output: Quality metrics and recommendations
```

## Testing and Quality

### Test Coverage

217 comprehensive unit tests covering:
- Authentication and security (44 tests)
- Configuration management (21 tests)
- Database operations (22 tests)
- Data models and validation (23 tests)
- All five agents (57 tests across specialized test files)
- Document processing (19 tests)
- LangGraph workflow (12 tests)
- Vector operations (19 tests)

Test suite runs in 50 seconds with 100% pass rate.

### Quality Evaluation

RAGAS evaluation framework implemented for measuring:
- Faithfulness (answer grounding in source documents)
- Answer relevancy (how well answers address questions)
- Context recall (retrieval effectiveness)
- Context precision (retrieval accuracy)

Test dataset includes 20 questions covering linear algebra, probability, neural networks, optimization, and other ML topics.

## Performance Characteristics

### Response Time Breakdown

Typical query: 2.96 seconds total
- Check documents: 50ms (2%)
- Routing decision: 300ms (12%)
- Query embedding: 100ms (4%)
- Vector search: 200ms (8%)
- Reranking (optional): 300ms (12%)
- Context building: 10ms (0%)
- LLM generation: 2000ms (62%)

Bottleneck: LLM generation (addressed via streaming for better UX)

### Scalability

Current capacity (single server):
- 50-100 concurrent requests
- 20-50 requests per second
- 1000+ documents per user
- 1M+ vectors in Pinecone

Scaling strategy:
- Horizontal API scaling with load balancer
- MongoDB replica set for read scaling
- Redis caching for repeated queries
- Async/await already implemented

## Security

### Authentication
- bcrypt password hashing with automatic salt generation
- JWT tokens with 24-hour expiration
- HS256 algorithm for token signing
- Secure secret key validation (32+ characters required, default rejected)

### Authorization
- Dependency injection for user verification on all protected endpoints
- Row-level security (users only access their own data)
- MongoDB credentials required from environment (not hard-coded)

### Identified Areas for Improvement
- Rate limiting needed (recommended: 100 requests/hour per IP)
- Timing attack vulnerability in login (should use constant-time comparison)
- Token revocation mechanism for logout (recommended: Redis blacklist)

## API Documentation

Once the server is running, access interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

**Authentication**
- `POST /api/v1/auth/register` - Create new account
- `POST /api/v1/auth/login` - Login and receive JWT token
- `POST /api/v1/auth/logout` - Logout

**Chat**
- `POST /api/v1/chat/message` - Send question and receive answer
- `GET /api/v1/chat/conversations` - List user's conversations
- `WS /api/v1/ws/chat` - WebSocket for streaming responses

**Documents**
- `POST /api/v1/documents/upload` - Upload PDF, text, or markdown file
- `GET /api/v1/documents/` - List user's documents
- `DELETE /api/v1/documents/{id}` - Delete document and associated vectors

**Progress**
- `GET /api/v1/progress/` - Get learning progress and concept mastery
- `POST /api/v1/progress/update` - Track concept interaction

## Design Patterns

### Implemented Patterns

- **Factory Pattern**: Document processors, LLM instantiation
- **Singleton Pattern**: Database connection, shared agents, settings
- **Repository Pattern**: All database access abstraction
- **Strategy Pattern**: Multiple chunking strategies
- **Dependency Injection**: Service composition and testing

### Key Architectural Choices

**Shared Resources**: RAG pipeline and agents instantiated once and reused to avoid expensive reloading (2-3 second initialization cost eliminated)

**Async/Await**: All API endpoints use async for non-blocking I/O, enabling 10x higher throughput during LLM calls

**State Management**: LangGraph's TypedDict state passes cleanly between nodes without manual tracking

**Error Handling**: Try-catch blocks throughout with graceful fallbacks and user-friendly error messages

## Deployment

### Production Considerations

**Before deploying to production:**

1. **Security**
   - Configure CORS to restrict allowed origins (currently set to `*`)
   - Implement rate limiting (recommended: slowapi middleware)
   - Set `LOG_LEVEL=INFO` (not DEBUG)
   - Use strong JWT secret (32+ characters)
   - Enable HTTPS/TLS

2. **Monitoring**
   - Add application monitoring (Prometheus/Grafana)
   - Set up error tracking (Sentry)
   - Configure log aggregation
   - Monitor LLM API usage and costs

3. **Database**
   - Enable MongoDB authentication
   - Configure replica set for high availability
   - Set up automated backups
   - Add connection pooling limits

4. **Scaling**
   - Deploy multiple API servers behind load balancer
   - Use Redis for session storage and caching
   - Configure CDN for frontend assets
   - Consider managed Pinecone for production

### Docker Deployment

```bash
# Build services
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite: `pytest tests/unit/ -v`
4. Ensure no new warnings or deprecations
5. Update documentation as needed
6. Submit pull request with clear description

## Acknowledgments

- LangChain Team for the excellent LangGraph framework
- Machine Learning course that inspired this project
- The viral "granny mode" technique that sparked the multi-level explanation idea

### Technologies Used

- LangChain and LangGraph for LLM orchestration
- sentence-transformers for semantic embeddings
- Pinecone for vector similarity search
- FastAPI for modern async API development
- MongoDB for flexible document storage
- RAGAS for quality evaluation

### Technical Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [RAGAS Framework](https://docs.ragas.io/)
- [sentence-transformers](https://www.sbert.net/)
- [FastAPI](https://fastapi.tiangolo.com/)

---

**Built with ❤️ for learners who struggle with complex concepts - full-stack academic AI assistant with RAG, multi-agent orchestration, and comprehensive testing. Built for scalability, maintainability, and quality.**