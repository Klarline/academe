"""
Configuration module for Academe.
Provides settings and LLM factory.
"""

from .settings import settings, validate_api_keys
from .llm_config import get_llm, get_default_llm

__all__ = [
    "settings",
    "validate_api_keys",
    "get_llm",
    "get_default_llm",
]