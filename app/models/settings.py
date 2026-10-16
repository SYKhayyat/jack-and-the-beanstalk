"""The knobs the user can turn, as validated domain objects.

Every field here maps to something the image model can act on. Fields whose
names begin with `keep_` control whether a real-world trait of the upload is
preserved or deliberately re-stylised.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CartoonStyle(StrEnum):
    """Art direction for the stylisation pass."""

    MANGA = "manga"
    ANIME = "anime"
    WESTERN_CARTOON = "western_cartoon"
    PIXAR_LIKE = "pixar_like"
    DISNEY_LIKE = "disney_like"
    COMIC_BOOK = "comic_book"
    PENCIL_SKETCH = "pencil_sketch"
    WATERCOLOUR = "watercolour"
    VECTOR_FLAT = "vector_flat"


class ApparentAge(StrEnum):
    """Apparent age of the cartoon character."""

    AS_UPLOADED = "as_uploaded"
    CHILD = "child"
    TEEN = "teen"
    ADULT = "adult"


class GenderPresentation(StrEnum):
    """Gender presentation of the cartoon character."""

    AS_UPLOADED = "as_uploaded"
    FEMININE = "feminine"
    MASCULINE = "masculine"
    ANDROGYNOUS = "androgynous"


class SkinTone(StrEnum):
    """Skin tone of the cartoon character."""

    AS_UPLOADED = "as_uploaded"
    VERY_LIGHT = "very_light"
    LIGHT = "light"
    MEDIUM = "medium"
    TAN = "tan"
    OLIVE = "olive"
    BROWN = "brown"
    DEEP_BROWN = "deep_brown"
    DEEPEST_BROWN = "deepest_brown"


class PortraitBackground(StrEnum):
    """Background of the cartoon portrait.

    Applies to pass 1 only. It is deliberately *not* carried into the scene
    prompt: pass 2 draws the scene from its own specification, so a background
    requested here would not survive into the final image — and a busy one in
    the reference actively fights the scene's caption. See
    `prompts._portrait_background_clause`.
    """

    AS_UPLOADED = "as_uploaded"
    PLAIN = "plain"
    SOFT_COLOUR = "soft_colour"
    STORYBOOK = "storybook"


class LikenessStrength(StrEnum):
    """How hard to hold on to the uploaded face.

    This exists because "recognisably the same person" is a graded requirement.
    Dropping to ``loose`` is occasionally worth it when style and fidelity fight,
    but ``strict`` is the default.
    """

    STRICT = "strict"
    BALANCED = "balanced"
    LOOSE = "loose"


class AspectRatio(StrEnum):
    PORTRAIT = "1:1"
    LANDSCAPE = "4:3"
    TALL = "3:4"
    CINEMATIC = "16:9"


class CartoonSettings(BaseModel):
    """Validated user settings for one generation request."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    # --- how cartoon vs. real ---
    cartoon_intensity: int = Field(
        default=8,
        ge=1,
        le=10,
        description=(
            "1 = nearly photorealistic with a hint of line art; 10 = flat graphic cartoon."
        ),
    )
    likeness_strength: LikenessStrength = LikenessStrength.STRICT

    # --- art direction ---
    cartoon_style: CartoonStyle = CartoonStyle.WESTERN_CARTOON
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE
    portrait_background: PortraitBackground = PortraitBackground.PLAIN
    candidates: int = Field(
        default=1,
        ge=1,
        le=3,
        description=(
            "How many alternatives to generate for the portrait. One API call "
            "covers all of them, so three candidates is three times the cost of "
            "one, but it lets you pick rather than re-roll blindly."
        ),
    )

    # --- who the character is ---
    apparent_age: ApparentAge = ApparentAge.AS_UPLOADED
    gender_presentation: GenderPresentation = GenderPresentation.AS_UPLOADED
    skin_tone: SkinTone = SkinTone.AS_UPLOADED

    # --- details ---
    hair_style: str = Field(default="as_uploaded", max_length=80)
    hair_color: str = Field(default="as_uploaded", max_length=80)
    outfit: str = Field(default="classic storybook tunic and breeches", max_length=160)
    expression: str = Field(default="focused and determined", max_length=80)

    # --- what to keep from the photo ---
    keep_glasses: bool = True
    keep_facial_hair: bool = True

    def identity_directive(self) -> str:
        """The sentence that tells the model to preserve the uploaded face."""
        return (
            "Preserve the identity of the person in the reference image with absolute "
            "fidelity: the same bone structure, the same face shape, the same eye shape "
            "and eye colour, the same nose, the same mouth, the same eyebrows, the same "
            "hairline, the same skin tone and the same distinguishing marks such as moles, "
            "freckles, glasses and facial hair. Do not invent a new face. Do not average "
            "the face towards a generic look. A person who knows the person in the photo "
            "must recognise them immediately."
        )


__all__ = [
    "ApparentAge",
    "AspectRatio",
    "CartoonSettings",
    "CartoonStyle",
    "GenderPresentation",
    "LikenessStrength",
    "SkinTone",
]
