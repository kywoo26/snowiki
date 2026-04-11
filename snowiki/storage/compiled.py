from __future__ import annotations

from pathlib import Path

from .zones import StoragePaths


class CompiledStorage:
    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()

    @property
    def root(self) -> Path:
        return self.paths.compiled

    def path_for(self, *segments: str) -> Path:
        return self.root.joinpath(*segments)

    def store_page(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError("CompiledStorage is a placeholder until Task 6.")
