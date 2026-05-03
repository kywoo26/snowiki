from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

from snowiki.storage.zones import StoragePaths

_LEGACY_PATCHABLE_NAMES = {
    "CompilerEngine",
    "build_retrieval_snapshot",
    "current_index_identity",
}


class RebuildFreshnessError(RuntimeError):
    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__(
            "rebuild snapshot freshness changed before integrity could be confirmed"
        )
        self.result = result


def run_rebuild_with_integrity(root: Path) -> dict[str, Any]:
    from snowiki.mutation import RebuildMutation
    from snowiki.mutation.finalizer import (
        RebuildFinalizationFreshnessError,
        RebuildFinalizer,
    )
    from snowiki.mutation.service import rebuild_outcome_payload

    finalizer = RebuildFinalizer.from_root(root)
    mutation = RebuildMutation(root=root, reason="legacy")
    with _LegacyMonkeypatchBridge():
        try:
            outcome = finalizer.finalize(mutation)
        except RebuildFinalizationFreshnessError as exc:
            result = cast("dict[str, Any]", rebuild_outcome_payload(exc.outcome))
            raise RebuildFreshnessError(result) from exc
    return cast("dict[str, Any]", rebuild_outcome_payload(outcome))


def verify_rebuild_integrity(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    paths = StoragePaths(base)
    compiled_before = sorted(
        path.relative_to(base).as_posix() for path in paths.compiled.rglob("*.md")
    )

    if paths.compiled.exists():
        shutil.rmtree(paths.compiled)
    if paths.index.exists():
        shutil.rmtree(paths.index)
    paths.ensure_all()

    rebuilt = run_rebuild_with_integrity(base)
    compiled_after = sorted(
        path.relative_to(base).as_posix() for path in paths.compiled.rglob("*.md")
    )
    manifest_exists = (base / rebuilt["index_manifest"]).exists()

    return {
        "root": base.as_posix(),
        "compiled_before": compiled_before,
        "compiled_after": compiled_after,
        "compiled_restored": compiled_after == rebuilt["compiled_paths"],
        "index_restored": manifest_exists,
        "content_identity": rebuilt["content_identity"],
        "current_content_identity": rebuilt["current_content_identity"],
        "freshness_restored": (
            rebuilt["content_identity"] == rebuilt["current_content_identity"]
        ),
        "result": rebuilt,
    }


class _LegacyMonkeypatchBridge:
    def __init__(self) -> None:
        self._originals: dict[str, object] = {}

    def __enter__(self) -> None:
        from snowiki.mutation import adapters

        for name in _LEGACY_PATCHABLE_NAMES:
            if name in globals():
                self._originals[name] = getattr(adapters, name)
                setattr(adapters, name, globals()[name])

    def __exit__(self, *_exc_info: object) -> None:
        from snowiki.mutation import adapters

        for name, value in self._originals.items():
            setattr(adapters, name, value)


def __getattr__(name: str) -> Any:
    if name == "CompilerEngine":
        from snowiki.compiler.engine import CompilerEngine

        return CompilerEngine
    if name == "build_retrieval_snapshot":
        from snowiki.search.runtime_retrieval import build_retrieval_snapshot

        return build_retrieval_snapshot
    if name == "current_index_identity":
        from snowiki.storage.index_manifest import current_index_identity

        return current_index_identity
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
