from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.compiler.taxonomy import PageType
from snowiki.config import get_snowiki_root
from snowiki.lint import run_lint
from snowiki.search.workspace import (
    content_freshness_identity,
    normalize_stored_tokenizer_name,
)


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


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


def _source_type_counts(
    normalized_root: Path,
) -> tuple[dict[str, int], str | None]:
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


def run_status(root: Path) -> dict[str, Any]:
    manifest = _load_manifest(root / "index" / "manifest.json")
    page_counts, latest_compiled_update = _page_type_counts(root / "compiled")
    source_counts, latest_normalized_recorded_at = _source_type_counts(
        root / "normalized"
    )
    lint_result = run_lint(root)
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
        "candidate_matrix": [],
    }


def _render_mapping_line(label: str, values: dict[str, int]) -> str:
    rendered = ", ".join(f"{key}: {values[key]}" for key in values)
    return f"{label}: {rendered}" if rendered else f"{label}: none"


def _render_status_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    pages = result["pages"]
    sources = result["sources"]
    lint = result["lint"]
    freshness = result["freshness"]
    manifest = result["manifest"]
    summary = lint["summary"]
    candidate_matrix = result.get("candidate_matrix", [])

    current_tokenizer = freshness["current_content_identity"].get("tokenizer", {})
    tokenizer_name = current_tokenizer.get("name", "n/a")

    freshness_bits = [
        f"state={freshness['status']}",
        f"tokenizer={tokenizer_name}",
        f"latest normalized={freshness['latest_normalized_recorded_at'] or 'n/a'}",
        f"latest compiled={freshness['latest_compiled_update'] or 'n/a'}",
    ]
    manifest_bits = [
        f"tokenizer={manifest['tokenizer_name'] or 'n/a'}",
        f"records indexed={manifest['records_indexed'] if manifest['records_indexed'] is not None else 'n/a'}",
        f"pages indexed={manifest['pages_indexed'] if manifest['pages_indexed'] is not None else 'n/a'}",
        f"search documents={manifest['search_documents'] if manifest['search_documents'] is not None else 'n/a'}",
        f"compiled paths={manifest['compiled_path_count'] if manifest['compiled_path_count'] is not None else 'n/a'}",
    ]

    lines = [
        f"Snowiki status for {result['root']}",
        f"Pages: {pages['total']} total",
        _render_mapping_line("  By type", pages["by_type"]),
        f"Sources: {sources['total']} total",
        _render_mapping_line("  By source", sources["by_type"]),
        (
            "Lint: "
            f"{summary['error']} errors, {summary['warning']} warnings, {summary['info']} info"
        ),
        f"Freshness: {', '.join(freshness_bits)}",
        f"Manifest: {', '.join(manifest_bits)}",
    ]

    if candidate_matrix:
        lines.append("Tokenizer Candidates:")
        for candidate in candidate_matrix:
            name = candidate.get("candidate_name", "unknown")
            role = candidate.get("role", "unknown")
            status = candidate.get("admission_status", "unknown")
            lines.append(f"  - {name}: role={role}, status={status}")

    return "\n".join(lines)


@click.command("status")
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
@click.option(
    "--root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Snowiki storage root (defaults to ~/.snowiki)",
)
def command(output: str, root: Path | None) -> None:
    output_mode = _normalize_output_mode(output)
    result: dict[str, Any] | None = None
    try:
        result = run_status(root if root else get_snowiki_root())
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="status_failed")
    if result is None:
        raise RuntimeError("status did not produce a result")
    emit_result(
        {"ok": True, "command": "status", "result": result},
        output=output_mode,
        human_renderer=_render_status_human,
    )
