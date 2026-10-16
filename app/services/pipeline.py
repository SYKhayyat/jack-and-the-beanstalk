"""The generation pipeline: photo in, captioned scene image out.

Two sequential passes, because the assignment asks for two distinct
transformations and they want different things from the model:

    pass 1  cartoonify  photo -> cartoon portrait          (applies all settings)
    pass 2  compose     cartoon portrait + photo -> scene  (applies scene spec)

The cartoon portrait from pass 1 is passed into pass 2 as a reference alongside
the original photo. That double anchor is what keeps the face recognisable once
the scene action competes for the model's attention.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from app.models import CartoonSettings, GenerationResult, Scene
from app.services.image_providers.base import (
    GeneratedImage,
    ImageProvider,
    ImageRequest,
)
from app.services.prompts import build_cartoon_prompt, build_scene_prompt
from app.services.storage import GenerationStore, StoredGeneration

__all__ = ["GenerationPipeline", "PipelineOutcome"]

logger = logging.getLogger(__name__)


class PipelineOutcome:
    """A stored generation: the result plus where its files went."""

    __slots__ = ("result", "stored")

    def __init__(self, result: GenerationResult, stored: StoredGeneration) -> None:
        self.result = result
        self.stored = stored


class GenerationPipeline:
    """Runs both passes and persists the artefacts."""

    def __init__(self, provider: ImageProvider, store: GenerationStore) -> None:
        self._provider = provider
        self._store = store

    def run(
        self,
        *,
        photo_data: bytes,
        photo_media_type: str,
        scene: Scene,
        settings: CartoonSettings,
        persist: bool = True,
    ) -> PipelineOutcome:
        """Execute both passes.

        Args:
            photo_data: A validated, normalised photo (see `images.decode_upload`).
            photo_media_type: Media type of `photo_data`.
            scene: The story beat to depict.
            settings: Validated user settings.
            persist: When False, nothing is written to disk. Tests use this.

        Raises:
            ProviderError: if either pass fails.
        """
        generation_id = uuid4().hex
        warnings: list[str] = []

        cartoon_prompt = build_cartoon_prompt(settings)
        scene_prompt = build_scene_prompt(scene, settings)

        logger.info(
            "pipeline.start id=%s provider=%s scene=%s style=%s intensity=%s",
            generation_id,
            self._provider.name,
            scene.key,
            settings.cartoon_style,
            settings.cartoon_intensity,
        )

        cartoon = self._provider.generate(
            ImageRequest(
                prompt=cartoon_prompt,
                reference_images=(photo_data,),
                reference_media_types=(photo_media_type,),
                output_format="png",
                aspect_ratio=str(settings.aspect_ratio),
                label="cartoonify",
            )
        )

        # Both anchors: the stylised face we just made, and the real one.
        composed = self._provider.generate(
            ImageRequest(
                prompt=scene_prompt,
                reference_images=(cartoon.data, photo_data),
                reference_media_types=(cartoon.media_type, photo_media_type),
                output_format="png",
                aspect_ratio=str(settings.aspect_ratio),
                label="scene-compose",
            )
        )

        if len(composed.data) < 1024:
            warnings.append(
                "The returned image is suspiciously small; the provider may have "
                "returned a placeholder instead of a real generation."
            )

        result = GenerationResult(
            generation_id=generation_id,
            provider=self._provider.name,
            model=composed.model or "unknown",
            scene_key=scene.key,
            # The caption burned onto the image is exactly the spec we sent.
            caption=scene.caption,
            cartoon_prompt=cartoon_prompt,
            scene_prompt=scene_prompt,
            cartoon_image=_validated(cartoon, warnings, "cartoon portrait"),
            scene_image=_validated(composed, warnings, "scene image"),
            warnings=tuple(warnings),
        )

        stored = (
            self._store.save(result)
            if persist
            else StoredGeneration(self._store.root, generation_id)
        )
        logger.info("pipeline.done id=%s bytes=%d", generation_id, len(result.scene_image))
        return PipelineOutcome(result=result, stored=stored)


def _validated(image: GeneratedImage, warnings: list[str], label: str) -> bytes:
    """Guard against a provider that returned empty or non-image bytes."""
    if not image.data:
        warnings.append(f"The provider returned an empty {label}.")
        raise ValueError(f"Provider returned an empty {label}.")
    if not image.data.startswith(b"\x89PNG") and not image.data.startswith(b"\xff\xd8"):
        warnings.append(f"The provider returned a {label} in an unexpected format.")
    return image.data
