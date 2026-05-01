from __future__ import annotations

from pathlib import Path

from .zones import StoragePaths


class IndexStorage:
    """Compatibility facade pointing to ``storage/index_manifest.py``.

    Manifest persistence, identity, and freshness are owned by
    ``snowiki.storage.index_manifest``. This class remains only so
    existing ``StorageEngine`` imports do not break.
    """

    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()

    @property
    def root(self) -> Path:
        return self.paths.index

    def path_for(self, *segments: str) -> Path:
        return self.root.joinpath(*segments)
