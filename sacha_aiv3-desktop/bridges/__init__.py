"""
bridges — multi-platform messaging (Telegram first, Discord/Slack planned).
"""

from bridges.base import BridgeMessage, BridgeNotAvailable, MessagingBridge
from bridges.registry import BridgeRegistry
from bridges.session_share import ConversationInbox

__all__ = [
    "BridgeMessage",
    "BridgeNotAvailable",
    "MessagingBridge",
    "BridgeRegistry",
    "ConversationInbox",
]
