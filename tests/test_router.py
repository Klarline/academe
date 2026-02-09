"""Test the router agent with pytest"""

import sys
from pathlib import Path

# Add src to Python path for standalone execution
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
from core.agents.router import route_query


class TestRouterAgent:
    """Test suite for router agent"""
    
    @pytest.mark.parametrize("query,expected", [
        # Concept queries
        ("What is gradient descent?", "concept"),
        ("Explain PCA", "concept"),
        ("Tell me about neural networks", "concept"),
        ("How does backpropagation work?", "concept"),
        ("What are eigenvalues?", "concept"),
        ("gradient descent", "concept"),  # Ambiguous - defaults to concept
    ])
    def test_concept_routing(self, query, expected):
        """Test that concept queries route correctly"""
        assert route_query(query) == expected
    
    @pytest.mark.parametrize("query,expected", [
        # Code queries
        ("Show me gradient descent code", "code"),
        ("Implement PCA in Python", "code"),
        ("Write a function for k-means", "code"),
        ("How to code neural networks in NumPy", "code"),
        ("Give me example code for linear regression", "code"),
        ("code review of my implementation", "code"),
        ("python implementation", "code"),
        ("numpy code", "code"),
    ])
    def test_code_routing(self, query, expected):
        """Test that code queries route correctly"""
        assert route_query(query) == expected
    
    def test_empty_query(self):
        """Test handling of edge cases"""
        # Empty query should default to concept
        assert route_query("") == "concept"
    
    def test_case_insensitive(self):
        """Test that routing is case insensitive"""
        assert route_query("SHOW ME CODE") == "code"
        assert route_query("Show Me Code") == "code"
        assert route_query("show me code") == "code"