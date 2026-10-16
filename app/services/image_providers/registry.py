"""Provider construction.

The single place in the app that knows which concrete provider classes exist.
Everything else receives a ready `ImageProvider` from `build_provider()`.
"""

from __future__ import annotations

import logging

from app.config import ProviderName, Settings
from app.services.image_providers.base import ImageProvider, ProviderUnavailable
from app.services.image_providers.gemini import GeminiImageProvider
from app.services.image_providers.mock import MockImageProvider

__all__ = ["KNOWN_PROVIDERS", "build_provider"]

logger = logging.getLogger(__name__)

KNOWN_PROVIDERS: dict[ProviderName, type[ImageProvider]] = {
    ProviderName.MOCK: MockImageProvider,
    ProviderName.GEMINI: GeminiImageProvider,
}


def build_provider(settings: Settings) -> ImageProvider:
    """Build the provider named in settings.

    Raises `ProviderUnavailable` for an unknown name or a provider missing
    credentials, so the caller can answer 503 with something actionable.
    """
    provider_cls = KNOWN_PROVIDERS.get(settings.image_provider)
    if provider_cls is None:
        raise ProviderUnavailable(
            f"Unknown image provider {settings.image_provider!r}. "
            f"Known providers: {', '.join(sorted(p.value for p in KNOWN_PROVIDERS))}."
        )

    if provider_cls is GeminiImageProvider:
        return GeminiImageProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.generation_timeout_seconds,
        )
    return provider_cls()
