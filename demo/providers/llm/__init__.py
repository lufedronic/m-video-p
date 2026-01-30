"""
LLM provider factory and registry.
"""
import os
from typing import Optional

from .base import LLMProvider, LLMResponse, Message

# Registry of available providers
_llm_providers: dict[str, type[LLMProvider]] = {}

# Cache of initialized provider instances
_provider_instances: dict[str, LLMProvider] = {}


def register_llm_provider(name: str, provider_class: type[LLMProvider]):
    """Register an LLM provider class."""
    _llm_providers[name] = provider_class


def get_llm_provider(name: Optional[str] = None) -> LLMProvider:
    """
    Get an LLM provider instance.
    If name is None, uses LLM_PROVIDER env var or defaults to 'gemini'.
    Instances are cached for reuse.
    """
    if name is None:
        name = os.getenv("LLM_PROVIDER", "gemini")

    if name not in _llm_providers:
        available = list(_llm_providers.keys())
        raise ValueError(f"Unknown LLM provider '{name}'. Available: {available}")

    # Return cached instance or create new one
    if name not in _provider_instances:
        _provider_instances[name] = _llm_providers[name]()

    return _provider_instances[name]


def list_llm_providers() -> dict:
    """List all registered LLM providers with their available models."""
    result = {}
    for name, provider_class in _llm_providers.items():
        try:
            # Try to get instance to access models
            provider = get_llm_provider(name)
            result[name] = {
                "models": provider.available_models,
                "default": provider.default_model
            }
        except ValueError:
            # Provider not configured (missing API key)
            result[name] = {
                "models": [],
                "default": None,
                "error": "Not configured (missing API key)"
            }
    return result


def get_available_llm_providers() -> list[str]:
    """Get list of configured (usable) LLM providers."""
    available = []
    for name in _llm_providers.keys():
        try:
            get_llm_provider(name)
            available.append(name)
        except ValueError:
            pass  # Not configured
    return available


# Import and register providers
# Each import may fail if the SDK is not installed, so we handle gracefully

try:
    from .gemini import GeminiProvider
    register_llm_provider("gemini", GeminiProvider)
except ImportError:
    pass

try:
    from .anthropic import AnthropicProvider
    register_llm_provider("anthropic", AnthropicProvider)
except ImportError:
    pass

try:
    from .openai import OpenAIProvider
    register_llm_provider("openai", OpenAIProvider)
except ImportError:
    pass


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "get_llm_provider",
    "list_llm_providers",
    "get_available_llm_providers",
]
