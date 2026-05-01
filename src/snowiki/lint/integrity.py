from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from snowiki.search.retrieval_identity import retrieval_identity_for_tokenizer
from snowiki.search.runtime_identity import (
    current_runtime_index_formats,
    current_runtime_tokenizer_name,
)
from snowiki.storage.index_manifest import (
    current_index_identity,
    explain_index_freshness,
    index_manifest_path,
    to_lint_issue_payload,
)
from snowiki.storage.provenance import raw_refs_from_record
from snowiki.storage.zones import StoragePaths

from .orphaned import find_orphaned_compiled_pages
from .stale_links import find_stale_wikilinks


def check_layer_integrity(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    issues: list[dict[str, Any]] = []

    normalized_paths = sorted(
        (base / "normalized").rglob("*.json"), key=lambda item: item.as_posix()
    )
    for path in normalized_paths:
        payload = cast(object, json.loads(path.read_text(encoding="utf-8")))
        if not isinstance(payload, Mapping):
            raw_refs: list[dict[str, object]] = []
        else:
            raw_refs = raw_refs_from_record(cast(Mapping[str, object], payload))
        if not raw_refs:
            issues.append(
                {
                    "code": "L101",
                    "check": "integrity.raw_provenance",
                    "severity": "error",
                    "path": path.relative_to(base).as_posix(),
                    "message": "normalized record missing raw provenance",
                }
            )
            continue
        for raw_ref in raw_refs:
            raw_path = raw_ref.get("path")
            if (
                isinstance(raw_path, str)
                and raw_path
                and not (base / raw_path).exists()
            ):
                issues.append(
                    {
                        "code": "L102",
                        "check": "integrity.raw_target",
                        "severity": "error",
                        "path": path.relative_to(base).as_posix(),
                        "message": f"raw provenance target missing: {raw_path}",
                    }
                )

    compiled_paths = list((base / "compiled").rglob("*.md"))
    if normalized_paths and not compiled_paths:
        issues.append(
            {
                "code": "L103",
                "check": "integrity.compiled_layer",
                "severity": "error",
                "path": "compiled",
                "message": "compiled layer missing for existing normalized records",
            }
        )

    if compiled_paths:
        issues.extend(_collect_index_manifest_issues(base))

    issues.extend(find_stale_wikilinks(base))
    issues.extend(find_orphaned_compiled_pages(base))

    return {
        "root": base.as_posix(),
        "issues": issues,
        "error_count": sum(1 for issue in issues if issue["severity"] == "error"),
    }


def _collect_index_manifest_issues(root: Path) -> list[dict[str, Any]]:
    paths = StoragePaths(root)
    manifest_path = index_manifest_path(paths)
    search_document_format, lexical_index_format = current_runtime_index_formats()
    current_identity = current_index_identity(
        paths,
        retrieval_identity_for_tokenizer(current_runtime_tokenizer_name()),
        search_document_format=search_document_format,
        lexical_index_format=lexical_index_format,
    )
    _, explanation = explain_index_freshness(
        paths,
        current_identity,
    )
    if explanation.status not in ("missing", "invalid"):
        return []
    return [
        cast(dict[str, Any], issue)
        for issue in to_lint_issue_payload(
            explanation,
            path=manifest_path.relative_to(root).as_posix(),
        )
    ]
