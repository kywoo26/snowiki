from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from snowiki.cli.context import (
    SnowikiCliContext,
    bind_cli_context,
    initialize_cli_root,
    pass_snowiki_context,
)
from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import (
    emit_command_result,
    emit_error,
)
from snowiki.cli.types import PROPOSAL_ID
from snowiki.fileback import (
    apply_fileback_proposal,
    apply_queued_fileback_proposal,
    list_queued_fileback_proposals,
    reject_queued_fileback_proposal,
    resolve_preview_root,
    show_queued_fileback_proposal,
)
from snowiki.fileback.queue import build_queue_list_result, run_fileback_preview


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
                f"queued: {queue_result['status']}",
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


def _render_queue_item_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"Fileback proposal {result['proposal_id']} [{result['status']}]",
        f"summary: {result['summary']}",
        f"target: {result['target']['compiled_path']}",
        f"queue path: {result['proposal_path']}",
    ]
    if "deleted_proposal_path" in result:
        lines.append(f"deleted queue path: {result['deleted_proposal_path']}")
    if "transition_reason" in result:
        lines.append(f"transition reason: {result['transition_reason']}")
    return "\n".join(lines)


@click.group(
    "fileback",
    no_args_is_help=True,
    short_help="Preview and apply reviewable filebacks.",
)
def command() -> None:
    """Preview and apply reviewable question filebacks."""


@command.command("preview", short_help="Build a non-mutating fileback preview.")
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
    "--queue",
    "queue_proposal",
    is_flag=True,
    help="Persist the preview as a pending proposal under the Snowiki root queue.",
)
@root_option
@output_option
@pass_snowiki_context
def preview_command(
    cli_context: SnowikiCliContext,
    question: str,
    answer_markdown: str,
    summary: str,
    evidence_paths: tuple[str, ...],
    queue_proposal: bool,
    root: Path | None,
    output: str,
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        result = run_fileback_preview(
            cli_context.root,
            question=question,
            answer_markdown=answer_markdown,
            summary=summary,
            evidence_paths=evidence_paths,
            queue_proposal=queue_proposal,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_preview_failed")
    emit_command_result(
        result,
        command="fileback preview",
        output=output_mode,
        human_renderer=_render_preview_human,
    )


@command.command("apply", short_help="Apply a reviewed fileback proposal file.")
@click.option(
    "--proposal-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Path to a reviewed preview payload or proposal JSON file.",
)
@root_option
@output_option
@pass_snowiki_context
def apply_command(
    cli_context: SnowikiCliContext, proposal_file: Path, root: Path | None, output: str
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        reviewed_payload = json.loads(proposal_file.read_text(encoding="utf-8"))
        apply_root = (
            cli_context.root if cli_context.root is not None else resolve_preview_root(None)
        )
        result = apply_fileback_proposal(apply_root, reviewed_payload)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_apply_failed")
    emit_command_result(
        result,
        command="fileback apply",
        output=output_mode,
        human_renderer=_render_apply_human,
    )


@command.group(
    "queue",
    no_args_is_help=True,
    short_help="Inspect queued fileback proposals.",
)
def queue_command() -> None:
    """Inspect pending fileback proposal queue entries."""


@queue_command.command("list", short_help="List queued fileback proposals.")
@root_option
@output_option
@pass_snowiki_context
def queue_list_command(
    cli_context: SnowikiCliContext, root: Path | None, output: str
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        queue_root = initialize_cli_root(cli_context)
        proposals = list_queued_fileback_proposals(queue_root)
        result = build_queue_list_result(
            root=queue_root,
            proposals=proposals,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_list_failed")
    emit_command_result(
        result,
        command="fileback queue list",
        output=output_mode,
        human_renderer=_render_queue_list_human,
    )


@queue_command.command("show", short_help="Show one queued fileback proposal.")
@click.argument("proposal_id", type=PROPOSAL_ID)
@click.option("--verbose", is_flag=True, help="Include full proposal and apply payloads.")
@root_option
@output_option
@pass_snowiki_context
def queue_show_command(
    cli_context: SnowikiCliContext,
    proposal_id: str,
    verbose: bool,
    root: Path | None,
    output: str,
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        queue_root = initialize_cli_root(cli_context)
        result = show_queued_fileback_proposal(queue_root, proposal_id, verbose=verbose)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_show_failed")
    emit_command_result(
        result,
        command="fileback queue show",
        output=output_mode,
        human_renderer=_render_queue_item_human,
    )


@queue_command.command("apply", short_help="Apply one queued fileback proposal.")
@click.argument("proposal_id", type=PROPOSAL_ID)
@root_option
@output_option
@pass_snowiki_context
def queue_apply_command(
    cli_context: SnowikiCliContext, proposal_id: str, root: Path | None, output: str
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        queue_root = initialize_cli_root(cli_context)
        result = apply_queued_fileback_proposal(queue_root, proposal_id)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_apply_failed")
    emit_command_result(
        result,
        command="fileback queue apply",
        output=output_mode,
        human_renderer=_render_queue_item_human,
    )


@queue_command.command("reject", short_help="Reject one queued fileback proposal.")
@click.argument("proposal_id", type=PROPOSAL_ID)
@click.option("--reason", required=True, help="Human-readable rejection reason.")
@root_option
@output_option
@pass_snowiki_context
def queue_reject_command(
    cli_context: SnowikiCliContext,
    proposal_id: str,
    reason: str,
    root: Path | None,
    output: str,
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        queue_root = initialize_cli_root(cli_context)
        result = reject_queued_fileback_proposal(queue_root, proposal_id, reason=reason)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="fileback_queue_reject_failed")
    emit_command_result(
        result,
        command="fileback queue reject",
        output=output_mode,
        human_renderer=_render_queue_item_human,
    )
