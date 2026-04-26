from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, TypedDict

from snowiki.compiler.taxonomy import PageType
from snowiki.lint.integrity import check_layer_integrity
from snowiki.lint.runtime import collect_structural_issues
from snowiki.markdown.source_state import collect_markdown_source_state
from snowiki.search.workspace import (
    content_freshness_identity,
    normalize_stored_tokenizer_name,
)


class StatusResult(TypedDict):
    root: str
    pages: dict[str, Any]
    sources: dict[str, Any]
    lint: dict[str, Any]
    freshness: dict[str, Any]
    manifest: dict[str, str | int | bool | None]


def _parse_scalar(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned or cleaned == "null":
        return None
    if cleaned.startswith(('"', "'")):
        try:
            return str(json.loads(cleaned))
        except json.JSONDecodeError:
            return cleaned.strip("\"'")
    return cleaned


def _frontmatter_scalars(text: str) -> dict[str, str | None]:
    if not text.startswith("---\n"):
        return {}
    delimiter_index = text.find("\n---\n", 4)
    if delimiter_index == -1:
        return {}
    fields: dict[str, str | None] = {}
    for line in text[4:delimiter_index].splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = _parse_scalar(value)
    return fields


def _load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _page_type_counts(compiled_root: Path) -> tuple[dict[str, int], str | None]:
    counts = {page_type.value: 0 for page_type in PageType}
    latest_compiled_update: str | None = None
    unknown_count = 0

    for path in sorted(compiled_root.rglob("*.md"), key=lambda item: item.as_posix()):
        frontmatter = _frontmatter_scalars(path.read_text(encoding="utf-8"))
        page_type = frontmatter.get("type")
        updated = frontmatter.get("updated")
        if isinstance(page_type, str) and page_type in counts:
            counts[page_type] += 1
        else:
            unknown_count += 1
        if isinstance(updated, str):
            latest_compiled_update = max(latest_compiled_update or updated, updated)

    if unknown_count:
        counts["unknown"] = unknown_count
    return counts, latest_compiled_update


def _source_type_counts(normalized_root: Path) -> tuple[dict[str, int], str | None]:
    counts: Counter[str] = Counter()
    latest_recorded_at: str | None = None

    for path in sorted(
        normalized_root.rglob("*.json"), key=lambda item: item.as_posix()
    ):
        source_type = "unknown"
        recorded_at: str | None = None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            counts[source_type] += 1
            continue
        if isinstance(payload, dict):
            raw_source_type = payload.get("source_type")
            if isinstance(raw_source_type, str) and raw_source_type.strip():
                source_type = raw_source_type.strip()
            raw_recorded_at = payload.get("recorded_at")
            if isinstance(raw_recorded_at, str) and raw_recorded_at.strip():
                recorded_at = raw_recorded_at.strip()
        counts[source_type] += 1
        if recorded_at is not None:
            latest_recorded_at = max(latest_recorded_at or recorded_at, recorded_at)

    return dict(sorted(counts.items())), latest_recorded_at


def _manifest_stats(
    manifest: dict[str, Any] | None,
) -> dict[str, str | int | bool | None]:
    compiled_paths = manifest.get("compiled_paths") if manifest is not None else None
    compiled_path_count = (
        len(compiled_paths) if isinstance(compiled_paths, list) else None
    )
    return {
        "path": "index/manifest.json",
        "present": manifest is not None,
        "tokenizer_name": (
            normalize_stored_tokenizer_name(manifest) if manifest else None
        ),
        "records_indexed": manifest.get("records_indexed") if manifest else None,
        "pages_indexed": manifest.get("pages_indexed") if manifest else None,
        "search_documents": manifest.get("search_documents") if manifest else None,
        "compiled_path_count": compiled_path_count,
    }


def _freshness_status(
    *,
    manifest: dict[str, Any] | None,
    current_identity: dict[str, dict[str, int]],
    latest_normalized_recorded_at: str | None,
    latest_compiled_update: str | None,
) -> dict[str, Any]:
    manifest_identity = manifest.get("content_identity") if manifest else None
    if isinstance(manifest_identity, dict):
        status = "current" if manifest_identity == current_identity else "stale"
    else:
        status = "missing"
    return {
        "status": status,
        "manifest_content_identity": manifest_identity,
        "current_content_identity": current_identity,
        "latest_normalized_recorded_at": latest_normalized_recorded_at,
        "latest_compiled_update": latest_compiled_update,
    }


def _source_freshness_status(root: Path) -> dict[str, Any]:
    report = collect_markdown_source_state(root)
    return {
        "total": report["total"],
        "counts": report["counts"],
        "stale_count": report["stale_count"],
    }


def _severity_counts(issues: Iterable[Mapping[str, object]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if isinstance(severity, str) and severity in counts:
            counts[severity] += 1
    return counts


def _status_lint_summary(root: Path) -> dict[str, Any]:
    issues: list[Mapping[str, object]] = []
    for issue in collect_structural_issues(root):
        issues.append(issue)
    for issue in check_layer_integrity(root)["issues"]:
        if isinstance(issue, Mapping):
            issues.append(issue)
    counts = _severity_counts(issues)
    summary = {**counts, "total": len(issues)}
    return {"summary": summary, "error_count": summary["error"]}


def run_status(root: Path) -> StatusResult:
    manifest = _load_manifest(root / "index" / "manifest.json")
    page_counts, latest_compiled_update = _page_type_counts(root / "compiled")
    source_counts, latest_normalized_recorded_at = _source_type_counts(root / "normalized")
    lint_result = _status_lint_summary(root)
    current_identity = content_freshness_identity(root)
    return {
        "root": root.as_posix(),
        "pages": {
            "total": sum(page_counts.values()),
            "by_type": page_counts,
        },
        "sources": {
            "total": sum(source_counts.values()),
            "by_type": source_counts,
            "freshness": _source_freshness_status(root),
        },
        "lint": {
            "summary": lint_result["summary"],
            "error_count": lint_result["error_count"],
        },
        "freshness": _freshness_status(
            manifest=manifest,
            current_identity=current_identity,
            latest_normalized_recorded_at=latest_normalized_recorded_at,
            latest_compiled_update=latest_compiled_update,
        ),
        "manifest": _manifest_stats(manifest),
    }
