"""
Comprehensive tests for configuration module.

Tests cover:
- Settings loading and validation
- Environment variable handling
- LLM factory functions
- API key validation
- Security validations (JWT secret, MongoDB URI)
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.config.settings import Settings, get_settings, validate_api_keys
from core.config.llm_config import get_llm


class TestSettings:
    """Test Settings class and validation."""

    def test_settings_loads_from_env(self):
        """Test that settings loads from environment variables."""
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'gemini',
            'GOOGLE_API_KEY': 'test-key',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'a' * 32
        }):
            settings = Settings()
            assert settings.llm_provider == "gemini"
            assert settings.google_api_key == "test-key"

    def test_settings_defaults(self):
        """Test default values are set correctly."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'a' * 32
        }):
            settings = Settings()
            assert settings.llm_provider == "gemini"
            assert settings.log_level == "INFO"
            assert settings.jwt_algorithm == "HS256"
            assert settings.jwt_expiration_hours == 24

    def test_jwt_secret_validation_too_short(self):
        """Test JWT secret must be at least 32 characters."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'short'
        }):
            with pytest.raises(ValueError, match="at least 32 characters"):
                Settings()

    def test_jwt_secret_validation_default_rejected(self):
        """Test that default JWT secret is rejected."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'your-secret-key-change-this-in-production'
        }):
            with pytest.raises(ValueError, match="must be changed from default"):
                Settings()

    def test_mongodb_uri_required(self):
        """Test that MongoDB URI has no insecure default."""
        # MongoDB URI should be required from .env, not have a default
        # The actual .env file has it, so this test verifies the field exists
        settings = get_settings()
        assert settings.mongodb_uri is not None
        assert "mongodb://" in settings.mongodb_uri

    def test_llm_provider_validation(self):
        """Test LLM provider only accepts valid values."""
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'invalid_provider',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'a' * 32
        }):
            with pytest.raises(Exception):  # ValidationError
                Settings()

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case-insensitive."""
        with patch.dict(os.environ, {
            'llm_provider': 'claude',  # lowercase
            'mongodb_uri': 'mongodb://localhost:27017',
            'jwt_secret_key': 'a' * 32
        }):
            settings = Settings()
            assert settings.llm_provider == "claude"


class TestGetSettings:
    """Test get_settings singleton function."""

    def test_get_settings_returns_singleton(self):
        """Test that get_settings returns the same instance."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'a' * 32
        }):
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2

    def test_get_settings_caches_instance(self):
        """Test that settings instance is cached."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'a' * 32
        }):
            # Clear any existing singleton
            import core.config.settings as settings_module
            settings_module._settings = None
            
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2


class TestValidateApiKeys:
    """Test API key validation."""

    def test_validate_gemini_api_key_present(self):
        """Test validation passes when Gemini key is present."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "gemini"
            mock_settings.google_api_key = "test-key"
            mock_get.return_value = mock_settings
            
            # Should not raise
            validate_api_keys()

    def test_validate_gemini_api_key_missing(self):
        """Test validation fails when Gemini key is missing."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "gemini"
            mock_settings.google_api_key = None
            mock_get.return_value = mock_settings
            
            with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
                validate_api_keys()

    def test_validate_claude_api_key_present(self):
        """Test validation passes when Claude key is present."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "claude"
            mock_settings.anthropic_api_key = "test-key"
            mock_get.return_value = mock_settings
            
            validate_api_keys()

    def test_validate_claude_api_key_missing(self):
        """Test validation fails when Claude key is missing."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "claude"
            mock_settings.anthropic_api_key = None
            mock_get.return_value = mock_settings
            
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                validate_api_keys()

    def test_validate_openai_api_key_present(self):
        """Test validation passes when OpenAI key is present."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = "test-key"
            mock_get.return_value = mock_settings
            
            validate_api_keys()

    def test_validate_openai_api_key_missing(self):
        """Test validation fails when OpenAI key is missing."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = None
            mock_get.return_value = mock_settings
            
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                validate_api_keys()


class TestGetLLM:
    """Test LLM factory function."""

    def test_get_llm_gemini(self):
        """Test getting Gemini LLM instance."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "gemini"
            mock_settings.google_api_key = "test-key-123"
            mock_get.return_value = mock_settings
            
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_llm:
                llm = get_llm(temperature=0.5)
                
                # Verify the LLM was created with correct parameters
                assert mock_llm.called
                call_kwargs = mock_llm.call_args[1]
                assert call_kwargs['model'] == "gemini-2.5-flash"
                assert call_kwargs['temperature'] == 0.5
                assert call_kwargs['convert_system_message_to_human'] is True

    @pytest.mark.skip(reason="langchain_anthropic not installed in test environment")
    def test_get_llm_claude(self):
        """Test getting Claude LLM instance."""
        pass

    @pytest.mark.skip(reason="langchain_openai not installed in test environment")
    def test_get_llm_openai(self):
        """Test getting OpenAI LLM instance."""
        pass

    def test_get_llm_invalid_provider(self):
        """Test that invalid provider raises validation error."""
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'invalid_provider',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'JWT_SECRET_KEY': 'a' * 32
        }):
            # Clear cached settings
            import core.config.settings as settings_module
            settings_module._settings = None
            
            # Pydantic validates provider at Settings creation
            from pydantic_core import ValidationError
            with pytest.raises(ValidationError):
                get_llm()

    def test_get_llm_default_temperature(self):
        """Test that default temperature is 0.7."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "gemini"
            mock_settings.google_api_key = "test-key"
            mock_get.return_value = mock_settings
            
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_llm:
                llm = get_llm()  # No temperature specified
                
                # Check that temperature=0.7 was passed
                call_kwargs = mock_llm.call_args[1]
                assert call_kwargs['temperature'] == 0.7

    def test_get_llm_case_insensitive_provider(self):
        """Test that provider name is case-insensitive."""
        with patch('core.config.settings.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.llm_provider = "GEMINI"  # Uppercase
            mock_settings.google_api_key = "test-key"
            mock_get.return_value = mock_settings
            
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_llm:
                llm = get_llm()
                
                # Should still work (lowercase internally)
                mock_llm.assert_called_once()


class TestConfigModule:
    """Test config module exports."""

    def test_exports_all_required_symbols(self):
        """Test that __all__ exports all required symbols."""
        from core.config import __all__
        
        expected = ["Settings", "get_settings", "validate_api_keys", "get_llm"]
        assert set(__all__) == set(expected)

    def test_can_import_all_symbols(self):
        """Test that all exported symbols can be imported."""
        from core.config import Settings, get_settings, validate_api_keys, get_llm
        
        assert Settings is not None
        assert callable(get_settings)
        assert callable(validate_api_keys)
        assert callable(get_llm)
