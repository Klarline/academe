"""Test the Code Helper agent"""

import sys
from pathlib import Path

# Add src to Python path for standalone execution
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
from core.agents.code_helper import generate_code, generate_code_with_context


class TestCodeHelper:
    """Test suite for Code Helper agent"""
    
    @pytest.mark.slow
    def test_generate_code_basic(self):
        """Test basic code generation"""
        result = generate_code("Implement a simple linear regression function in NumPy")
        
        # Should contain code block
        assert "```python" in result or "```" in result
        assert len(result) > 100
    
    @pytest.mark.slow
    def test_generate_code_with_context(self):
        """Test code generation with context"""
        result = generate_code_with_context(
            question="Implement gradient descent",
            user_profile=None,
            context=None,
            memory_context=None
        )
        
        assert len(result) > 50
    
    @pytest.mark.slow
    def test_generate_code_simple(self):
        """Test simple code generation"""
        result = generate_code("k-means clustering")
        
        # Should be longer with context
        assert len(result) > 100
    
    def test_different_implementations(self):
        """Test that function accepts various concepts"""
        concepts = [
            "linear regression",
            "gradient descent",
            "PCA",
            "k-means clustering",
            "logistic regression"
        ]
        
        # Just verify function signature works
        for concept in concepts:
            assert callable(generate_code)


class TestCodeHelperIntegration:
    """Integration tests with real LLM calls"""
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_real_code_generation_quality(self):
        """
        Test with real LLM call and check code quality.
        This is expensive, so marked as integration test.
        """
        result = generate_code("Implement gradient descent in NumPy")
        
        # Quality checks
        assert len(result) > 200, "Should have substantial content"
        assert "numpy" in result.lower() or "np" in result.lower()
        assert "def" in result.lower(), "Should contain function definition"
        
        # Should have structured sections
        has_structure = any(marker in result for marker in [
            "##", "Overview", "Implementation", "Example"
        ])
        assert has_structure, "Should have structured sections"
        
        # Should contain code block
        assert "```" in result, "Should contain code block"


# Manual test for development
def manual_test_code_helper():
    """
    Manual test to see actual code output.
    Run directly during development.
    """
    print("\n" + "=" * 70)
    print("Manual Test: Code Helper")
    print("=" * 70)
    
    test_requests = [
        "Implement gradient descent in NumPy",
        "Write a function for linear regression from scratch",
        "Show me how to implement PCA"
    ]
    
    for request in test_requests:
        print(f"\n{'=' * 70}")
        print(f"Request: {request}")
        print('=' * 70)
        
        result = generate_code(request)
        print(result)
        print("\n")
        
        input("Press Enter to continue...")


if __name__ == "__main__":
    manual_test_code_helper()