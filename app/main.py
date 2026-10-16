"""Application factory.

`create_app` is the only entry point — no module-level side effects — so tests
can build an app against a temporary storage dir and a fake provider without
touching global state.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Settings, get_settings
from app.container import build_container
from app.errors import register_exception_handlers
from app.routes import api, media, web
from app.services.image_providers.base import ImageProvider

__all__ = ["create_app"]

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app(
    settings: Settings | None = None,
    *,
    provider: ImageProvider | None = None,
) -> FastAPI:
    """Build a configured application.

    Args:
        settings: Overrides the environment-derived defaults. Tests pass one.
        provider: Overrides provider construction. Tests pass a fake.
    """
    resolved = settings or get_settings()
    _configure_logging(resolved)

    app = FastAPI(
        title="Jack and the Beanstalk",
        description=(
            "Upload a photo, cartoonify it with your own settings, and place the "
            "cartoon you into a scene from Jack and the Beanstalk."
        ),
        version="1.0.0",
        docs_url="/docs",
    )

    app.state.settings = resolved
    app.state.container = build_container(resolved, provider=provider)
    app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)

    register_exception_handlers(app)
    app.include_router(web.router)
    app.include_router(api.router)
    app.include_router(media.router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    logger.info(
        "app.ready provider=%s model=%s env=%s",
        app.state.container.provider.name,
        resolved.gemini_model if resolved.image_provider == "gemini" else "-",
        resolved.app_env,
    )
    return app


def _configure_logging(settings: Settings) -> None:
    level = logging.INFO if settings.is_production else logging.DEBUG
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
