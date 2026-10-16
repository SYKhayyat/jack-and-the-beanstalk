"""Server-rendered pages."""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import ContainerDep
from app.models import (
    SCENES,
    ApparentAge,
    AspectRatio,
    CartoonSettings,
    CartoonStyle,
    GenderPresentation,
    LikenessStrength,
    SkinTone,
)

__all__ = ["router"]

router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request, container: ContainerDep) -> HTMLResponse:
    """The single-page UI: upload, settings, scene picker, results."""
    templates: Jinja2Templates = request.app.state.templates
    defaults = CartoonSettings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "scenes": SCENES,
            "defaults": defaults,
            "styles": _choices(CartoonStyle),
            "aspect_ratios": _choices(AspectRatio),
            "ages": _choices(ApparentAge),
            "genders": _choices(GenderPresentation),
            "skin_tones": _choices(SkinTone),
            "likeness_levels": _choices(LikenessStrength),
            "max_upload_mb": container.settings.max_upload_mb,
            "provider": container.provider_status(),
        },
    )


@router.get("/healthz")
def healthz(container: ContainerDep) -> dict[str, object]:
    """Liveness plus which provider is active. Safe to expose."""
    status_payload = container.provider_status()
    return {"status": "ok", "provider": status_payload}


def _choices(enum_cls: type[Enum]) -> list[tuple[str, str]]:
    """Enum members as `(value, label)` pairs for the template.

    Defined here rather than in the template so the view stays presentation-only.
    """
    return [(member.value, member.value.replace("_", " ").title()) for member in enum_cls]
