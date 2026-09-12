"""
core/providers — ModelProvider interface + concrete backends.

Importing this package does not require any cloud credentials; providers
self-report ``configured`` so the registry can skip unkeyed backends.
"""

from core.providers.base import ModelProvider, ProviderError, normalize_messages
from core.providers.gemini import GeminiProvider
from core.providers.local import LocalProvider
from core.providers.nvidia import NvidiaProvider
from core.providers.openai import OpenAIProvider
from core.providers.registry import ProviderRegistry

__all__ = [
    "ModelProvider",
    "ProviderError",
    "normalize_messages",
    "GeminiProvider",
    "LocalProvider",
    "NvidiaProvider",
    "OpenAIProvider",
    "ProviderRegistry",
]
