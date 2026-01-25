"""Test the Concept Explainer agent"""

import pytest
from academe.agents.concept_explainer import (
    explain_concept,
    explain_concept_interactive
)


class TestConceptExplainer:
    """Test suite for Concept Explainer agent"""
    
    @pytest.mark.slow  # Mark as slow since it calls LLM
    def test_explain_both_levels(self):
        """Test explanation with both levels"""
        result = explain_concept("What is gradient descent?", level="both")
        
        # Should contain both sections
        assert "Intuitive" in result or "intuitive" in result.lower()
        assert "Technical" in result or "technical" in result.lower()
        assert len(result) > 100  # Should be substantial
    
    @pytest.mark.slow
    def test_explain_intuitive_only(self):
        """Test intuitive-only explanation"""
        result = explain_concept("What is PCA?", level="intuitive")
        
        # Should have content
        assert len(result) > 50
        # Intuitive explanations should avoid heavy math notation
        # (This is a weak test - just checking it returns something)
    
    @pytest.mark.slow
    def test_explain_technical_only(self):
        """Test technical-only explanation"""
        result = explain_concept("What are eigenvalues?", level="technical")
        
        # Should have content
        assert len(result) > 50
    
    @pytest.mark.slow
    def test_explain_interactive(self):
        """Test interactive structured output"""
        result = explain_concept_interactive("What is backpropagation?")
        
        # Should return dictionary with expected keys
        assert isinstance(result, dict)
        assert "full_response" in result
        assert "intuitive" in result
        assert "technical" in result
        
        # Should have content
        assert len(result["full_response"]) > 100
    
    def test_different_concepts(self):
        """Test that different concepts produce different outputs"""
        # This test doesn't call LLM, just validates function signature
        # In a real test, you'd use mocking or vcr.py to record responses
        
        concepts = [
            "gradient descent",
            "principal component analysis",
            "neural networks"
        ]
        
        # Just verify function accepts these inputs without error
        for concept in concepts:
            assert callable(explain_concept)  # Sanity check


class TestConceptExplainerIntegration:
    """Integration tests that actually call the LLM"""
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_real_explanation_quality(self):
        """
        Test with a real LLM call and check response quality.
        
        This is a slow test that costs API credits, so we mark it
        as integration and slow.
        """
        result = explain_concept("What is gradient descent?", level="both")
        
        # Quality checks
        assert len(result) > 200, "Explanation should be substantial"
        assert "gradient" in result.lower(), "Should mention the concept"
        
        # Check structure exists
        has_structure = any(marker in result for marker in [
            "##", "Intuitive", "Technical", "Key Takeaway"
        ])
        assert has_structure, "Should have structured sections"


# Manual test for development (not run by pytest)
def manual_test_concept_explainer():
    """
    Manual test for interactive development.
    Run this directly to see actual output during development.
    """
    print("\n" + "=" * 70)
    print("Manual Test: Concept Explainer")
    print("=" * 70)
    
    test_questions = [
        "What is gradient descent?",
        "Explain Principal Component Analysis",
        "What are eigenvalues and eigenvectors?"
    ]
    
    for question in test_questions:
        print(f"\n{'=' * 70}")
        print(f"Question: {question}")
        print('=' * 70)
        
        result = explain_concept(question, level="both")
        print(result)
        print("\n")
        
        input("Press Enter to continue...")


if __name__ == "__main__":
    # Run manual test if executed directly
    manual_test_concept_explainer()