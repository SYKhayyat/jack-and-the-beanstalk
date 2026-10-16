"""Filesystem persistence for generation artefacts.

Kept behind a small interface so the pipeline never touches paths. In tests it is
backed by a tmp dir; in production by `settings.storage_dir`.

Note for deployment: Render's filesystem is ephemeral, so artefacts survive only
until the container is replaced. That is acceptable here because the user sees
their results immediately in the same response cycle.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models import GenerationResult

__all__ = ["GenerationStore", "StoredGeneration"]


class StoredGeneration:
    """Where one generation's artefacts live on disk."""

    def __init__(self, root: Path, generation_id: str) -> None:
        self.root = root
        self.generation_id = generation_id

    @property
    def directory(self) -> Path:
        return self.root / self.generation_id

    def path(self, filename: str) -> Path:
        return self.directory / filename

    def to_urls(self) -> dict[str, str]:
        base = f"/media/{self.generation_id}"
        return {
            "cartoon": f"{base}/cartoon",
            "scene": f"{base}/scene",
            "meta": f"{base}/meta.json",
        }


class GenerationStore:
    """Reads and writes generations under a root directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, result: GenerationResult) -> StoredGeneration:
        """Persist both images and a JSON sidecar describing the run."""
        stored = StoredGeneration(self.root, result.generation_id)
        stored.directory.mkdir(parents=True, exist_ok=True)

        cartoon_suffix = "jpg" if result.cartoon_image[:2] == b"\xff\xd8" else "png"
        scene_suffix = "jpg" if result.scene_image[:2] == b"\xff\xd8" else "png"

        stored.path(f"cartoon.{cartoon_suffix}").write_bytes(result.cartoon_image)
        stored.path(f"scene.{scene_suffix}").write_bytes(result.scene_image)

        meta = {
            "generation_id": result.generation_id,
            "provider": result.provider,
            "model": result.model,
            "scene_key": result.scene_key,
            "caption": result.caption,
            "cartoon_prompt": result.cartoon_prompt,
            "scene_prompt": result.scene_prompt,
            "created_at": result.created_at.isoformat(),
            "warnings": list(result.warnings),
        }
        stored.path("meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return stored

    def read_meta(self, generation_id: str) -> dict[str, object] | None:
        """Load a generation's metadata, or None if it is gone or malformed."""
        if not _is_safe_id(generation_id):
            return None
        path = StoredGeneration(self.root, generation_id).path("meta.json")
        if not path.is_file():
            return None
        try:
            parsed: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return parsed

    def read_image(self, generation_id: str, stem: str) -> bytes | None:
        """Load a stored image by stem ("cartoon" or "scene"), or None."""
        if not _is_safe_id(generation_id) or stem not in {"cartoon", "scene"}:
            return None
        directory = StoredGeneration(self.root, generation_id).directory
        for suffix in ("png", "jpg"):
            candidate = directory / f"{stem}.{suffix}"
            if candidate.is_file():
                return candidate.read_bytes()
        return None

    def delete(self, generation_id: str) -> None:
        if not _is_safe_id(generation_id):
            return
        stored = StoredGeneration(self.root, generation_id)
        if not stored.directory.is_dir():
            return
        for child in stored.directory.iterdir():
            if child.is_file():
                child.unlink()
        stored.directory.rmdir()


def _is_safe_id(generation_id: str) -> bool:
    """Generation ids become path segments, so they must not contain any."""
    if not generation_id or generation_id.startswith("."):
        return False
    return not any(part in generation_id for part in ("/", "\\", "..", "\x00"))
