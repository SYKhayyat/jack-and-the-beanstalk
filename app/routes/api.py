"""JSON API: scene catalogue and generation."""

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter, File, Form, UploadFile, status
from pydantic import ValidationError

from app.dependencies import PipelineDep, SettingsDep
from app.errors import InvalidSettings, UnknownScene
from app.models import (
    SCENES,
    ApparentAge,
    AspectRatio,
    CartoonSettings,
    CartoonStyle,
    GenderPresentation,
    LikenessStrength,
    SkinTone,
    get_scene,
)
from app.services.images import InvalidImage, decode_upload

__all__ = ["router"]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["api"])


@router.get("/scenes")
def list_scenes() -> dict[str, object]:
    """The scenes this app can draw, for the UI to populate."""
    return {
        "scenes": [
            {
                "key": scene.key,
                "title": scene.title,
                "caption": scene.caption,
                "checklist": list(scene.must_include),
            }
            for scene in SCENES
        ]
    }


@router.get("/settings-options")
def list_settings_options() -> dict[str, object]:
    """Every enum the UI may offer, plus the default settings object."""
    return {
        "cartoon_style": _options(CartoonStyle),
        "aspect_ratio": _options(AspectRatio),
        "apparent_age": _options(ApparentAge),
        "gender_presentation": _options(GenderPresentation),
        "skin_tone": _options(SkinTone),
        "likeness_strength": _options(LikenessStrength),
        "defaults": CartoonSettings().model_dump(mode="json"),
        "limits": {"cartoon_intensity": {"min": 1, "max": 10}},
    }


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate(
    pipeline: PipelineDep,
    settings_config: SettingsDep,
    photo: UploadFile = File(..., description="A photo of a person. JPEG, PNG or WEBP."),
    scene: str = Form(..., description="Scene key, e.g. planting-seeds."),
    cartoon_intensity: int = Form(8, ge=1, le=10),
    cartoon_style: str = Form(CartoonStyle.WESTERN_CARTOON),
    likeness_strength: str = Form(LikenessStrength.STRICT),
    aspect_ratio: str = Form(AspectRatio.LANDSCAPE),
    apparent_age: str = Form(ApparentAge.AS_UPLOADED),
    gender_presentation: str = Form(GenderPresentation.AS_UPLOADED),
    skin_tone: str = Form(SkinTone.AS_UPLOADED),
    hair_style: str = Form("as_uploaded"),
    hair_color: str = Form("as_uploaded"),
    outfit: str = Form("classic storybook tunic and breeches"),
    expression: str = Form("focused and determined"),
    keep_glasses: bool = Form(True),
    keep_facial_hair: bool = Form(True),
) -> dict[str, object]:
    """Cartoonify the upload, place it in the scene, caption the result.

    Returns JSON pointing at the stored images rather than inline bytes, so the
    browser can fetch them lazily and the response stays small.
    """
    selected = get_scene(scene)
    if selected is None:
        raise UnknownScene(
            f"Unknown scene {scene!r}. Known scenes: {', '.join(s.key for s in SCENES)}."
        )

    try:
        # Form fields arrive as strings; model_validate is what turns them into
        # enums and enforces the 1..10 range, so a bad value fails here rather
        # than deep inside the prompt builder.
        cartoon_settings = CartoonSettings.model_validate(
            {
                "cartoon_intensity": cartoon_intensity,
                "cartoon_style": cartoon_style,
                "likeness_strength": likeness_strength,
                "aspect_ratio": aspect_ratio,
                "apparent_age": apparent_age,
                "gender_presentation": gender_presentation,
                "skin_tone": skin_tone,
                "hair_style": hair_style,
                "hair_color": hair_color,
                "outfit": outfit,
                "expression": expression,
                "keep_glasses": keep_glasses,
                "keep_facial_hair": keep_facial_hair,
            }
        )
    except ValidationError as exc:
        # Surfaced as 422 with field detail, same as FastAPI's own validation.
        raise InvalidSettings(
            f"Invalid cartoon settings: {exc.errors(include_url=False)}"
        ) from exc

    raw = await photo.read()
    # Bound the read before decoding: a 5GB stream should not become 5GB of RAM.
    if len(raw) > settings_config.max_upload_bytes:
        raise InvalidImage(
            f"That photo is larger than the {settings_config.max_upload_mb}MB limit."
        )
    if not raw:
        raise InvalidImage("No photo was uploaded.")

    decoded = decode_upload(raw)

    outcome = pipeline.run(
        photo_data=decoded.data,
        photo_media_type=decoded.media_type,
        scene=selected,
        settings=cartoon_settings,
    )
    result = outcome.result
    urls = outcome.stored.to_urls()

    logger.info(
        "api.generate id=%s scene=%s cartoon_bytes=%d scene_bytes=%d",
        result.generation_id,
        result.scene_key,
        len(result.cartoon_image),
        len(result.scene_image),
    )

    return {
        "generation_id": result.generation_id,
        "provider": result.provider,
        "model": result.model,
        "scene_key": result.scene_key,
        "scene_title": selected.title,
        "caption": result.caption,
        "created_at": result.created_at.isoformat(),
        "images": {
            "cartoon_url": urls["cartoon"],
            "scene_url": urls["scene"],
            "cartoon_bytes": len(result.cartoon_image),
            "scene_bytes": len(result.scene_image),
        },
        "prompts": {
            "cartoon": result.cartoon_prompt,
            "scene": result.scene_prompt,
        },
        "settings": cartoon_settings.model_dump(mode="json"),
        "warnings": list(result.warnings),
        "meta_url": urls["meta"],
    }


def _options(enum_cls: type[Enum]) -> list[dict[str, str]]:
    """Enum values as `{value, label}` pairs for the UI."""
    return [
        {"value": member.value, "label": member.value.replace("_", " ").title()}
        for member in enum_cls
    ]
