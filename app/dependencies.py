"""FastAPI dependency providers.

Thin accessors from the request to the container. Keeping them here means route
functions read as controller code with no plumbing noise.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from app.config import Settings
from app.container import Container
from app.services.pipeline import GenerationPipeline
from app.services.storage import GenerationStore

__all__ = [
    "ContainerDep",
    "PipelineDep",
    "SettingsDep",
    "StoreDep",
]


def get_container(request: Request) -> Container:
    """The container attached to this app at startup."""
    return cast(Container, request.app.state.container)


ContainerDep = Annotated[Container, Depends(get_container)]


def get_app_settings(container: ContainerDep) -> Settings:
    return container.settings


def get_pipeline(container: ContainerDep) -> GenerationPipeline:
    return container.pipeline


def get_store(container: ContainerDep) -> GenerationStore:
    return container.store


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
PipelineDep = Annotated[GenerationPipeline, Depends(get_pipeline)]
StoreDep = Annotated[GenerationStore, Depends(get_store)]
