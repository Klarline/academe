"""Configuration module for Academe."""

from .settings import Settings, get_settings, validate_api_keys

def get_llm(temperature: float = 0.7):
    """
    Get configured LLM instance based on settings.
    
    Args:
        temperature: Temperature for LLM sampling
    
    Returns:
        Configured LLM instance
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI
    
    settings = get_settings()
    
    if settings.llm_provider == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",  # Latest stable (June 2025) - 1M tokens, 65K output
            google_api_key=settings.google_api_key,
            temperature=temperature,
            convert_system_message_to_human=True  # For better compatibility
        )
    elif settings.llm_provider == "claude":
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=temperature
        )
    elif settings.llm_provider == "openai":
        return ChatOpenAI(
            model="gpt-4o",
            openai_api_key=settings.openai_api_key,
            temperature=temperature
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


__all__ = ["Settings", "get_settings", "validate_api_keys", "get_llm"]