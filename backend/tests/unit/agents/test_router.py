"""
Tests for Router Agent.

Router is stateless and uses LLM for routing decisions.
"""

import pytest
from unittest.mock import Mock, patch
from core.agents.router import (
    route_query_structured,
    route_query,
    get_agent_description,
    RouterDecision
)


class TestRouter:
    """Unit tests for Router agent."""
    
    @patch('core.agents.router.get_llm')
    def test_should_route_concept_question(self, mock_get_llm):
        """Should route 'explain' questions to concept agent."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_decision = RouterDecision(
            route="concept",
            reasoning="This is a conceptual explanation request",
            confidence=0.95
        )
        mock_structured_llm.invoke.return_value = mock_decision
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        # Act
        decision = route_query_structured("Explain gradient descent")
        
        # Assert
        assert decision.route == "concept"
        assert decision.confidence > 0.5
        assert isinstance(decision.reasoning, str)
        mock_get_llm.assert_called_once()
    
    @patch('core.agents.router.get_llm')
    def test_should_route_code_question(self, mock_get_llm):
        """Should route 'implement' questions to code agent."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_decision = RouterDecision(
            route="code",
            reasoning="User wants code implementation",
            confidence=0.92
        )
        mock_structured_llm.invoke.return_value = mock_decision
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        # Act
        decision = route_query_structured("Implement gradient descent in Python")
        
        # Assert
        assert decision.route == "code"
        assert decision.confidence > 0.5
    
    @patch('core.agents.router.get_llm')
    def test_should_route_research_when_has_documents(self, mock_get_llm):
        """Should route to research agent when user has documents."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_decision = RouterDecision(
            route="research",
            reasoning="User has documents and asking specific question",
            confidence=0.88
        )
        mock_structured_llm.invoke.return_value = mock_decision
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        # Act
        decision = route_query_structured(
            "What does the paper say about transformers?",
            has_documents=True
        )
        
        # Assert
        assert decision.route == "research"
    
    @patch('core.agents.router.get_llm')
    def test_should_route_practice_question(self, mock_get_llm):
        """Should route practice/quiz requests to practice agent."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_decision = RouterDecision(
            route="practice",
            reasoning="User wants practice questions",
            confidence=0.94
        )
        mock_structured_llm.invoke.return_value = mock_decision
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        # Act
        decision = route_query_structured("Generate practice questions on PCA")
        
        # Assert
        assert decision.route == "practice"
    
    @patch('core.agents.router.get_llm')
    def test_route_query_returns_string(self, mock_get_llm):
        """route_query should return route as string (backward compatible)."""
        # Arrange
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_decision = RouterDecision(
            route="concept",
            reasoning="Test",
            confidence=0.9
        )
        mock_structured_llm.invoke.return_value = mock_decision
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        # Act
        route = route_query("Explain PCA")
        
        # Assert
        assert route == "concept"
        assert isinstance(route, str)
    
    def test_get_agent_description_returns_descriptions(self):
        """Should return description for each agent type."""
        assert "concept" in get_agent_description("concept").lower() or "explain" in get_agent_description("concept").lower()
        assert "code" in get_agent_description("code").lower()
        assert "search" in get_agent_description("research").lower() or "document" in get_agent_description("research").lower()
        assert "practice" in get_agent_description("practice").lower() or "question" in get_agent_description("practice").lower()
    
    def test_get_agent_description_handles_unknown(self):
        """Should handle unknown route gracefully."""
        result = get_agent_description("unknown_agent")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_router_decision_model_validation(self):
        """RouterDecision model should validate fields correctly."""
        # Valid decision
        decision = RouterDecision(
            route="concept",
            reasoning="Test reasoning",
            confidence=0.85
        )
        assert decision.route == "concept"
        assert 0.0 <= decision.confidence <= 1.0
        
        # Test confidence bounds
        with pytest.raises(Exception):
            RouterDecision(route="concept", reasoning="Test", confidence=1.5)
        
        with pytest.raises(Exception):
            RouterDecision(route="concept", reasoning="Test", confidence=-0.1)
