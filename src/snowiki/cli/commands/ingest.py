from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from snowiki.cli.commands.rebuild import run_rebuild
from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.config import get_snowiki_root
from snowiki.markdown import (
    MarkdownSource,
    discover_markdown_sources,
    parse_markdown_document,
)
from snowiki.privacy import PrivacyGate
from snowiki.search.workspace import clear_query_search_index_cache
from snowiki.storage.normalized import NormalizedStorage
from snowiki.storage.raw import RawStorage

_PRIVACY_GATE = PrivacyGate()


def _render_ingest_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"Ingested Markdown sources into {result['root']}",
        f"source_root: {result['source_root']}",
        f"documents_seen: {result['documents_seen']}",
        f"documents_inserted: {result['documents_inserted']}",
        f"documents_updated: {result['documents_updated']}",
        f"documents_unchanged: {result['documents_unchanged']}",
        f"documents_stale: {result['documents_stale']}",
        f"rebuild_required: {result['rebuild_required']}",
    ]
    rebuild = result.get("rebuild")
    if isinstance(rebuild, dict):
        lines.append(f"compiled_paths: {rebuild.get('compiled_count', 0)}")
    return "\n".join(lines)


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def _error_code_for_value_error(message: str) -> str:
    return "privacy_blocked" if message.startswith("sensitive path excluded") else "ingest_failed"


def _markdown_title(source: MarkdownSource, document_text: str, promoted: dict[str, Any]) -> str:
    title = promoted.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    for line in document_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
    return source.path.stem


def _markdown_summary(promoted: dict[str, Any]) -> str:
    for key in ("summary", "description"):
        value = promoted.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _store_markdown_source(
    source: MarkdownSource,
    *,
    raw_storage: RawStorage,
    normalized_storage: NormalizedStorage,
) -> dict[str, Any]:
    _PRIVACY_GATE.ensure_allowed_source(source.path)
    raw_ref = raw_storage.store_file("markdown", source.path)
    content = source.path.read_text(encoding="utf-8")
    parsed = parse_markdown_document(content)
    payload: dict[str, object] = {
        "title": _markdown_title(source, parsed.text, parsed.promoted),
        "summary": _markdown_summary(parsed.promoted),
        "text": parsed.text,
        "frontmatter": parsed.frontmatter,
        "promoted_frontmatter": parsed.promoted,
        "reserved_frontmatter": parsed.reserved,
        "source_path": source.path.as_posix(),
        "source_root": source.source_root.as_posix(),
        "relative_path": source.relative_path,
        "content_hash": str(raw_ref["sha256"]),
        "source_metadata": {
            "extension": source.path.suffix.lower(),
            "size": raw_ref["size"],
        },
    }
    result = normalized_storage.store_markdown_document(
        source_root=source.source_root.as_posix(),
        relative_path=source.relative_path,
        payload=payload,
        raw_ref=raw_ref,
        recorded_at=str(raw_ref["mtime"]),
    )
    return {
        "relative_path": source.relative_path,
        "record_id": result["id"],
        "content_hash": str(raw_ref["sha256"]),
        "status": result["status"],
        "normalized_path": result["path"],
        "raw_path": raw_ref["path"],
    }


def run_ingest(
    path: Path,
    *,
    root: Path,
    source_root: Path | None = None,
    rebuild: bool = False,
) -> dict[str, Any]:
    _PRIVACY_GATE.ensure_allowed_source(path)
    sources = discover_markdown_sources(path, source_root=source_root)
    raw_storage = RawStorage(root)
    normalized_storage = NormalizedStorage(root)
    documents = [
        _store_markdown_source(
            source,
            raw_storage=raw_storage,
            normalized_storage=normalized_storage,
        )
        for source in sources
    ]
    source_root_value = sources[0].source_root.as_posix() if sources else path.resolve().as_posix()
    result: dict[str, Any] = {
        "root": root.as_posix(),
        "source_root": source_root_value,
        "documents_seen": len(documents),
        "documents_inserted": sum(1 for item in documents if item["status"] == "inserted"),
        "documents_updated": sum(1 for item in documents if item["status"] == "updated"),
        "documents_unchanged": sum(1 for item in documents if item["status"] == "unchanged"),
        "documents_stale": 0,
        "rebuild_required": bool(documents),
        "documents": documents,
    }
    if rebuild:
        result["rebuild"] = run_rebuild(root)
        result["rebuild_required"] = False
    clear_query_search_index_cache()
    return result


@click.command("ingest")
@click.argument("path", type=click.Path(exists=False, path_type=Path))
@click.option(
    "--source-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Canonical source root for Markdown identity.",
)
@click.option(
    "--root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Snowiki storage root (defaults to ~/.snowiki)",
)
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
@click.option("--rebuild", is_flag=True, help="Rebuild compiled artifacts after ingest.")
def command(
    path: Path,
    source_root: Path | None,
    root: Path | None,
    output: str,
    rebuild: bool,
) -> None:
    output_mode = _normalize_output_mode(output)
    root = root if root else get_snowiki_root()
    result: dict[str, Any] | None = None
    try:
        result = run_ingest(
            path,
            source_root=source_root,
            root=root,
            rebuild=rebuild,
        )
    except click.ClickException as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="ingest_failed",
            details={"path": path.as_posix()},
        )
    except ValueError as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code=_error_code_for_value_error(str(exc)),
            details={"path": path.as_posix()},
        )
    except Exception as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="unexpected_error",
            details={"path": path.as_posix()},
        )
    if result is None:
        raise RuntimeError("ingest did not produce a result")

    emit_result(
        {"ok": True, "command": "ingest", "result": result},
        output=output_mode,
        human_renderer=_render_ingest_human,
    )
