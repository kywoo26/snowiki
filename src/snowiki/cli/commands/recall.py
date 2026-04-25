from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import emit_error, emit_result, normalize_output_mode
from snowiki.config import get_snowiki_root
from snowiki.search.queries import run_recall


def _render_recall_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [f"Recall strategy: {result['strategy']}", f"hits: {len(result['hits'])}"]
    for index, hit in enumerate(result["hits"], start=1):
        lines.append(f"{index}. [{hit['kind']}] {hit['title']} ({hit['path']})")
    return "\n".join(lines)


@click.command("recall")
@click.argument("target")
@output_option
@root_option
def command(target: str, output: str, root: Path | None) -> None:
    output_mode = normalize_output_mode(output)
    try:
        result = run_recall(root if root else get_snowiki_root(), target)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="recall_failed")
    emit_result(
        {"ok": True, "command": "recall", "result": result},
        output=output_mode,
        human_renderer=_render_recall_human,
    )
