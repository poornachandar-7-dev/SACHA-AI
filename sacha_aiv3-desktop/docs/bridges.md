# Bridges

Bridges let SACHA reach the user on platforms other than the desktop HUD —
Telegram today, Discord and Slack planned. Each bridge is an isolated
subprocess or async task that talks to the SACHA core through the same
`MessagingBridge` interface.

## Interface

`bridges/base.py` defines:

- `name` — short identifier (`telegram`, `discord`, `slack`)
- `async start()` — begin receiving messages
- `async stop()` — graceful shutdown
- `async send(user_id, text, **opts)` — push a message back to the platform
- `on_message` — registered callback the core subscribes to

All bridges share:

- The same session/memory as the desktop HUD (`bridges/registry.py`
  routes inbound messages to the same conversation state).
- The same provider selection logic through the OmniRouter.
- The same `SOUL.md` personality loader.

## Telegram (first bridge)

`bridges/telegram/` contains:

- `bot.py` — Telegram bot entry point (python-telegram-bot or aiogram)
- `commands.py` — `/start`, `/help`, `/reset`, plus custom plugin commands
- `session_share.py` — pairs a Telegram chat with an existing desktop
  session, so a conversation started on the desktop can be continued on
  Telegram and vice versa

Setup:

1. Create a bot with `@BotFather`, copy the token.
2. Put the token in `.env` as `TELEGRAM_BOT_TOKEN`.
3. Set `TELEGRAM_ALLOWED_USER_ID` to your own Telegram user ID — this is
   the auth gate; the bot will refuse anyone else.
4. Start SACHA; the bridge auto-launches if the token is present.

## Auth model

Bridges never operate without an explicit allowlist. By default each bridge
denies all inbound traffic until at least one user ID is approved in the
gateway config (`bridges/gateway.py`).

## Planned bridges

- **Discord** — `bridges/discord/bot.py` using `discord.py`
- **Slack** — `bridges/slack/app.py` using the Bolt framework
- WhatsApp / Signal — stretch goals, only after the first three are solid