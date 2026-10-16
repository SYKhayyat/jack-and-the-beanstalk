"""Prompt construction.

This module is the app's actual intellectual core. The API call is trivial;
deciding *what to say* is the work, and it is why this file is pure functions
over plain data with no I/O — so every word of it is unit-testable.

The pipeline runs two passes:

1. `build_cartoon_prompt` — stylise the uploaded photo into a cartoon portrait,
   applying every user setting. The output is the identity anchor.
2. `build_scene_prompt` — place that cartoon person into the requested scene,
   re-stating the identity constraints because models drift when the scene
   action is interesting.

Passing the original photo alongside the cartoon portrait in pass 2 gives the
model two independent anchors on the same face, which is the single biggest
lever on "does this look like the person".
"""

from __future__ import annotations

from app.models import CartoonSettings, CartoonStyle, Scene
from app.models.settings import (
    ApparentAge,
    AspectRatio,
    GenderPresentation,
    LikenessStrength,
    SkinTone,
)

__all__ = [
    "NEGATIVE_PROMPT_TAIL",
    "build_cartoon_prompt",
    "build_scene_prompt",
]

# Kept in one place so every pass rejects the same failure modes: text artefacts
# (which would fight the caption) and extra people (which would break identity).
NEGATIVE_PROMPT_TAIL = (
    "Do not include any text, letters, numbers, watermark, signature, logo, caption "
    "or speech bubble anywhere in the image — the picture must be a clean illustration "
    "with no writing in it. Do not include any other people or characters; only the one "
    "person described above. Do not include extra limbs, extra fingers, duplicate faces "
    "or distorted hands."
)

_STYLE_DESCRIPTIONS: dict[CartoonStyle, str] = {
    CartoonStyle.MANGA: (
        "black-and-white Japanese manga style, crisp confident ink linework, heavy black "
        "outlines, screentone dot shading, dramatic speed lines, high-contrast monochrome, "
        "large expressive eyes, hand-drawn manga panel aesthetic"
    ),
    CartoonStyle.ANIME: (
        "modern Japanese anime style, clean cel shading with two-tone shadows, bright "
        "saturated colours, soft gradient skies, large sparkling expressive eyes, delicate "
        "linework, detailed hair strands, polished studio-anime finish"
    ),
    CartoonStyle.WESTERN_CARTOON: (
        "classic hand-drawn western cartoon style, bold rounded ink outlines, flat blocks "
        "of warm colour, simplified friendly shapes, gentle squash-and-stretch, vintage "
        "storybook cel animation look"
    ),
    CartoonStyle.PIXAR_LIKE: (
        "high-end 3D animated feature style, soft global illumination, subsurface-scattered "
        "skin, large expressive eyes with real catchlights, appealing stylised proportions, "
        "shallow depth of field, warm cinematic colour grading, Pixar-like character design"
    ),
    CartoonStyle.DISNEY_LIKE: (
        "Disney-like classic hand-painted 2D animation style, fluid confident curves, soft "
        "painted backgrounds, expressive appealing character design, warm colour, generous "
        "rounded shapes, storybook cel animation finish"
    ),
    CartoonStyle.COMIC_BOOK: (
        "American comic book style, heavy black ink outlines, halftone Ben-Day dot shading, "
        "flat saturated four-colour palette, dynamic heroic composition, bold panel energy"
    ),
    CartoonStyle.PENCIL_SKETCH: (
        "graphite pencil sketch, confident cross-hatched shading, visible pencil grain, "
        "loose expressive linework on warm off-white paper, monochrome hand-drawn study"
    ),
    CartoonStyle.WATERCOLOUR: (
        "traditional watercolour painting, soft wet-on-wet colour bleeds, visible paper "
        "texture, translucent layered washes, loose painterly edges, delicate ink accents"
    ),
    CartoonStyle.VECTOR_FLAT: (
        "flat vector illustration, perfectly smooth geometric shapes, no gradients, "
        "no texture, bold clean silhouettes, bright modern palette, minimal "
        "scalable-graphics look"
    ),
}

_ASPECT_HINTS: dict[AspectRatio, str] = {
    AspectRatio.PORTRAIT: "square 1:1 composition",
    AspectRatio.LANDSCAPE: "4:3 landscape composition",
    AspectRatio.TALL: "tall 3:4 portrait composition",
    AspectRatio.CINEMATIC: "wide cinematic 16:9 composition",
}

_AGE_DESCRIPTIONS: dict[ApparentAge, str] = {
    ApparentAge.AS_UPLOADED: "Keep the subject at the same apparent age as in the photo.",
    ApparentAge.CHILD: "Depict the subject as a child around 10 years old.",
    ApparentAge.TEEN: "Depict the subject as a teenager around 16 years old.",
    ApparentAge.ADULT: "Depict the subject as a grown adult around 30 years old.",
}

_GENDER_DESCRIPTIONS: dict[GenderPresentation, str] = {
    GenderPresentation.AS_UPLOADED: (
        "Match the gender presentation of the person in the photo."
    ),
    GenderPresentation.FEMININE: (
        "Present the character with a feminine gender presentation, redesigned "
        "consistently from the same facial bone structure."
    ),
    GenderPresentation.MASCULINE: (
        "Present the character with a masculine gender presentation, redesigned "
        "consistently from the same facial bone structure."
    ),
    GenderPresentation.ANDROGYNOUS: (
        "Present the character as deliberately androgynous, keeping the facial bone "
        "structure from the photo and reading as gender-neutral."
    ),
}

_SKIN_DESCRIPTIONS: dict[SkinTone, str] = {
    SkinTone.AS_UPLOADED: "Keep the exact natural skin tone from the photo.",
    SkinTone.VERY_LIGHT: "Render the skin very light and fair.",
    SkinTone.LIGHT: "Render the skin light and fair.",
    SkinTone.MEDIUM: "Render the skin a medium beige tone.",
    SkinTone.TAN: "Render the skin warm and tanned.",
    SkinTone.OLIVE: "Render the skin an olive tone.",
    SkinTone.BROWN: "Render the skin a rich brown tone.",
    SkinTone.DEEP_BROWN: "Render the skin a deep brown tone.",
    SkinTone.DEEPEST_BROWN: "Render the skin the deepest rich brown tone.",
}

_LIKENESS_EMPHASIS: dict[LikenessStrength, str] = {
    LikenessStrength.STRICT: (
        "Match the uploaded face as precisely as a photograph would. Small deviations "
        "in the eyes, nose, jaw or hairline are failures, not interpretation."
    ),
    LikenessStrength.BALANCED: (
        "Match the uploaded face closely while allowing small stylised departures."
    ),
    LikenessStrength.LOOSE: (
        "Keep the uploaded face recognisable, letting the art style shape it somewhat more."
    ),
}

# The cartoon-vs-real dial, sampled at each intensity from 1 to 10. Written out
# rather than interpolated so each step has human-vetted language behind it —
# the alternative, a numeric formula, produced mush at the middle values.
_INTENSITY_DESCRIPTIONS: dict[int, str] = {
    1: (
        "barely stylised: keep the photograph almost intact, adding only delicate line "
        "work over the eyes and a very light ink trace on the contours"
    ),
    2: (
        "very lightly stylised: retain photographic shading and texture, with soft "
        "ink lines defining the eyes, brows and jaw"
    ),
    3: (
        "lightly stylised: photographic likeness with visible outline lines and slightly "
        "simplified facial shapes"
    ),
    4: (
        "moderately stylised: painterly realism with clear outlines and gently simplified "
        "features, still unmistakably the same person"
    ),
    5: (
        "about half stylised: an even balance between realistic rendering and cartoon "
        "simplification, with clean outlines and simplified shapes"
    ),
    6: (
        "clearly stylised: unmistakable cartoon rendering, but the facial structure and "
        "every identifying feature are still faithful to the photo"
    ),
    7: (
        "strongly stylised: bold cartoon shapes and confident outlines, with the face "
        "still unmistakably the person in the photo"
    ),
    8: (
        "very strongly stylised: graphic cartoon shapes, heavy clean outlines and flat "
        "colour, while the face remains instantly recognisable as the same person"
    ),
    9: (
        "almost entirely graphic: bold flat shapes and thick outlines, the design reads "
        "as a caricature that a friend would still identify without hesitation"
    ),
    10: (
        "fully graphic: maximally simplified bold shapes, thick outlines and flat poster "
        "colour, reduced to the most iconic version of this specific person's face"
    ),
}


def _intensity_text(intensity: int) -> str:
    return _INTENSITY_DESCRIPTIONS[max(1, min(10, intensity))]


def _photoreal_keywords(intensity: int) -> str:
    """Terms to suppress as the dial turns away from photorealism."""
    if intensity <= 3:
        return ""
    if intensity <= 5:
        return "Avoid heavy simplification of the face; keep features readable."
    return (
        "Simplify boldly and graphically. Do not fall back towards photographic "
        "rendering or 3D realism."
    )


def _accessory_directives(settings: CartoonSettings) -> list[str]:
    directives: list[str] = []
    if settings.keep_glasses:
        directives.append(
            "If the person in the photo wears glasses, keep those glasses on the "
            "character, drawn in the same style as the rest of the image."
        )
    else:
        directives.append("Remove any glasses or sunglasses.")
    if settings.keep_facial_hair:
        directives.append(
            "If the person has facial hair, keep it, drawn in the same style as the "
            "rest of the image."
        )
    else:
        directives.append("Remove any facial hair.")
    return directives


def _common_character_block(settings: CartoonSettings) -> str:
    """The lines describing *who the character is*, shared by both passes."""
    return " ".join(
        [
            _AGE_DESCRIPTIONS[settings.apparent_age],
            _GENDER_DESCRIPTIONS[settings.gender_presentation],
            _SKIN_DESCRIPTIONS[settings.skin_tone],
            f"Hair style: {settings.hair_style}.",
            f"Hair colour: {settings.hair_color}.",
            f"Wearing {settings.outfit}.",
            f"Facial expression: {settings.expression}.",
            *_accessory_directives(settings),
        ]
    )


def build_cartoon_prompt(settings: CartoonSettings) -> str:
    """Prompt for pass 1: stylise the uploaded photo into a cartoon portrait."""
    style_text = _STYLE_DESCRIPTIONS[settings.cartoon_style]
    sections = [
        "TASK: Turn the person in the supplied photograph into a single "
        "character portrait, in the art style described below.",
        settings.identity_directive(),
        _LIKENESS_EMPHASIS[settings.likeness_strength],
        _common_character_block(settings),
        "STYLISATION LEVEL (user setting, honour it exactly): "
        f"{_intensity_text(settings.cartoon_intensity)}.",
        _photoreal_keywords(settings.cartoon_intensity),
        f"ART STYLE: {style_text}.",
        "FRAMING: a head-and-shoulders portrait facing the camera, head and face "
        "large and unobstructed in the centre of the frame, eyes fully visible and "
        "not hidden by hair or shadow, plain simple background that does not compete "
        "with the face, even flattering light on the face so every feature reads clearly.",
        f"COMPOSITION: {_ASPECT_HINTS[settings.aspect_ratio]}.",
        NEGATIVE_PROMPT_TAIL,
    ]
    return _join_sections(sections)


def build_scene_prompt(scene: Scene, settings: CartoonSettings) -> str:
    """Prompt for pass 2: place the cartoon character into the scene.

    The first reference image is the cartoon portrait from pass 1; the second,
    when supplied, is the original photograph. They are the same person, and the
    model should treat them as a matched pair.
    """
    style_text = _STYLE_DESCRIPTIONS[settings.cartoon_style]
    sections = [
        "TASK: Draw the character from the reference images as Jack, performing the "
        "scene specified below. The reference images are the same person: the first is "
        "their cartoon portrait, the second is their original photograph.",
        settings.identity_directive(),
        _LIKENESS_EMPHASIS[settings.likeness_strength],
        # Repeated rather than assumed: this is what models drop when the scene
        # action is exciting, and it is the first of the two graded requirements.
        f"SCENE TO DRAW (this is the entire content of the picture): {scene.caption}",
        f"WHAT THE CHARACTER IS DOING: {scene.subject_action}. "
        f"Get this action right — it is what the scene is about.",
        f"WHERE: {scene.environment}.",
        f"LIGHTING: {scene.time_of_day}.",
        f"CAMERA: {scene.camera}.",
        scene.checklist,
        _common_character_block(settings),
        "STYLISATION LEVEL (user setting, honour it exactly): "
        f"{_intensity_text(settings.cartoon_intensity)}.",
        _photoreal_keywords(settings.cartoon_intensity),
        f"ART STYLE: {style_text}.",
        f"COMPOSITION: {_ASPECT_HINTS[settings.aspect_ratio]}.",
        _avoid_clause(scene),
        NEGATIVE_PROMPT_TAIL,
    ]
    return _join_sections(sections)


def _avoid_clause(scene: Scene) -> str:
    if not scene.must_avoid:
        return ""
    items = ", ".join(scene.must_avoid)
    return f"Do not show any of the following: {items}."


def _join_sections(sections: list[str]) -> str:
    """Join non-empty sections into a prompt, one labelled paragraph each."""
    return "\n\n".join(section.strip() for section in sections if section.strip())
