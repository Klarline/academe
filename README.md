# 🎓 Academe

> Multi-Agent AI Assistant that adapts machine learning explanations to your level

Built with LangGraph • Powered by Google Gemini

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.45-green.svg)](https://github.com/langchain-ai/langgraph)

---

## 🌟 What Makes Academe Special?

**The Problem:** Academic papers and textbooks are often too complex for students to understand. Even when using ChatGPT, explanations can still be overly technical or frustratingly vague.

**The Insight:** The internet discovered that prompting LLMs with "explain this like I'm a 70-year-old granny" produces surprisingly better explanations. This reveals a gap: **LLMs CAN simplify complex concepts, but they need the right framing.**

**Academe's Solution:** A multi-agent system that automatically provides **adaptive, multi-level explanations**:

- 🎈 **Intuitive Level**: Simple analogies, everyday language, zero jargon
- 🔬 **Technical Level**: Full mathematical rigor, formulas, graduate-level detail

Both explanations are accurate—just presented differently. It's like having a patient tutor who can explain the same concept multiple ways until it clicks.

---

## 🏗️ Architecture
```
User Query
    ↓
Router Agent (keyword-based classification)
    ↓
    ├─→ Concept Explainer Agent → Multi-level explanations
    │   (Intuitive + Technical)
    │
    └─→ Code Helper Agent → Educational Python code
        (Implementation + Examples + Explanations)
```

### The Three Specialized Agents

1. **Router Agent** 🧭
   - Analyzes queries to determine intent
   - Routes to appropriate specialist agent
   - Uses keyword matching (v0.1) with LLM fallback option

2. **Concept Explainer Agent** 💡 ⭐
   - **This is Academe's key innovation!**
   - Explains concepts at two levels simultaneously:
     - Intuitive: "Granny mode" - pure intuition, no math
     - Technical: Full rigor with mathematical notation
   - Inspired by the viral "granny mode" prompting technique

3. **Code Helper Agent** 💻
   - Generates clean, educational Python implementations
   - Includes detailed comments and docstrings
   - Provides usage examples and step-by-step explanations
   - Focuses on NumPy for mathematical operations

---

## ✨ Features

- 🎯 **Intelligent Routing**: Automatically determines whether you want explanations or code
- 📊 **Multi-Level Explanations**: Same concept explained intuitively AND technically
- 💻 **Educational Code**: Production-quality implementations with teaching focus
- 🔄 **LangGraph Orchestration**: Professional multi-agent coordination
- 🧪 **Fully Tested**: Comprehensive test suite with pytest
- 🎨 **Clean CLI**: Beautiful command-line interface

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Conda (recommended) or venv
- Google Gemini API key ([Get one free](https://aistudio.google.com/apikey))

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/academe.git
cd academe

# Create conda environment
conda create -n academe python=3.11
conda activate academe

# Install dependencies
pip install -r requirements.txt

# Install in editable mode
pip install -e .

# Set up environment variables
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
```

### Configuration

Edit `.env`:
```bash
# LLM Configuration
LLM_PROVIDER=gemini

# API Keys
GOOGLE_API_KEY=your_key_here

# App Settings
LOG_LEVEL=INFO
```

### Usage

**Interactive Mode:**
```bash
python main.py
```

**Demo Mode:**
```bash
python main.py demo
```

**Get Help:**
```bash
python main.py help
```

---

## 💡 Usage Examples

### Example 1: Concept Explanation

**Input:**
```
🤔 Your question: What is gradient descent?
```

**Output:**
```
## Intuitive Explanation 🎈

Imagine you're blindfolded on a hilly landscape, trying to find 
the lowest valley. You feel around with your feet—if you detect 
a downward slope, you take a small step in that direction...

## Technical Explanation 🔬

Gradient Descent is an iterative first-order optimization algorithm 
used to minimize a differentiable objective function J(w).

The update rule: w_{t+1} = w_t - α∇J(w_t)

Where α is the learning rate and ∇J(w_t) is the gradient...

## Key Takeaway 💡

Gradient descent finds function minima by iteratively moving in 
the direction of steepest descent.
```

### Example 2: Code Generation

**Input:**
```
🤔 Your question: Implement gradient descent in NumPy
```

**Output:**
Overview 📋
Implementation of gradient descent optimization in NumPy for
linear regression...
Implementation 💻
pythonimport numpy as np

def gradient_descent(X, y, learning_rate=0.01, num_iterations=1000):
    """
    Performs gradient descent to optimize linear regression parameters.
    
    Args:
        X: Input features
        y: Target values
        learning_rate: Step size for updates
        num_iterations: Number of optimization steps
    """
    # [Complete working code with detailed comments]
```

## Usage Example 🚀
[Working example with sample data]

## How It Works 🔍
[Step-by-step explanation]
```

---

## 🧪 Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run fast tests only (skip LLM calls)
python -m pytest tests/ -v -m "not slow"

# Run with coverage
python -m pytest tests/ --cov=academe --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_router.py -v
```

---

## 📂 Project Structure
```
academe/
├── academe/                    # Main package
│   ├── __init__.py
│   ├── config/                # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py        # Environment settings
│   │   └── llm_config.py      # LLM factory (supports multiple providers)
│   ├── agents/                # Specialized agents
│   │   ├── __init__.py
│   │   ├── router.py          # Routes queries to agents
│   │   ├── concept_explainer.py  # Multi-level explanations
│   │   └── code_helper.py     # Code generation
│   └── graph/                 # LangGraph workflow
│       ├── __init__.py
│       ├── state.py           # State definition
│       ├── nodes.py           # Node functions
│       └── workflow.py        # Workflow graph
├── tests/                     # Test suite
│   ├── test_router.py
│   ├── test_concept_explainer.py
│   ├── test_code_helper.py
│   └── test_workflow.py
├── main.py                    # CLI application
├── demo.py                    # Interactive demo
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
├── pytest.ini                 # Test configuration
├── .env                       # Environment variables (gitignored)
├── .gitignore
└── README.md
```

---

## 🛠️ Technology Stack

**Core Framework:**
- [LangGraph 0.2.45](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [LangChain 0.3.7](https://github.com/langchain-ai/langchain) - LLM integration

**LLM Provider:**
- [Google Gemini 2.5 Flash](https://ai.google.dev/) - Fast, free-tier model

**Development:**
- Python 3.11+
- [pytest](https://pytest.org/) - Testing framework
- [Pydantic](https://docs.pydantic.dev/) - Settings validation

---

## 🎓 What I Learned Building This

### Technical Skills

- **Multi-Agent Architectures**: Designed and implemented a production-ready multi-agent system with specialized agents and intelligent routing
- **LangGraph Workflows**: Mastered state management, conditional edges, and node orchestration
- **Prompt Engineering**: Developed sophisticated prompts for multi-level adaptive explanations
- **Software Design**: Applied factory pattern for LLM abstraction, making the system provider-agnostic

### Key Design Decisions

1. **Why Multi-Agent vs Single LLM?**
   - Specialized agents are better at their specific tasks
   - Easier to optimize and debug individual components
   - More modular and maintainable architecture

2. **Why Keyword Routing (v0.1)?**
   - Fast and free (no additional LLM call)
   - Accurate enough for common cases
   - Can upgrade to LLM-based routing in v1.0 for better accuracy

3. **Why Multi-Level Explanations?**
   - Real problem: Academic content is often inaccessibly complex
   - Inspired by "granny mode" viral technique
   - Both levels maintain accuracy while serving different audiences

### Challenges Overcome

- **LLM Provider Selection**: Initially tried multiple Gemini models before finding the right one (gemini-2.5-flash)
- **Import Path Issues**: Learned about Python package structure and editable installs
- **State Design**: Balanced simplicity (TypedDict) with functionality

---

## 🙏 Acknowledgments

- **LangChain Team** for the excellent LangGraph framework
- **Google** for providing free-tier Gemini API access
- **Northeastern University** for the CS6140 Machine Learning course that inspired this project
- The viral "granny mode" technique that sparked the multi-level explanation idea

---

**Built with ❤️ for learners who struggle with complex concepts**
