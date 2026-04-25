from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import emit_error, emit_result, normalize_output_mode
from snowiki.config import get_snowiki_root
from snowiki.markdown.ingest import MarkdownIngestResult, run_markdown_ingest


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


def _error_code_for_value_error(message: str) -> str:
    return "privacy_blocked" if message.startswith("sensitive path excluded") else "ingest_failed"


def run_ingest(
    path: Path,
    *,
    root: Path,
    source_root: Path | None = None,
    rebuild: bool = False,
) -> MarkdownIngestResult:
    return run_markdown_ingest(path, root=root, source_root=source_root, rebuild=rebuild)


@click.command("ingest")
@click.argument("path", type=click.Path(exists=False, path_type=Path))
@click.option(
    "--source-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Canonical source root for Markdown identity.",
)
@root_option
@output_option
@click.option("--rebuild", is_flag=True, help="Rebuild compiled artifacts after ingest.")
def command(
    path: Path,
    source_root: Path | None,
    root: Path | None,
    output: str,
    rebuild: bool,
) -> None:
    output_mode = normalize_output_mode(output)
    root = root if root else get_snowiki_root()
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

    emit_result(
        {"ok": True, "command": "ingest", "result": result},
        output=output_mode,
        human_renderer=_render_ingest_human,
    )
