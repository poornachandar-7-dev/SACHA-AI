"""
bridges/telegram/bot.py — python-telegram-bot v22 application bridge.
"""

from __future__ import annotations

import logging

from bridges.base import BridgeMessage, MessagingBridge
from bridges.session_share import ConversationInbox
from bridges.telegram.commands import register_handlers

logger = logging.getLogger(__name__)


class TelegramBridge(MessagingBridge):
    name = "telegram"
    channel = "telegram"
    requires_auth = ("token",)

    def __init__(self, token: str | None = None, inbox: ConversationInbox | None = None) -> None:
        super().__init__(inbox=inbox)
        if token:
            self._auth["token"] = token
        self._application = None

    async def start(self) -> None:
        from telegram.ext import Application

        token = self._auth.get("token")
        if not token:
            raise RuntimeError("telegram bridge has no token")
        app = Application.builder().token(token).connect_timeout(10).build()
        register_handlers(app, on_message=self._on_message)
        await app.initialize()
        await app.start()
        if app.updater is not None:
            await app.updater.start_polling(drop_pending_updates=True)
        self._application = app
        logger.info("telegram bridge polling")

    async def stop(self) -> None:
        if self._application is None:
            return
        app = self._application
        if app.updater is not None:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        self._application = None

    async def _on_message(self, chat_id, sender, text) -> None:
        await self.dispatch(
            BridgeMessage(chat_id=str(chat_id), sender=sender or "unknown", text=text or "", channel="telegram")
        )
