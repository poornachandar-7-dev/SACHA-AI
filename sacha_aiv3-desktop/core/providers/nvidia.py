"""
core/providers/nvidia.py — NVIDIA NIM provider.

NVIDIA's hosted NIM endpoint is OpenAI-API-compatible, so this inherits the
whole request/stream machinery and only sets its own key + model defaults.
"""

from __future__ import annotations

from core.providers.openai import OpenAIProvider


class NvidiaProvider(OpenAIProvider):
    name = "nvidia"
    display_name = "NVIDIA NIM"
    default_model = "meta/llama-3.1-8b-instruct"
    base_url = "https://integrate.api.nvidia.com/v1"
