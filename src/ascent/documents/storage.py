"""Object storage interface.

Business logic (the upload route, create_document) only ever talks to
the ObjectStorage protocol below, never to a specific implementation
directly — so a future cloud-backed adapter (e.g. S3) is a drop-in
replacement that doesn't require touching calling code. Mirrors the same
pattern already used for the AIProvider protocol (see
docs/architecture/system-architecture.md).
"""

from pathlib import Path
from typing import Protocol


class ObjectStorage(Protocol):
    def save(self, *, key: str, content: bytes) -> str:
        """Persist content under key, returning the storage key to record."""
        ...

    def retrieve(self, *, key: str) -> bytes:
        """Return the raw bytes previously stored under key."""
        ...


class LocalFileStorage:
    """Development-only backend: writes to a directory on the local
    filesystem. Only viable because the app and disk are the same
    machine — breaks down the moment there's more than one instance, or
    the app runs somewhere ephemeral. A cloud adapter implementing the
    same ObjectStorage protocol replaces this for staging/production.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, key: str, content: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def retrieve(self, *, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def _resolve(self, key: str) -> Path:
        path = (self._base_dir / key).resolve()
        if self._base_dir not in path.parents and path != self._base_dir:
            raise ValueError(f"invalid storage key (path traversal): {key!r}")
        return path