# Providers

SACHA's AI calls go through the `ModelProvider` interface defined in
`core/providers/base.py`. Adding a new provider is a one-file swap — no
changes to the router, reply composer, or HUD.

## Interface contract

A provider must implement:

- `name` — short identifier used in config and logs
- `capabilities` — what it can do (chat, streaming, vision, function-calling)
- `async chat(messages, **opts) -> Reply` — non-streaming completion
- `async stream(messages, **opts) -> AsyncIterator[Chunk]` — streaming
- `async close()` — release any open client/session

`Reply` and `Chunk` are small dataclasses that the reply composer in
`core/reply/` already knows how to consume.

## Built-in providers

| Provider    | File                            | Notes                          |
| ----------- | ------------------------------- | ------------------------------ |
| Local       | `core/providers/local.py`       | Ollama / llama.cpp on localhost |
| NVIDIA      | `core/providers/nvidia.py`      | Cloud, OpenAI-compatible API   |
| OpenAI      | `core/providers/openai.py`      | Cloud                          |
| Gemini      | `core/providers/gemini.py`      | Cloud                          |

## Adding a new provider

1. Create `core/providers/<your_provider>.py`.
2. Subclass `ModelProvider` from `base.py`.
3. Register it in `core/providers/registry.py` under its `name` and capability
   tags.
4. Add the API key name to `.env.example` and `core/config.py`.
5. Add `tests/unit/test_providers_<your_provider>.py` with mocked HTTP — no
   real network calls in unit tests.

## Router integration

The `OmniRouter` in `core/router/omni_router.py` picks a provider per
request based on:

- **Privacy sensitivity** — routing key from the request (set by HUD or
  scheduler); sensitive queries prefer the local provider.
- **Complexity / length** — long prompts and tool-heavy requests prefer
  cloud providers with larger context windows.
- **Fallback** — `core/router/fallback.py` retries the next provider in the
  chain on transport / rate-limit / timeout errors.

Providers register themselves with the router through the registry; the
router never imports a concrete provider directly.