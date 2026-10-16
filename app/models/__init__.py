"""Domain models: what the app knows about scenes, settings and results.

Re-exported here so callers can `from app.models import CartoonSettings, get_scene`
without knowing the internal module layout.
"""

from app.models.generation import GenerationRequest, GenerationResult
from app.models.scenes import SCENES, Scene, get_scene
from app.models.settings import (
    ApparentAge,
    AspectRatio,
    CartoonSettings,
    CartoonStyle,
    GenderPresentation,
    LikenessStrength,
    SkinTone,
)

__all__ = [
    "SCENES",
    "ApparentAge",
    "AspectRatio",
    "CartoonSettings",
    "CartoonStyle",
    "GenderPresentation",
    "GenerationRequest",
    "GenerationResult",
    "LikenessStrength",
    "Scene",
    "SkinTone",
    "get_scene",
]
