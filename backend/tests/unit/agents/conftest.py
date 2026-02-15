"""
Shared test fixtures for agent tests.

Provides common mocks and sample data for testing agents.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.models import UserProfile, LearningLevel, ExplanationStyle, LearningGoal


@pytest.fixture
def sample_user():
    """Sample user profile for testing."""
    return UserProfile(
        id="test_user_123",
        email="test@academe.ai",
        username="test_user",
        password_hash="hashed_password_123",
        learning_level=LearningLevel.INTERMEDIATE,
        explanation_style=ExplanationStyle.BALANCED,
        learning_goal=LearningGoal.DEEP_LEARNING,
        include_math_formulas=True,
        include_visualizations=True,
        preferred_code_language="python"
    )


@pytest.fixture
def beginner_user():
    """Beginner-level user profile."""
    return UserProfile(
        id="beginner_123",
        email="beginner@academe.ai",
        username="beginner_user",
        password_hash="hashed_password_456",
        learning_level=LearningLevel.BEGINNER,
        explanation_style=ExplanationStyle.INTUITIVE,
        learning_goal=LearningGoal.QUICK_REVIEW,
        include_math_formulas=False,
        include_visualizations=True,
        preferred_code_language="python"
    )


@pytest.fixture
def advanced_user():
    """Advanced-level user profile."""
    return UserProfile(
        id="advanced_123",
        email="advanced@academe.ai",
        username="advanced_user",
        password_hash="hashed_password_789",
        learning_level=LearningLevel.ADVANCED,
        explanation_style=ExplanationStyle.TECHNICAL,
        learning_goal=LearningGoal.RESEARCH,
        include_math_formulas=True,
        include_visualizations=False,
        preferred_code_language="python"
    )


@pytest.fixture
def mock_rag_pipeline():
    """Mock RAG pipeline that returns empty results."""
    mock = Mock()
    mock.query_with_context.return_value = ("", [])
    return mock


@pytest.fixture
def mock_rag_pipeline_with_sources():
    """Mock RAG pipeline that returns sources."""
    mock = Mock()
    
    # Create mock source
    mock_source = Mock()
    mock_source.document.title = "Machine Learning Textbook"
    mock_source.document.original_filename = "ml_book.pdf"
    mock_source.chunk.content = "This is relevant content from the document about the concept."
    mock_source.chunk.page_number = 42
    
    mock.query_with_context.return_value = (
        "Relevant content from documents",
        [mock_source]
    )
    return mock


@pytest.fixture
def mock_document_manager_empty():
    """Mock document manager with no documents."""
    mock = Mock()
    mock.get_user_documents.return_value = []
    return mock


@pytest.fixture
def mock_document_manager_with_docs():
    """Mock document manager with documents."""
    mock = Mock()
    
    mock_doc = Mock()
    mock_doc.id = "doc_123"
    mock_doc.title = "ML Textbook"
    mock_doc.original_filename = "ml_book.pdf"
    
    mock.get_user_documents.return_value = [mock_doc]
    return mock


@pytest.fixture
def sample_memory_context():
    """Sample memory context for testing."""
    return {
        "relevant_concepts": ["linear algebra", "matrices", "eigenvalues"],
        "weak_areas": ["calculus", "probability"],
        "memory": {
            "current_topic": "PCA"
        },
        "is_followup": True
    }


@pytest.fixture
def mock_llm_concept_response():
    """Mock structured response for concept explanation."""
    mock = Mock()
    mock.intuitive_explanation = "Simple, intuitive explanation using everyday analogies."
    mock.technical_explanation = "Rigorous technical explanation with mathematical formulas."
    mock.key_takeaway = "The main insight in one sentence."
    mock.why_matters = "This concept matters because it enables understanding of advanced topics."
    mock.concepts_covered = ["concept 1", "concept 2", "concept 3"]
    return mock


@pytest.fixture
def mock_llm_code_response():
    """Mock structured response for code generation."""
    mock = Mock()
    mock.code = "def example():\n    pass"
    mock.explanation = "This code does something useful."
    mock.usage_example = "result = example()"
    mock.time_complexity = "O(n)"
    mock.space_complexity = "O(1)"
    mock.key_concepts = ["loops", "functions", "variables"]
    return mock


@pytest.fixture
def setup_mock_llm():
    """
    Helper fixture to setup LLM mock chain.
    
    Returns a function that takes (mock_get_llm, mock_response) and sets up the mock.
    """
    def _setup(mock_get_llm, mock_response):
        """
        Setup LLM mock chain.
        
        Args:
            mock_get_llm: Mocked get_llm function
            mock_response: Mock response object to return
        """
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = mock_response
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        return mock_llm
    
    return _setup
