"""Test the complete LangGraph workflow"""

import sys
from pathlib import Path

# Add src to Python path for standalone execution
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
from core.graph import build_workflow, process_with_langgraph
from core.models import UserProfile


class TestWorkflow:
    """Test suite for the complete workflow"""
    
    def test_workflow_structure(self):
        """Test that workflow compiles without errors"""
        app = build_workflow()
        assert app is not None
    
    @pytest.mark.slow
    def test_concept_query_flow(self):
        """Test workflow with concept query"""
        result = process_with_langgraph(
            question="What is gradient descent?",
            user_id="test_user",
            conversation_id="test_conv",
            user_profile=None
        )
        
        # Should have routed to concept explainer
        assert result["agent_used"] == "concept_explainer"
        assert result["route"] == "concept"
        assert len(result["response"]) > 100
    
    @pytest.mark.slow
    def test_code_query_flow(self):
        """Test workflow with code query"""
        result = process_with_langgraph(
            question="Show me gradient descent code in Python",
            user_id="test_user",
            conversation_id="test_conv",
            user_profile=None
        )
        
        # Should have routed to code helper
        assert result["agent_used"] == "code_helper"
        assert result["route"] == "code"
        assert len(result["response"]) > 100
    
    @pytest.mark.slow
    def test_multiple_queries(self):
        """Test workflow handles multiple different queries"""
        queries = [
            ("What is PCA?", "concept"),
            ("Implement PCA in NumPy", "code"),
            ("Explain eigenvalues", "concept"),
        ]
        
        for question, expected_route in queries:
            result = process_with_langgraph(
                question=question,
                user_id="test_user",
                conversation_id="test_conv",
                user_profile=None
            )
            assert result["route"] == expected_route
            assert len(result["response"]) > 50
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_end_to_end_concept(self):
        """Integration test: full concept explanation workflow"""
        result = process_with_langgraph(
            question="What is backpropagation?",
            user_id="test_user",
            conversation_id="test_conv",
            user_profile=None
        )
        
        # Verify complete response structure
        assert "agent_used" in result
        assert "response" in result
        assert "question" in result
        
        # Should contain multi-level explanation markers
        response = result["response"].lower()
        assert any(marker in response for marker in ["intuitive", "technical"])
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_end_to_end_code(self):
        """Integration test: full code generation workflow"""
        result = process_with_langgraph(
            question="Write a function for linear regression",
            user_id="test_user",
            conversation_id="test_conv",
            user_profile=None
        )
        
        # Verify complete response structure
        assert result["agent_used"] == "code_helper"
        
        # Should contain code block
        assert "```" in result["response"]
        assert "def" in result["response"].lower()


# Manual test for interactive development
def manual_test_workflow():
    """
    Manual test to see the complete workflow in action.
    Run this directly to test interactively.
    """
    print("\n" + "=" * 70)
    print("Manual Test: Complete Workflow")
    print("=" * 70)
    
    test_queries = [
        "What is gradient descent?",
        "Show me how to implement gradient descent in NumPy",
        "Explain Principal Component Analysis",
        "Write code for PCA from scratch",
    ]
    
    for query in test_queries:
        print(f"\n{'=' * 70}")
        print(f"Query: {query}")
        print('=' * 70 + "\n")
        
        result = process_with_langgraph(
            question=query,
            user_id="test_user",
            conversation_id="test_conv",
            user_profile=None
        )
        
        print(f"Route: {result['route']}")
        print(f"Agent: {result['agent_used']}")
        print(f"\nResponse:\n{result['response']}")
        print("\n" + "─" * 70)
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    manual_test_workflow()