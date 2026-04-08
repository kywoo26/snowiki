from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import click

from snowiki.cli.commands.query import build_search_index
from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.search import known_item_lookup, temporal_recall, topical_recall


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def _hit_to_payload(hit: Any) -> dict[str, Any]:
    return {
        "id": hit.document.id,
        "path": hit.document.path,
        "title": hit.document.title,
        "kind": hit.document.kind,
        "score": round(hit.score, 6),
        "summary": hit.document.summary,
    }


def _render_recall_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [f"Recall strategy: {result['strategy']}", f"hits: {len(result['hits'])}"]
    for index, hit in enumerate(result["hits"], start=1):
        lines.append(f"{index}. [{hit['kind']}] {hit['title']} ({hit['path']})")
    return "\n".join(lines)


def _iso_date_window(text: str) -> tuple[datetime, datetime] | None:
    try:
        start = datetime.fromisoformat(text).replace(tzinfo=UTC)
    except ValueError:
        return None
    end = start + timedelta(days=1)
    return start, end


def run_recall(root: Path, target: str) -> dict[str, Any]:
    index, _, _ = build_search_index(root)
    strategy = "topic"
    window = _iso_date_window(target)
    if window is not None:
        start, end = window
        hits = index.search(target, limit=10, recorded_after=start, recorded_before=end)
        strategy = "date"
    elif any(
        token in target.casefold()
        for token in (
            "yesterday",
            "today",
            "last week",
            "this week",
            "어제",
            "오늘",
            "지난주",
            "이번주",
        )
    ):
        hits = temporal_recall(index, target, limit=10)
        strategy = "temporal"
    else:
        hits = known_item_lookup(index, target, limit=10)
        strategy = "known_item"
        if not hits:
            hits = topical_recall(index, target, limit=10)
            strategy = "topic"
    return {
        "target": target,
        "strategy": strategy,
        "hits": [_hit_to_payload(hit) for hit in hits],
    }


@click.command("recall")
@click.argument("target")
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
def command(target: str, output: str) -> None:
    output_mode = _normalize_output_mode(output)
    result: dict[str, Any] | None = None
    try:
        result = run_recall(Path.cwd(), target)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="recall_failed")
    if result is None:
        raise RuntimeError("recall did not produce a result")
    emit_result(
        {"ok": True, "command": "recall", "result": result},
        output=output_mode,
        human_renderer=_render_recall_human,
    )
