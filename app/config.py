"""Application configuration, loaded from environment variables.

All secrets enter the process through here and nowhere else. Nothing in this
module ever reads a value out of source code, and nothing here is ever logged.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class ProviderName(StrEnum):
    """Names of the image-generation backends the app knows how to build."""

    MOCK = "mock"
    GEMINI = "gemini"


class Settings(BaseSettings):
    """Process-wide settings.

    Reads from the real environment and from a local `.env` file (dev only).
    Field names map to upper-case environment variables, e.g. `max_upload_mb`
    is populated from `MAX_UPLOAD_MB`.
    """

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- provider ---
    image_provider: ProviderName = Field(
        default=ProviderName.MOCK,
        description="Which image backend to use. 'mock' needs no API key.",
    )
    gemini_api_key: str = Field(
        default="",
        description="Google AI Studio API key. Only needed for the gemini provider.",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash-image",
        description="Gemini image-capable model id.",
    )

    # --- app ---
    app_env: str = Field(default="development")
    max_upload_mb: int = Field(default=10, ge=1, le=50)

    storage_dir: Path = Field(
        default=BASE_DIR / "storage",
        description="Where uploads and generated images are written.",
    )

    @field_validator("storage_dir", mode="after")
    @classmethod
    def _make_storage_dir(cls, value: Path) -> Path:
        value.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so that every layer reads the same object. Tests can call
    `get_settings.cache_clear()` to force a re-read after patching the env.
    """
    return Settings()
