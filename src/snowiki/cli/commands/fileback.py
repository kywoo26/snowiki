from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.fileback import (
    apply_fileback_proposal,
    build_fileback_proposal,
    resolve_preview_root,
)


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def _render_preview_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    proposal = result["proposal"]
    draft = proposal["draft"]
    lines = [
        f"Fileback preview for {proposal['target']['compiled_path']}",
        f"proposal_id: {proposal['proposal_id']}",
        f"summary: {draft['summary']}",
        f"supporting paths: {len(proposal['evidence']['requested_paths'])}",
        f"raw note write: {proposal['apply_plan']['raw_note_path']}",
        f"normalized write: {proposal['apply_plan']['normalized_path']}",
        "rebuild required: yes",
    ]
    return "\n".join(lines)


def _render_apply_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"Applied fileback proposal {result['proposal_id']}",
        f"normalized record: {result['normalized_path']}",
        f"compiled question: {result['compiled_path']}",
        f"proposal raw artifact: {result['raw_ref']['path']}",
        f"rebuild wrote {result['rebuild']['compiled_count']} compiled paths",
    ]
    return "\n".join(lines)


@click.group("fileback")
def command() -> None:
    """Preview and apply reviewable question filebacks."""


@command.command("preview")
@click.argument("question")
@click.option("--answer-markdown", required=True, help="Reviewed answer content.")
@click.option("--summary", required=True, help="Short summary for the question page.")
@click.option(
    "--evidence-path",
    "evidence_paths",
    multiple=True,
    required=True,
    help="Supporting compiled/, normalized/, or raw/ workspace file path. Repeat as needed.",
)
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
def preview_command(
    question: str,
    answer_markdown: str,
    summary: str,
    evidence_paths: tuple[str, ...],
    output: str,
    root: Path | None,
) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        preview_root = resolve_preview_root(root)
        proposal = build_fileback_proposal(
            preview_root,
            question=question,
            answer_markdown=answer_markdown,
            summary=summary,
            evidence_paths=evidence_paths,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_preview_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback preview",
            "result": {
                "root": preview_root.as_posix(),
                "proposal": proposal,
                "proposed_write": {
                    "raw_note_body": proposal["apply_plan"]["proposed_raw_note_body"],
                    "normalized_record_payload": proposal["apply_plan"][
                        "proposed_normalized_record_payload"
                    ],
                },
            },
        },
        output=output_mode,
        human_renderer=_render_preview_human,
    )


@command.command("apply")
@click.option(
    "--proposal-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Path to a reviewed preview payload or proposal JSON file.",
)
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
def apply_command(proposal_file: Path, output: str, root: Path | None) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        reviewed_payload = json.loads(proposal_file.read_text(encoding="utf-8"))
        apply_root = root if root is not None else resolve_preview_root(None)
        result = apply_fileback_proposal(apply_root, reviewed_payload)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_apply_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback apply",
            "result": result,
        },
        output=output_mode,
        human_renderer=_render_apply_human,
    )
