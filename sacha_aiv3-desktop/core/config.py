"""
core/config.py — env-based settings (pydantic-settings).

Loads configuration from environment variables / .env file. This is the
single source of truth for API keys, model defaults, and runtime paths.
See .env.example at the project root for the full list of variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

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
    # Derived from data_dir in model_post_init; None → data_dir-based default.
    chat_db_path: Path | None = Field(default=None)
    graph_db_path: Path | None = Field(default=None)
    preferences_path: Path | None = Field(default=None)

    # --- Voice ------------------------------------------------------------
    stt_engine: Literal["faster_whisper", "whisper_cpp", "vosk"] = "faster_whisper"
    tts_engine: Literal["piper", "kokoro", "coqui"] = "piper"
    wakeword_phrase: str = "hey sacha"
    whisper_model_size: str = "base"
    audio_sample_rate: int = 16000

    # Model files (downloaded / placed by the user in data/models)
    piper_model_path: Path | None = Field(default=None)
    vosk_model_path: Path | None = Field(default=None)

    @field_validator("data_dir", "chat_db_path", "graph_db_path", "preferences_path", mode="before")
    @classmethod
    def _coerce_path(cls, v: str | Path | None) -> Path | None:
        return None if v is None else Path(v)

    @field_validator("piper_model_path", "vosk_model_path", mode="before")
    @classmethod
    def _coerce_optional_path(cls, v: str | Path | None) -> Path | None:
        return None if v in (None, "", "None") else Path(v)

    def model_post_init(self, __context: Any) -> None:
        """Fill derived paths from data_dir unless explicitly overridden."""
        data = Path(self.data_dir)
        if self.chat_db_path is None:
            self.chat_db_path = data / "chat.db"
        if self.graph_db_path is None:
            self.graph_db_path = data / "graph.db"
        if self.preferences_path is None:
            self.preferences_path = data / "preferences.json"

    def models_dir(self) -> Path:
        """Directory for downloaded voice / STT model files."""
        return Path(self.data_dir) / "models"

    def ensure_dirs(self) -> None:
        """Create data directories if they don't exist yet."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "notes").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "models").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "cache" / "embeddings").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "cache" / "audio").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "cache" / "screenshots").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so Settings is only parsed once per process."""
    return Settings()


# Convenience module-level instance for `from core.config import settings`
settings = get_settings()
