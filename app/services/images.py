"""Inbound image handling: validate, normalise, strip metadata.

An upload is untrusted input. Before anything else we open it with Pillow, which
both proves it really is an image (rather than a script with a .jpg name) and
gives us a chance to rewrite it. Re-encoding is not incidental: it drops EXIF,
which on phone photos routinely carries GPS coordinates of the user's home.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

__all__ = ["MAX_EDGE_PIXELS", "DecodedImage", "InvalidImage", "decode_upload"]

MAX_EDGE_PIXELS = 1536
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidImage(ValueError):
    """The upload is not a usable still image."""


@dataclass(frozen=True, slots=True)
class DecodedImage:
    """A validated, normalised upload."""

    data: bytes
    media_type: str

    @property
    def suffix(self) -> str:
        return "jpg" if self.media_type == "image/jpeg" else "png"


def decode_upload(raw: bytes) -> DecodedImage:
    """Validate and normalise an uploaded photo.

    Rejects anything that is not a still JPEG/PNG/WEBP, applies EXIF orientation,
    downsizes over-long edges, and re-encodes without metadata.

    Raises:
        InvalidImage: if the bytes are not a decodable still image.
    """
    if not raw:
        raise InvalidImage("The uploaded file was empty.")

    try:
        with Image.open(io.BytesIO(raw)) as opened:
            if getattr(opened, "is_animated", False):
                # Checked before the format allow-list so an animated GIF gets
                # the actionable message instead of "unsupported format".
                raise InvalidImage(
                    "Animated images are not supported. Upload a single still photo."
                )
            image_format = (opened.format or "").upper()
            if image_format not in _ALLOWED_FORMATS:
                raise InvalidImage(
                    f"Unsupported image format {image_format or 'unknown'!r}. "
                    "Please upload a JPEG, PNG or WEBP."
                )

            image = ImageOps.exif_transpose(opened)
            image = image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise InvalidImage(
            "That file is not a readable image. Please upload a JPEG, PNG or WEBP."
        ) from exc
    except OSError as exc:
        raise InvalidImage("That image could not be decoded; it may be corrupted.") from exc

    image.thumbnail((MAX_EDGE_PIXELS, MAX_EDGE_PIXELS), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    # Re-encoding discards the original metadata block, including EXIF GPS data.
    image.save(buffer, format="JPEG", quality=92, optimize=True)
    return DecodedImage(data=buffer.getvalue(), media_type="image/jpeg")
