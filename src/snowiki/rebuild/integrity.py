from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from snowiki.compiler.engine import CompilerEngine
from snowiki.search.workspace import (
    build_retrieval_snapshot,
    clear_query_search_index_cache,
)
from snowiki.storage.zones import StoragePaths, atomic_write_json


def _run_rebuild(root: Path) -> dict[str, Any]:
    engine = CompilerEngine(root)
    compiled_paths = engine.rebuild()
    clear_query_search_index_cache()
    snapshot = build_retrieval_snapshot(root)
    storage_paths = StoragePaths(root)
    manifest_path = storage_paths.index / "manifest.json"
    atomic_write_json(
        manifest_path,
        {
            "records_indexed": snapshot.records_indexed,
            "pages_indexed": snapshot.pages_indexed,
            "search_documents": snapshot.index.size,
            "compiled_paths": compiled_paths,
        },
    )
    return {
        "compiled_count": len(compiled_paths),
        "compiled_paths": compiled_paths,
        "index_manifest": manifest_path.relative_to(root).as_posix(),
        "pages_indexed": snapshot.pages_indexed,
        "records_indexed": snapshot.records_indexed,
    }


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

    rebuilt = _run_rebuild(base)
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
        "result": rebuilt,
    }
