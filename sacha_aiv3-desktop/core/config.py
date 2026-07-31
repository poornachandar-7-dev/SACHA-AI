"""
core/config.py — env-based settings (pydantic-settings).

Loads configuration from environment variables / .env file. This is the
single source of truth for API keys, model defaults, and runtime paths.
See .env.example at the project root for the full list of variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """
    All runtime configuration lives here. Values are read from environment
    variables first, then from a `.env` file at the project root if present.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App / runtime -----------------------------------------------
    app_name: str = "SACHA"
    env: Literal["dev", "prod", "test"] = "dev"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Provider API keys ---------------------------------------------
    nvidia_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)

    # --- Default routing ------------------------------------------------
    default_provider: str = "local"
    fallback_provider: str = "local"
    local_model: str = "llama3"
    local_base_url: str = "http://localhost:11434"

    # --- Telegram bridge --------------------------------------------------
    telegram_bot_token: str | None = Field(default=None)

    # --- Paths ------------------------------------------------------------
    data_dir: Path = DATA_DIR
    chat_db_path: Path = DATA_DIR / "chat.db"
    graph_db_path: Path = DATA_DIR / "graph.db"
    preferences_path: Path = DATA_DIR / "preferences.json"

    # --- Voice ------------------------------------------------------------
    stt_engine: Literal["faster_whisper", "whisper_cpp", "vosk"] = "faster_whisper"
    tts_engine: Literal["piper", "kokoro", "coqui"] = "piper"
    wakeword_phrase: str = "hey sacha"

    @field_validator("data_dir", "chat_db_path", "graph_db_path", "preferences_path", mode="before")
    @classmethod
    def _coerce_path(cls, v: str | Path) -> Path:
        return Path(v)

    def ensure_dirs(self) -> None:
        """Create data directories if they don't exist yet."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "notes").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "cache" / "embeddings").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "cache" / "audio").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so Settings is only parsed once per process."""
    return Settings()


# Convenience module-level instance for `from core.config import settings`
settings = get_settings()
