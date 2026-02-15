"""
Agents Module - Multi-agent system for Academe.

This module contains specialized agents for different educational tasks:
- Router: Routes queries to appropriate agents
- Concept Explainer: Provides multi-level concept explanations
- Code Helper: Generates code examples and implementations
- Practice Generator: Creates practice problems and exercises
- Research Agent: RAG-powered document Q&A with citations
"""

# Router Agent
from .router import (
    route_query,
    route_query_structured,
    route_query_keyword,
    route_query_with_context,
    get_agent_description,
    RouterDecision,
)

# Concept Explainer Agent
from .concept_explainer import (
    ConceptExplainer,
    explain_concept_streaming,
)

# Code Helper Agent
from .code_helper import (
    CodeHelper,
    generate_code_streaming,
)

# Practice Generator Agent
from .practice_generator import PracticeGenerator

# Research Agent
from .research_agent import (
    ResearchAgent,
    create_research_agent,
    research_streaming,
)

__all__ = [
    # Router
    "route_query",
    "route_query_structured",
    "route_query_keyword",
    "route_query_with_context",
    "get_agent_description",
    "RouterDecision",
    # Concept Explainer
    "ConceptExplainer",
    "explain_concept_streaming",
    # Code Helper
    "CodeHelper",
    "generate_code_streaming",
    # Practice Generator
    "PracticeGenerator",
    # Research Agent
    "ResearchAgent",
    "create_research_agent",
    "research_streaming",
]
