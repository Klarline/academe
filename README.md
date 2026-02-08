# 🎓 Academe - Academic AI Assistant

Built with LangGraph • Powered by Google Gemini

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.45-green.svg)](https://github.com/langchain-ai/langgraph)

**Multi-Agent Learning System with Adaptive Explanations**

A production-grade AI assistant that helps students understand complex academic concepts through personalized, memory-adaptive responses. Built with LangGraph, featuring 5 specialized agents, RAG-powered document understanding, and intelligent memory that learns from your progress.

---

## 🌟 Key Features

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

### Production-Grade Architecture
- **Async processing** - Celery + Redis for non-blocking operations (20% faster)
- **Real semantic search** - sentence-transformers for accurate document retrieval
- **RAG pipeline** - Upload PDFs and get context-aware answers with citations
- **Progress tracking** - Dashboard showing mastery levels and study analytics

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker (for MongoDB and Redis)
- ~2GB disk space

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Klarline/academe.git
cd academe

# 2. Create conda environment
conda create -n academe python=3.11
conda activate academe

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 5. Start services
docker-compose up -d  # MongoDB
docker run -d -p 6379:6379 redis  # Redis for Celery

# 6. Start Celery worker (new terminal)
./scripts/start_worker.sh

# 7. Run the app
python main.py
```

---

## 📖 Usage Examples

### Basic Chat
```
You: What is gradient descent?
AI: [Adapts explanation based on your level and learning history]
```

### Document Q&A
```
Upload: Murphy's PML Chapter 7
You: What does the author say about eigenvalues?
AI: [Searches your PDF, provides answer with page citations]
```

### Adaptive Practice
```
You: Generate practice questions on linear algebra
AI: [Auto-focuses on eigenvalues if that's your weak area]
   - Generates 5 questions
   - MCQ with proper options A-D
   - Focuses on concepts you're struggling with
```

### Memory-Aware Responses
```
[You previously struggled with eigenvalues - 35% accuracy]

You: Explain gradient descent
AI: "Remember how we discussed eigenvalues showing main directions? 
     Gradient descent is similar, but simpler. Since eigenvalues is 
     still challenging, I'll explain without assuming that knowledge..."
```

---

## 🏗️ Architecture

### Multi-Agent System
```
User Query
    ↓
Router (LLM-based)
    ↓
┌─────────┬─────────┬──────────┬──────────┐
│ Concept │  Code   │ Research │ Practice │
│Explainer│ Helper  │  Agent   │Generator │
└─────────┴─────────┴──────────┴──────────┘
    ↓
Memory Update (Celery - background)
    ↓
MongoDB (Progress tracking)
```

### Tech Stack
- **Orchestration:** LangGraph 0.2.45
- **LLM:** Google Gemini 2.5 Flash
- **Vector DB:** Pinecone
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384d)
- **Database:** MongoDB 7.0
- **Task Queue:** Celery 5.3.4 + Redis 5.0.1
- **CLI:** Rich 13.7.0
- **Validation:** Pydantic 2.10.4

---

## 📊 Project Status

### Current Capabilities
- 5 specialized AI agents (3 memory-adaptive)
- Real semantic search with embeddings
- Intelligent memory system with LLM filtering
- Production-grade async processing (Celery + Redis)
- Progress tracking and weak area detection
- ~17,500 lines of production Python code

---

## 🧪 Testing

```bash
# Test memory integration
python tests/test_memory_integration.py

# Test real embeddings
python tests/test_real_embeddings.py

# Run full test suite
pytest tests/
```

---

## 📁 Project Structure

```
academe/
├── academe/              # Main source code
│   ├── agents/          # 5 AI agents
│   ├── auth/            # JWT authentication
│   ├── cli/             # Rich terminal interface
│   ├── config/          # Settings and LLM setup
│   ├── database/        # MongoDB repositories
│   ├── documents/       # PDF processing
│   ├── evaluation/      # RAGAS framework
│   ├── graph/           # LangGraph workflow
│   ├── memory/          # Context management
│   ├── models/          # Pydantic models
│   ├── onboarding/      # User onboarding flow
│   ├── rag/             # RAG pipeline
│   ├── vectors/         # Embeddings & search
│   ├── utils/           # Utility modules
│   ├── celery_config.py # Celery setup
│   ├── tasks.py         # Background tasks
├── scripts/            # Helper scripts
│   └── start_worker.sh # Start Celery worker
├── tests/              # Test suite
├── main.py             # Entry point
├── requirements.txt    # Dependencies
├── docker-compose.yml  # MongoDB setup
└── .env.example        # Configuration template
```

---

## 🎯 Use Cases

### For CS/ML Students
- Understand complex papers and textbooks
- Get explanations adapted to your level
- Generate practice problems
- Track learning progress

### For Developers
- Learn LangGraph and multi-agent systems
- Study production RAG implementation
- Understand async task processing with Celery
- See Pydantic structured outputs in action

---

## 🔧 Development

### Running Locally

**Terminal 1 - Services:**
```bash
docker-compose up -d  # MongoDB
docker run -d -p 6379:6379 redis  # Redis
```

**Terminal 2 - Celery Worker:**
```bash
./scripts/start_worker.sh
```

**Terminal 3 - Application:**
```bash
python main.py
```

### Adding New Agents
1. Create agent in `academe/agents/your_agent.py`
2. Add node function in `academe/graph/nodes.py`
3. Update router in `academe/agents/router.py`
4. Add to workflow in `academe/graph/workflow.py`

---

## 🔮 Future Enhancements

- FastAPI REST API backend
- Next.js/React frontend
- WebSocket streaming responses
- Multi-modal support (LaTeX, diagrams)
- Fine-tuned models for academic language
- Collaborative learning features
- Cloud deployment (AWS/GCP)

---

## 🤝 Contributing

This is a personal portfolio project, but feedback and suggestions are welcome!

---

## 🙏 Acknowledgments

- LangChain Team for the excellent LangGraph framework
- Google for providing free-tier Gemini API access
- Machine Learning course that inspired this project
- The viral "granny mode" technique that sparked the multi-level explanation idea

---

**Built with ❤️ for learners who struggle with complex concepts**