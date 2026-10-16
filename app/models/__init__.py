"""Domain models: what the app knows about scenes, settings and results.

Re-exported here so callers can `from app.models import CartoonSettings, get_scene`
without knowing the internal module layout.
"""

from app.models.feedback import (
    REJECTION_CLAUSES,
    REJECTION_LABELS,
    RejectionFeedback,
    RejectionReason,
)
from app.models.generation import GenerationRequest, GenerationResult
from app.models.scenes import SCENES, Scene, get_scene
from app.models.settings import (
    ApparentAge,
    AspectRatio,
    CartoonSettings,
    CartoonStyle,
    GenderPresentation,
    LikenessStrength,
    PortraitBackground,
    SkinTone,
)

__all__ = [
    "REJECTION_CLAUSES",
    "REJECTION_LABELS",
    "SCENES",
    "ApparentAge",
    "AspectRatio",
    "CartoonSettings",
    "CartoonStyle",
    "GenderPresentation",
    "GenerationRequest",
    "GenerationResult",
    "LikenessStrength",
    "PortraitBackground",
    "RejectionFeedback",
    "RejectionReason",
    "Scene",
    "SkinTone",
    "get_scene",
]
