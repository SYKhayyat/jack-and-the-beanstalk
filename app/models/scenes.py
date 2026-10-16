"""Scene specifications from Jack and the Beanstalk.

A `Scene` is pure data: the prose specification sent to the image model, plus
the caption burned onto the result. Adding a third scene means adding one entry
to `SCENES` — no code changes anywhere else in the app.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Scene:
    """One story beat.

    Attributes:
        key: Stable identifier used in URLs and the API payload.
        title: Short human label for the UI.
        caption: The scene specification as sent to the model. This exact text
            is burned onto the generated image, which is what the assignment's
            "captioned with the scene specification you sent" requirement asks for.
        subject_action: What the character is physically doing. This is the part
            the model most often gets wrong, so it is kept separate and gets its
            own emphatic clause in the prompt.
        environment: Where the beat happens.
        time_of_day: Drives lighting and palette.
        camera: Framing and lens language.
        must_include: Concrete objects that must be visible. Also emitted as an
            explicit checklist so the model treats them as requirements.
        must_avoid: Things that would make the image unfaithful to the caption.
    """

    key: str
    title: str
    caption: str
    subject_action: str
    environment: str
    time_of_day: str
    camera: str
    must_include: tuple[str, ...] = field(default_factory=tuple)
    must_avoid: tuple[str, ...] = field(default_factory=tuple)

    @property
    def checklist(self) -> str:
        if not self.must_include:
            return ""
        items = ", ".join(f'"{item}"' for item in self.must_include)
        return f"Every one of these must be clearly visible: {items}."


SCENES: tuple[Scene, ...] = (
    Scene(
        key="planting-seeds",
        title="Jack is planting the seeds",
        caption=(
            "Jack is planting the seeds. Young Jack kneels in a cottage garden, "
            "pressing a handful of magic beans into a freshly dug hole in dark soil, "
            "beside his mother's cottage with a thatched roof behind him."
        ),
        subject_action=(
            "kneeling on both knees in the soil, bent forward, one hand pushing beans "
            "down into the hole and the other steadying himself on the ground"
        ),
        environment=(
            "the dirt patch behind his mother's small stone cottage, a wooden fence and "
            "a low stone wall at the edge of the plot, garden tools and an empty clay pot "
            "set aside, the magic beans glowing faintly in the hole"
        ),
        time_of_day="early morning, soft low golden sunlight and long cool shadows",
        camera=(
            "three-quarter eye-level medium-wide shot, subject sharp in the centre third, "
            "gentle depth of field on the cottage behind"
        ),
        must_include=(
            "magic beans being placed into the soil",
            "a dug hole in dark earth",
            "the thatched cottage",
            "Jack kneeling",
        ),
        must_avoid=(
            "a beanstalk",
            "a giant",
            "Jack climbing or standing upright",
            "text, watermark, logo or speech bubble",
        ),
    ),
    Scene(
        key="climbing-beanstalk",
        title="Jack is climbing the beanstalk",
        caption=(
            "Jack is climbing the beanstalk. Jack grips the thick twisting vine and "
            "clambers high above the clouds, the stalk vanishing up into a bright sky "
            "while the cottage and fields shrink to a toy-sized patchwork far below."
        ),
        subject_action=(
            "climbing, both hands wrapped around the vine and one knee hooked around it, "
            "body pressed to the stalk and looking upward toward the clouds"
        ),
        environment=(
            "a colossal spiralling green beanstalk rising out of the farmland below, "
            "clouds and pale blue sky all around, a vast castle with golden turrets "
            "faintly visible high above through a break in the clouds, tiny cottage and "
            "fields far beneath"
        ),
        time_of_day="bright clear morning, sunlit clouds and luminous green stalk",
        camera=(
            "dramatic vertical low-angle looking up the length of the stalk, extreme "
            "scale contrast between the tiny earth below and Jack high in the sky"
        ),
        must_include=(
            "a colossal beanstalk Jack is gripping",
            "clouds",
            "the ground and cottage far below",
            "hands and feet in a climbing position",
        ),
        must_avoid=(
            "Jack planting or kneeling on the ground",
            "a giant",
            "the chicken or the golden hen",
            "text, watermark, logo or speech bubble",
        ),
    ),
)

_SCENES_BY_KEY: dict[str, Scene] = {scene.key: scene for scene in SCENES}


def get_scene(key: str) -> Scene | None:
    """Look up a scene by key, or None if unknown."""
    return _SCENES_BY_KEY.get(key)
