"""Central configuration. One source of truth for thresholds, LLM wiring, storage.

Loaded from environment / backend/.env. Everything has a safe default so the app
boots (and the demo runs) with zero configuration.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (parent of app/). Relative DB paths resolve against this.
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM (OpenRouter default) ---
    openrouter_api_key: str | None = Field(default=None)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "inclusionai/ling-3.0-flash-fin:free"
    fallback_models: list[str] = [
        "nvidia/nemotron-3.5-lightning:free",
        "dots-studio/dots-3-note-preview:free",
        "liquid/lfm-2.5-2.6b:free",
    ]
    llm_timeout_seconds: float = 20.0
    force_mock_critic: bool = False

    # --- Trust gate freshness thresholds (seconds) ---
    fresh_max_seconds: int = 120   # < this  -> fresh
    stale_max_seconds: int = 300   # < this  -> stale ; >= this -> invalid

    # --- Storage ---
    db_path: str = "fleet_harness.db"

    # --- Action Gateway (Layer 2) ---
    auto_approve_auto_tier: bool = True

    @property
    def resolved_db_path(self) -> str:
        """Absolute DB path. ':memory:' is passed through untouched."""
        if self.db_path == ":memory:":
            return self.db_path
        p = Path(self.db_path)
        return str(p if p.is_absolute() else BACKEND_DIR / p)

    @property
    def use_mock_critic(self) -> bool:
        """Mock when explicitly forced, or when no API key is configured."""
        return self.force_mock_critic or not self.openrouter_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()

