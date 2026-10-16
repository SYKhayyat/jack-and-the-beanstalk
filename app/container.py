"""Composition root.

The one module allowed to know about every concrete implementation. It reads
settings and wires the object graph; everything else receives what it needs
through FastAPI dependencies. Swapping the provider, the store location or the
pipeline is a change here and nowhere else.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings
from app.services.image_providers.base import ImageProvider
from app.services.image_providers.registry import build_provider
from app.services.pipeline import GenerationPipeline
from app.services.storage import GenerationStore

__all__ = ["Container", "build_container"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Container:
    """Everything the routes need, already constructed."""

    settings: Settings
    provider: ImageProvider
    store: GenerationStore
    pipeline: GenerationPipeline

    def provider_status(self) -> dict[str, object]:
        ok, reason = self.provider.health_check()
        return {
            "name": self.provider.name,
            "ready": ok,
            "reason": reason,
            "using_real_api": self.provider.name != "mock",
        }


def build_container(settings: Settings, provider: ImageProvider | None = None) -> Container:
    """Construct the graph. Pass `provider` to override it (tests do)."""
    resolved = provider or build_provider(settings)
    store = GenerationStore(settings.storage_dir)
    logger.info("container.built provider=%s env=%s", resolved.name, settings.app_env)
    return Container(
        settings=settings,
        provider=resolved,
        store=store,
        pipeline=GenerationPipeline(resolved, store),
    )
