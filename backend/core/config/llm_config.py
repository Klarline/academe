"""
LLM factory for creating language model instances.
Supports multiple providers: Gemini, Claude, OpenAI.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

from .settings import get_settings


def get_llm(temperature: float = 0.7) -> "BaseChatModel":
    """
    Factory function to get LLM instance based on configuration.
    
    This design pattern makes it easy to swap LLMs without changing
    any agent code. Just change LLM_PROVIDER in .env!
    
    Args:
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
    
    Returns:
        Configured LLM instance
        
    Raises:
        ValueError: If provider is unsupported or API key is missing
    
    Example:
        >>> llm = get_llm(temperature=0.7)
        >>> response = llm.invoke("What is machine learning?")
    """
    
    settings = get_settings()
    provider = settings.llm_provider.lower()
    
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=temperature,
            google_api_key=settings.google_api_key,
            convert_system_message_to_human=True  # Better compatibility
        )
    
    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=temperature,
            api_key=settings.anthropic_api_key
        )
    
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            api_key=settings.openai_api_key
        )
    
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: gemini, claude, openai"
        )