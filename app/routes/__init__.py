"""HTTP layer. Controllers only: parse input, call services, render a response."""

from app.routes import api, media, web

__all__ = ["api", "media", "web"]
