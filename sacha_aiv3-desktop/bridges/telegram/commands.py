"""
bridges/telegram/commands.py — /start /help /reset handlers.

Handlers are registered on the telegram Application. The bridge wires a
``on_message`` callback for ordinary text; slash commands short-circuit it.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

SLASH_HELP = {
    "/start": "Begin a session with SACHA.",
    "/help": "Show this help.",
    "/reset": "Forget this conversation and start fresh.",
}

_HELP_TEXT = (
    "SACHA at your service via Telegram.\n\n"
    "/start — begin session\n"
    "/help — this help\n"
    "/reset — clear the conversation\n\n"
    "Just type a normal message to talk."
)


def register_handlers(application: Any, on_message: Callable[[Any, str, str], Awaitable[None]]) -> None:
    """Attach slash-command + message handlers to a telegram Application."""
    from telegram import Update
    from telegram.ext import CommandHandler, MessageHandler, filters

    async def _echo_reply(chat_id: int, text: str) -> None:
        await on_message(chat_id, "telegram", text)

    async def _cmd_start(update: Update, context: Any) -> None:
        if update.effective_chat:
            await update.effective_chat.send_message("Session started with SACHA. What shall we do?")

    async def _cmd_help(update: Update, context: Any) -> None:
        if update.effective_chat:
            await update.effective_chat.send_message(_HELP_TEXT)

    async def _cmd_reset(update: Update, context: Any) -> None:
        if update.effective_chat:
            await update.effective_chat.send_message("Conversation reset. Start fresh whenever you're ready.")

    async def _on_text(update: Update, context: Any) -> None:
        msg = update.effective_message
        if msg is None or msg.chat is None or not msg.text:
            return
        await _echo_reply(msg.chat.id, msg.text)

    application.add_handler(CommandHandler("start", _cmd_start))
    application.add_handler(CommandHandler("help", _cmd_help))
    application.add_handler(CommandHandler("reset", _cmd_reset))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_text))
    logger.info("telegram command handlers registered")
