"""
SACHA — AI provider abstraction.
"""

import os
import requests

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")  # ollama | openai | gemini | claude

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = (
    "You are SACHA, a helpful, concise AI assistant running locally on the user's device. "
    "Keep answers short and practical unless asked for detail."
)


def _build_prompt(message: str, context: list) -> str:
    """Turns recent chat history + the new message into one prompt string."""
    convo = ""
    for turn in context:
        role = "User" if turn["role"] == "user" else "SACHA"
        convo += f"{role}: {turn['content']}\n"
    convo += f"User: {message}\nSACHA:"
    return f"{SYSTEM_PROMPT}\n\n{convo}"


def _generate_ollama(message: str, context: list) -> str:
    prompt = _build_prompt(message, context)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "Error: couldn't reach Ollama. Make sure it's running (`ollama serve`)."
    except Exception as e:
        return f"Error: {e}"


def _generate_openai(message: str, context: list) -> str:
    # TODO: implement when web demo mode is needed.
    # Requires OPENAI_API_KEY env var and the `openai` package.
    return "Error: OpenAI provider not implemented yet."


def _generate_gemini(message: str, context: list) -> str:
    # TODO: implement when web demo mode is needed.
    return "Error: Gemini provider not implemented yet."


def _generate_claude(message: str, context: list) -> str:
    # TODO: implement when web demo mode is needed.
    return "Error: Claude provider not implemented yet."


def generate_reply(message: str, context: list = None) -> str:
    context = context or []

    if AI_PROVIDER == "ollama":
        return _generate_ollama(message, context)
    elif AI_PROVIDER == "openai":
        return _generate_openai(message, context)
    elif AI_PROVIDER == "gemini":
        return _generate_gemini(message, context)
    elif AI_PROVIDER == "claude":
        return _generate_claude(message, context)
    else:
        return f"Error: unknown AI_PROVIDER '{AI_PROVIDER}'"
