from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, cast

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.config import resolve_snowiki_root
from snowiki.fileback import (
    apply_fileback_proposal,
    apply_queued_fileback_proposal,
    list_queued_fileback_proposals,
    prune_queued_fileback_proposals,
    reject_queued_fileback_proposal,
    resolve_preview_root,
    show_queued_fileback_proposal,
)
from snowiki.fileback.queue import build_queue_list_result, run_fileback_preview

QueueCliStatus = Literal["pending", "applied", "rejected", "failed", "all"]
TerminalQueueCliStatus = Literal["applied", "rejected", "failed", "all"]


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
    queue_result = result.get("queue")
    if isinstance(queue_result, dict):
        lines.extend(
            [
                f"queued: {queue_result['decision']}",
                f"queue path: {queue_result['proposal_path']}",
            ]
        )
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


def _render_queue_list_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    proposals = result["proposals"]
    lines = [
        f"Fileback proposals for {result['root']} [{result['status']}]: {len(proposals)}"
    ]
    for proposal in proposals:
        target = proposal["target"]
        lines.append(
            f"- {proposal['proposal_id']}: "
            f"{target['compiled_path']} ({proposal['proposal_path']})"
        )
    return "\n".join(lines)


def _render_queue_show_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"Fileback proposal {result['proposal_id']} [{result['status']}]",
        f"summary: {result['summary']}",
        f"target: {result['target']['compiled_path']}",
        f"queue path: {result['proposal_path']}",
        f"decision: {result['decision']}",
        f"requires human review: {result['requires_human_review']}",
    ]
    if "transitioned_at" in result:
        lines.append(f"transitioned: {result['transitioned_at']}")
        lines.append(f"transition reason: {result['transition_reason']}")
    return "\n".join(lines)


def _render_queue_prune_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    action = "Would delete" if result["dry_run"] else "Deleted"
    return (
        f"{action} {result['candidate_count']} fileback queue artifact(s) "
        f"for {', '.join(result['statuses'])}; retained {result['retained_count']}"
    )


def _parse_duration(value: str | None) -> timedelta | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        raise click.BadParameter("duration must not be empty")
    unit = normalized[-1]
    amount_text = normalized[:-1]
    if not amount_text.isdigit() or unit not in {"d", "h", "s"}:
        raise click.BadParameter("duration must use a positive integer plus d, h, or s")
    amount = int(amount_text)
    if amount <= 0:
        raise click.BadParameter("duration must be positive")
    if unit == "d":
        return timedelta(days=amount)
    if unit == "h":
        return timedelta(hours=amount)
    return timedelta(seconds=amount)


def _queue_cli_status(value: str) -> QueueCliStatus:
    return cast(QueueCliStatus, value.lower())


def _terminal_queue_cli_status(value: str) -> TerminalQueueCliStatus:
    return cast(TerminalQueueCliStatus, value.lower())


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
@click.option(
    "--queue",
    "queue_proposal",
    is_flag=True,
    help="Persist the preview as a pending proposal under the Snowiki root queue.",
)
@click.option(
    "--auto-apply-low-risk",
    is_flag=True,
    help="Queue and immediately apply only if runtime low-risk policy passes.",
)
def preview_command(
    question: str,
    answer_markdown: str,
    summary: str,
    evidence_paths: tuple[str, ...],
    output: str,
    root: Path | None,
    queue_proposal: bool,
    auto_apply_low_risk: bool,
) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        result = run_fileback_preview(
            root,
            question=question,
            answer_markdown=answer_markdown,
            summary=summary,
            evidence_paths=evidence_paths,
            queue_proposal=queue_proposal,
            auto_apply_low_risk=auto_apply_low_risk,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_preview_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback preview",
            "result": result,
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


@command.group("queue")
def queue_command() -> None:
    """Inspect pending fileback proposal queue entries."""


@queue_command.command("list")
@click.option(
    "--status",
    type=click.Choice(["pending", "applied", "rejected", "failed", "all"], case_sensitive=False),
    default="pending",
    show_default=True,
    help="Queue state to list.",
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
def queue_list_command(status: str, output: str, root: Path | None) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        queue_root = resolve_snowiki_root(root)
        normalized_status = _queue_cli_status(status)
        proposals = list_queued_fileback_proposals(queue_root, status=normalized_status)
        result = build_queue_list_result(
            root=queue_root,
            status=normalized_status,
            proposals=proposals,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_list_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback queue list",
            "result": result,
        },
        output=output_mode,
        human_renderer=_render_queue_list_human,
    )


@queue_command.command("show")
@click.argument("proposal_id")
@click.option("--verbose", is_flag=True, help="Include full proposal and apply payloads.")
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
def queue_show_command(
    proposal_id: str, verbose: bool, output: str, root: Path | None
) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        queue_root = resolve_snowiki_root(root)
        result = show_queued_fileback_proposal(queue_root, proposal_id, verbose=verbose)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_show_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback queue show",
            "result": result,
        },
        output=output_mode,
        human_renderer=_render_queue_show_human,
    )


@queue_command.command("apply")
@click.argument("proposal_id")
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
def queue_apply_command(proposal_id: str, output: str, root: Path | None) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        queue_root = resolve_snowiki_root(root)
        result = apply_queued_fileback_proposal(queue_root, proposal_id)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_apply_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback queue apply",
            "result": result,
        },
        output=output_mode,
        human_renderer=_render_queue_show_human,
    )


@queue_command.command("reject")
@click.argument("proposal_id")
@click.option("--reason", required=True, help="Human-readable rejection reason.")
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
def queue_reject_command(
    proposal_id: str, reason: str, output: str, root: Path | None
) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        queue_root = resolve_snowiki_root(root)
        result = reject_queued_fileback_proposal(queue_root, proposal_id, reason=reason)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_reject_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback queue reject",
            "result": result,
        },
        output=output_mode,
        human_renderer=_render_queue_show_human,
    )


@queue_command.command("prune")
@click.option(
    "--status",
    type=click.Choice(["applied", "rejected", "failed", "all"], case_sensitive=False),
    required=True,
    help="Terminal queue state to prune.",
)
@click.option("--keep", type=int, default=None, help="Number of newest terminal artifacts to retain.")
@click.option("--older-than", default=None, help="Optional age filter such as 30d, 12h, or 60s.")
@click.option("--dry-run", is_flag=True, help="Preview prune candidates without deleting them.")
@click.option("--delete", "delete_artifacts", is_flag=True, help="Delete prune candidates.")
@click.option("--yes", is_flag=True, help="Confirm deletion when --delete is used.")
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
def queue_prune_command(
    status: str,
    keep: int | None,
    older_than: str | None,
    dry_run: bool,
    delete_artifacts: bool,
    yes: bool,
    output: str,
    root: Path | None,
) -> None:
    output_mode = _normalize_output_mode(output)
    try:
        if dry_run and delete_artifacts:
            raise ValueError("--dry-run cannot be combined with --delete")
        if delete_artifacts and not yes:
            raise ValueError("--delete requires --yes")
        queue_root = resolve_snowiki_root(root)
        result = prune_queued_fileback_proposals(
            queue_root,
            status=_terminal_queue_cli_status(status),
            keep=keep,
            older_than=_parse_duration(older_than),
            dry_run=not delete_artifacts,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_prune_failed")
    emit_result(
        {
            "ok": True,
            "command": "fileback queue prune",
            "result": result,
        },
        output=output_mode,
        human_renderer=_render_queue_prune_human,
    )
