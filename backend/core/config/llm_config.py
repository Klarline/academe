"""
LLM factory for creating language model instances.
Supports multiple providers: Gemini, Claude, OpenAI.

LLM Routing Strategy:
    - get_llm()          → User-facing (Gemini by default): explanations, answers
    - get_openai_llm()   → Infrastructure tasks: query rewriting, HyDE, RAGAS evaluation
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

from .settings import get_settings

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0.7) -> "BaseChatModel":
    """
    Get the primary LLM for user-facing tasks (explanations, answers).

    Uses the provider set in LLM_PROVIDER env var (default: Gemini).

    Args:
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

    Returns:
        Configured LLM instance
    """

    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=temperature,
            google_api_key=settings.google_api_key,
            convert_system_message_to_human=True,
        )

    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=temperature,
            api_key=settings.anthropic_api_key,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            api_key=settings.openai_api_key,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: gemini, claude, openai"
        )


def get_openai_llm(
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
) -> "BaseChatModel":
    """
    Get OpenAI LLM for infrastructure/evaluation tasks.

    Used for: query rewriting, HyDE, RAGAS evaluation — tasks
    where OpenAI excels at structured, instruction-following output.

    Falls back to the primary LLM if OpenAI key is not available.

    Args:
        model: OpenAI model name (default: gpt-4o-mini for speed/cost)
        temperature: Sampling temperature (default: 0.0 for determinism)

    Returns:
        Configured LLM instance
    """
    settings = get_settings()

    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )

    logger.warning("OpenAI API key not set, falling back to primary LLM")
    return get_llm(temperature=temperature)