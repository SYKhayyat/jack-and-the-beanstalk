"""Application-level exceptions and their HTTP translation.

Routes raise; this module decides the status code. That keeps controller
functions free of try/except ladders and guarantees an error never leaks a
stack trace or an API key to the client.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.image_providers.base import ProviderError, ProviderUnavailable
from app.services.images import InvalidImage

__all__ = [
    "AppError",
    "InvalidSettings",
    "UnknownScene",
    "register_exception_handlers",
]

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for errors that map cleanly onto an HTTP response."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "app_error"


class UnknownScene(AppError):
    """The requested scene key is not in the catalogue."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "unknown_scene"


class InvalidSettings(AppError):
    """The submitted cartoon settings did not validate."""

    status_code = 422
    error_code = "invalid_settings"


class GenerationTimeout(AppError):
    """A generation ran past the configured wall-clock ceiling.

    504 rather than 500: the server is fine, the upstream work simply did not
    finish in time. Safe to retry, and nothing partial is served.
    """

    status_code = 504
    error_code = "generation_timeout"


class ServerBusy(AppError):
    """Every generation slot was occupied, so this request was not started.

    429 with a Retry-After hint. Nothing was sent to the image model, so this
    costs the user nothing.
    """

    status_code = 429
    error_code = "server_busy"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the app's error contract to a FastAPI instance."""

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.info("app_error %s: %s", exc.error_code, exc)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "detail": str(exc)},
        )

    @app.exception_handler(ProviderUnavailable)
    async def _unavailable(_: Request, exc: ProviderUnavailable) -> JSONResponse:
        logger.warning("provider.unavailable: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "provider_unavailable",
                "detail": str(exc),
                "hint": "Set IMAGE_PROVIDER=mock to run the app without an API key.",
            },
        )

    @app.exception_handler(ProviderError)
    async def _provider_failed(_: Request, exc: ProviderError) -> JSONResponse:
        logger.exception("provider.error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": "provider_error",
                "detail": str(exc),
                "hint": "The image provider was reached but failed. Check the logs.",
            },
        )

    @app.exception_handler(InvalidImage)
    async def _bad_image(_: Request, exc: InvalidImage) -> JSONResponse:
        logger.info("upload.rejected: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_image", "detail": str(exc)},
        )
