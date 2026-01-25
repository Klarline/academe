"""
Application settings and configuration.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from typing import Literal
import os
from pathlib import Path

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        llm_provider: Which LLM to use (gemini, claude, openai)
        google_api_key: Google API key for Gemini
        anthropic_api_key: Anthropic API key for Claude
        openai_api_key: OpenAI API key
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    
    # LLM Configuration
    llm_provider: Literal["gemini", "claude", "openai"] = "gemini"
    
    # API Keys
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    
    # App Settings
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Create global settings instance
settings = Settings()

# Validate that we have the required API key
def validate_api_keys():
    """Ensure we have the API key for the selected provider."""
    provider = settings.llm_provider
    
    if provider == "gemini" and not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found in .env file. "
            "Get your key from: https://aistudio.google.com/apikey"
        )
    elif provider == "claude" and not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env file")
    elif provider == "openai" and not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")

# Validate on import
validate_api_keys()