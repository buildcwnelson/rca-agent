"""Multi-provider model factory for rca-agent.

Supports seamless instantiation of reasoning models across:
- Google Gemini (Google AI Studio)
- OpenRouter (Unified router for Claude, Llama 3, DeepSeek, etc.)
- OpenAI (GPT-4o, o3, etc.)
- Ollama (Local open-source models)

Automatically detects available keys from environment variables or explicit flags.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agno.models.base import Model


def resolve_provider_and_key(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str, str | None]:
    """Resolve the active LLM provider, default model, and API key.

    Returns
    -------
    tuple[str, str, str | None]
        (provider_name, model_id, resolved_api_key)
    """
    # 1. If explicit provider is requested
    req_provider = provider.lower() if provider else None

    # Detect provider from model name prefixes
    if not req_provider and model:
        if model.startswith("openrouter/"):
            req_provider = "openrouter"
            model = model.removeprefix("openrouter/")
        elif model.startswith("gemini"):
            req_provider = "gemini"
        elif model.startswith(("gpt-", "o1", "o3")):
            req_provider = "openai"

    # 2. Auto-detect provider based on environment variables if not specified
    if not req_provider:
        if os.getenv("OPENROUTER_API_KEY"):
            req_provider = "openrouter"
        elif os.getenv("OPENAI_API_KEY"):
            req_provider = "openai"
        elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            req_provider = "gemini"
        elif os.getenv("OLLAMA_HOST"):
            req_provider = "ollama"
        else:
            # Fall back to Gemini default
            req_provider = os.getenv("RCA_DEFAULT_PROVIDER", "gemini").lower()

    # 3. Resolve API key and model per provider
    if req_provider == "openrouter":
        resolved_key = (
            api_key
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("OPENAI_API_KEY")  # Some setups alias OpenRouter as OpenAI key
        )
        resolved_model = model or os.getenv(
            "OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"
        )
    elif req_provider == "openai":
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    elif req_provider == "ollama":
        resolved_key = None
        resolved_model = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    else:
        # Default: Gemini
        req_provider = "gemini"
        resolved_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        resolved_model = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    return req_provider, resolved_model, resolved_key


def create_model_instance(
    provider: str,
    model_id: str,
    api_key: str | None = None,
) -> Model:
    """Instantiate an Agno Model instance for the chosen provider."""
    provider_clean = provider.lower()

    if provider_clean == "openrouter":
        try:
            from agno.models.openrouter import OpenRouter
        except ImportError as exc:
            raise RuntimeError("OpenRouter requires 'openai'. Run: pip install openai") from exc

        kwargs: dict[str, Any] = {"id": model_id}
        if api_key:
            kwargs["api_key"] = api_key
        return OpenRouter(**kwargs)

    if provider_clean == "openai":
        try:
            from agno.models.openai import OpenAIChat
        except ImportError as exc:
            raise RuntimeError("OpenAI requires 'openai'. Run: pip install openai") from exc

        kwargs = {"id": model_id}
        if api_key:
            kwargs["api_key"] = api_key
        return OpenAIChat(**kwargs)

    if provider_clean == "ollama":
        from agno.models.ollama import Ollama

        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        return Ollama(id=model_id, host=host)

    # Default: Google Gemini
    from agno.models.google import Gemini

    kwargs = {"id": model_id}
    if api_key:
        kwargs["api_key"] = api_key
    return Gemini(**kwargs)
