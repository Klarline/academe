"""
Application settings and configuration.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from typing import Literal
import os
from pathlib import Path

# Get project root (3 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        llm_provider: Which LLM to use (gemini, claude, openai)
        google_api_key: Google API key for Gemini
        anthropic_api_key: Anthropic API key for Claude
        openai_api_key: OpenAI API key
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        mongodb_uri: MongoDB connection URI (REQUIRED - no default for security)
        jwt_secret_key: JWT secret key (REQUIRED - must be changed from default)
    """
    
    # LLM Configuration
    llm_provider: Literal["gemini", "claude", "openai"] = "gemini"
    
    # API Keys
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    
    # Pinecone Configuration (Optional - uses mock if not provided)
    pinecone_api_key: str | None = None
    pinecone_environment: str | None = None
    pinecone_index_name: str = "academe"
    
    # App Settings
    log_level: str = "INFO"

    # MongoDB Configuration - NO DEFAULT for security
    mongodb_uri: str
    mongodb_db_name: str = "academe"

    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Session Configuration
    session_timeout_minutes: int = 60
    max_sessions_per_user: int = 5

    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    model_config = ConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Ensure JWT secret was changed from insecure default."""
        if v == "your-secret-key-change-this-in-production":
            raise ValueError(
                "JWT_SECRET_KEY must be changed from default! "
                "Set a secure random string in .env file. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long for security. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v

# Create global settings instance
_settings: Settings | None = None

def get_settings() -> Settings:
    """Get the global settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def validate_api_keys() -> None:
    """
    Ensure we have the API key for the selected provider.
    
    Call this at application startup to fail fast if configuration is invalid.
    
    Raises:
        ValueError: If the required API key for selected provider is missing
    """
    settings = get_settings()
    provider = settings.llm_provider
    
    if provider == "gemini" and not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found in .env file. "
            "Get your key from: https://aistudio.google.com/apikey"
        )
    elif provider == "claude" and not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found in .env file. "
            "Get your key from: https://console.anthropic.com/"
        )
    elif provider == "openai" and not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in .env file. "
            "Get your key from: https://platform.openai.com/api-keys"
        )
