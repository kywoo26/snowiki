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
from snowiki.search.retrieval_identity import retrieval_identity_for_tokenizer
from snowiki.search.runtime_identity import (
    current_runtime_index_formats,
    current_runtime_tokenizer_name,
)
from snowiki.storage.index_manifest import (
    current_index_identity,
    explain_index_freshness,
    to_manifest_stats_payload,
    to_status_payload,
)
from snowiki.storage.zones import StoragePaths


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
    paths = StoragePaths(root)
    manifest_present = (paths.index / "manifest.json").exists()
    page_counts, latest_compiled_update = _page_type_counts(root / "compiled")
    source_counts, latest_normalized_recorded_at = _source_type_counts(root / "normalized")
    lint_result = _status_lint_summary(root)
    search_document_format, lexical_index_format = current_runtime_index_formats()
    current_identity = current_index_identity(
        paths,
        retrieval_identity_for_tokenizer(current_runtime_tokenizer_name()),
        search_document_format=search_document_format,
        lexical_index_format=lexical_index_format,
    )
    manifest, freshness_explanation = explain_index_freshness(
        paths,
        current_identity,
    )
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
        "freshness": to_status_payload(
            manifest=manifest,
            current=current_identity,
            explanation=freshness_explanation,
            latest_normalized_recorded_at=latest_normalized_recorded_at,
            latest_compiled_update=latest_compiled_update,
        ),
        "manifest": to_manifest_stats_payload(manifest, present=manifest_present),
    }
