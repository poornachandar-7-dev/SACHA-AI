"""
core/router — OmniRouter + classifier + provider fallback chain.
"""

from core.router.classifier import Complexity, KeywordClassifier, RoutingIntent
from core.router.fallback import FallbackChain
from core.router.omni_router import OmniRouter

__all__ = [
    "KeywordClassifier",
    "RoutingIntent",
    "Complexity",
    "FallbackChain",
    "OmniRouter",
]
