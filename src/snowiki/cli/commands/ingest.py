from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from snowiki.adapters import normalize_claude_session_file
from snowiki.adapters.opencode import load_opencode_session
from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.config import get_snowiki_root
from snowiki.privacy import PrivacyGate
from snowiki.search.workspace import clear_query_search_index_cache
from snowiki.storage.normalized import NormalizedStorage
from snowiki.storage.raw import RawStorage

_PRIVACY_GATE = PrivacyGate()


def _render_ingest_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"Ingested {result['source']} source into {result['root']}",
        f"session_id: {result.get('session_id', 'n/a')}",
        f"raw_ref: {result['raw_ref']['path']}",
        f"records_written: {result['records_written']}",
    ]
    if result["written_paths"]:
        lines.append("written_paths:")
        lines.extend(f"- {path}" for path in result["written_paths"])
    return "\n".join(lines)


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def _stabilize_provenance(node: Any, *, captured_at: str) -> Any:
    if isinstance(node, dict):
        provenance = node.get("provenance")
        if isinstance(provenance, dict) and captured_at:
            provenance["captured_at"] = captured_at
        for value in node.values():
            _stabilize_provenance(value, captured_at=captured_at)
    elif isinstance(node, list):
        for item in node:
            _stabilize_provenance(item, captured_at=captured_at)
    return node


def _model_payload(model: Any, *, captured_at: str) -> dict[str, Any]:
    payload = model.model_dump(mode="json")
    return _stabilize_provenance(payload, captured_at=captured_at)


def _iso_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _store_record(
    storage: NormalizedStorage,
    *,
    source_type: str,
    record_type: str,
    record_id: str,
    payload: dict[str, Any],
    raw_ref: dict[str, Any],
    recorded_at: str,
) -> str:
    return storage.store_record(
        source_type=source_type,
        record_type=record_type,
        record_id=record_id,
        payload=payload,
        raw_ref=raw_ref,
        recorded_at=recorded_at,
    )["path"]


def _store_claude_session(
    source_path: Path,
    *,
    root: Path,
) -> dict[str, Any]:
    _PRIVACY_GATE.ensure_allowed_source(source_path)
    raw_storage = RawStorage(root)
    normalized_storage = NormalizedStorage(root)
    raw_ref = raw_storage.store_file("claude", source_path)
    captured_at = str(raw_ref["mtime"])
    try:
        normalized = normalize_claude_session_file(source_path)
    except Exception:
        return _store_claude_fallback_session(
            source_path,
            root=root,
            raw_ref=raw_ref,
            normalized_storage=normalized_storage,
            captured_at=captured_at,
        )

    written_paths: list[str] = []
    written_paths.append(
        _store_record(
            normalized_storage,
            source_type="claude",
            record_type="session",
            record_id=normalized.session.id,
            payload=_model_payload(normalized.session, captured_at=captured_at),
            raw_ref=raw_ref,
            recorded_at=normalized.session.updated_at.isoformat(),
        )
    )

    for event in normalized.events:
        written_paths.append(
            _store_record(
                normalized_storage,
                source_type="claude",
                record_type="event",
                record_id=event.id,
                payload=_model_payload(event, captured_at=captured_at),
                raw_ref=raw_ref,
                recorded_at=event.timestamp.isoformat(),
            )
        )
        if event.content is None:
            continue
        message = event.content
        written_paths.append(
            _store_record(
                normalized_storage,
                source_type="claude",
                record_type="message",
                record_id=message.id,
                payload=_model_payload(message, captured_at=captured_at),
                raw_ref=raw_ref,
                recorded_at=message.created_at.isoformat(),
            )
        )
        for part in message.parts:
            written_paths.append(
                _store_record(
                    normalized_storage,
                    source_type="claude",
                    record_type="part",
                    record_id=part.id,
                    payload=_model_payload(part, captured_at=captured_at),
                    raw_ref=raw_ref,
                    recorded_at=message.created_at.isoformat(),
                )
            )

    return {
        "source": "claude",
        "root": root.as_posix(),
        "session_id": normalized.session.id,
        "raw_ref": raw_ref,
        "records_written": len(written_paths),
        "written_paths": sorted(set(written_paths)),
    }


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    if not rows:
        raise ValueError("Claude JSONL stream is empty")
    return rows


def _fallback_message_text(row: dict[str, Any]) -> str:
    message = row.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts)
    return ""


def _store_claude_fallback_session(
    source_path: Path,
    *,
    root: Path,
    raw_ref: dict[str, Any],
    normalized_storage: NormalizedStorage,
    captured_at: str,
) -> dict[str, Any]:
    rows = _read_jsonl_rows(source_path)
    session_id = next(
        (
            str(row.get("sessionId"))
            for row in rows
            if isinstance(row.get("sessionId"), str)
            and str(row.get("sessionId")).strip()
        ),
        source_path.stem,
    )
    message_rows = [row for row in rows if row.get("type") in {"user", "assistant"}]
    timestamps = [
        str(row.get("timestamp"))
        for row in rows
        if isinstance(row.get("timestamp"), str) and str(row.get("timestamp")).strip()
    ]
    updated_at = timestamps[-1] if timestamps else captured_at
    title = (
        _fallback_message_text(message_rows[0]) if message_rows else source_path.stem
    )
    summary = (
        _fallback_message_text(message_rows[-1])
        if message_rows
        else f"Imported from {source_path.name}."
    )

    written_paths = [
        _store_record(
            normalized_storage,
            source_type="claude",
            record_type="session",
            record_id=session_id,
            payload={
                "title": title,
                "summary": summary,
                "metadata": {"title": title, "source_path": source_path.as_posix()},
                "source": "claude",
                "status": "closed",
                "source_metadata": {
                    "format": "fallback_jsonl",
                    "record_count": len(rows),
                },
                "provenance": {
                    "id": f"prov:session:{session_id}",
                    "source": "claude",
                    "identity_keys": [f"raw:claude:jsonl:{session_id}"],
                    "raw_uri": source_path.resolve().as_uri(),
                    "raw_id": session_id,
                    "raw_kind": "jsonl_session",
                    "captured_at": captured_at,
                    "locator": {"path": source_path.as_posix()},
                    "source_metadata": {"adapter": "claude-fallback"},
                },
            },
            raw_ref=raw_ref,
            recorded_at=updated_at,
        )
    ]

    for index, row in enumerate(message_rows):
        role = str(row.get("type", "unknown"))
        text = _fallback_message_text(row)
        record_id = str(row.get("uuid") or f"{session_id}:message:{index}")
        timestamp = str(row.get("timestamp") or updated_at)
        payload = {
            "session_id": session_id,
            "title": text or record_id,
            "summary": text or f"{role} message from Claude JSONL fallback import.",
            "text": text,
            "role": role,
            "metadata": {"role": role, "source_path": source_path.as_posix()},
            "source_metadata": {
                "format": "fallback_jsonl",
                "raw_type": row.get("type"),
            },
            "provenance": {
                "id": f"prov:message:{record_id}",
                "source": "claude",
                "identity_keys": [f"raw:claude:jsonl_message:{record_id}"],
                "raw_uri": source_path.resolve().as_uri(),
                "raw_id": record_id,
                "raw_kind": "jsonl_message",
                "captured_at": captured_at,
                "locator": {"uuid": row.get("uuid")},
                "source_metadata": {"adapter": "claude-fallback"},
            },
        }
        written_paths.append(
            _store_record(
                normalized_storage,
                source_type="claude",
                record_type="message",
                record_id=record_id,
                payload=payload,
                raw_ref=raw_ref,
                recorded_at=timestamp,
            )
        )
        written_paths.append(
            _store_record(
                normalized_storage,
                source_type="claude",
                record_type="event",
                record_id=f"event:{record_id}",
                payload={
                    "session_id": session_id,
                    "title": payload["title"],
                    "summary": payload["summary"],
                    "text": text,
                    "type": role,
                    "source_metadata": {
                        "format": "fallback_jsonl",
                        "raw_type": row.get("type"),
                    },
                    "provenance": payload["provenance"],
                },
                raw_ref=raw_ref,
                recorded_at=timestamp,
            )
        )

    return {
        "source": "claude",
        "root": root.as_posix(),
        "session_id": session_id,
        "raw_ref": raw_ref,
        "records_written": len(written_paths),
        "written_paths": sorted(set(written_paths)),
    }


def _store_opencode_session(
    source_path: Path,
    *,
    root: Path,
) -> dict[str, Any]:
    _PRIVACY_GATE.ensure_allowed_source(source_path)
    raw_storage = RawStorage(root)
    normalized_storage = NormalizedStorage(root)
    raw_ref = raw_storage.store_file("opencode", source_path)
    captured_at = str(raw_ref["mtime"])
    normalized = load_opencode_session(db_path=source_path)

    if normalized.error or normalized.session is None:
        error_message = normalized.error or "failed to normalize OpenCode source"
        _store_record(
            normalized_storage,
            source_type="opencode",
            record_type="ingest_status",
            record_id=normalized.ingest_status.id,
            payload=_model_payload(normalized.ingest_status, captured_at=captured_at),
            raw_ref=raw_ref,
            recorded_at=_iso_now(),
        )
        raise click.ClickException(error_message)

    written_paths: list[str] = []
    written_paths.append(
        _store_record(
            normalized_storage,
            source_type="opencode",
            record_type="session",
            record_id=normalized.session.id,
            payload=_model_payload(normalized.session, captured_at=captured_at),
            raw_ref=raw_ref,
            recorded_at=normalized.session.updated_at.isoformat(),
        )
    )
    for message in normalized.messages:
        written_paths.append(
            _store_record(
                normalized_storage,
                source_type="opencode",
                record_type="message",
                record_id=message.id,
                payload=_model_payload(message, captured_at=captured_at),
                raw_ref=raw_ref,
                recorded_at=message.created_at.isoformat(),
            )
        )
        for part in message.parts:
            written_paths.append(
                _store_record(
                    normalized_storage,
                    source_type="opencode",
                    record_type="part",
                    record_id=part.id,
                    payload=_model_payload(part, captured_at=captured_at),
                    raw_ref=raw_ref,
                    recorded_at=message.created_at.isoformat(),
                )
            )
    for event in normalized.events:
        written_paths.append(
            _store_record(
                normalized_storage,
                source_type="opencode",
                record_type="event",
                record_id=event.id,
                payload=_model_payload(event, captured_at=captured_at),
                raw_ref=raw_ref,
                recorded_at=event.timestamp.isoformat(),
            )
        )
    written_paths.append(
        _store_record(
            normalized_storage,
            source_type="opencode",
            record_type="ingest_status",
            record_id=normalized.ingest_status.id,
            payload=_model_payload(normalized.ingest_status, captured_at=captured_at),
            raw_ref=raw_ref,
            recorded_at=normalized.ingest_status.last_seen_at.isoformat(),
        )
    )

    return {
        "source": "opencode",
        "root": root.as_posix(),
        "session_id": normalized.session.id,
        "raw_ref": raw_ref,
        "records_written": len(written_paths),
        "written_paths": sorted(set(written_paths)),
    }


def run_ingest(path: Path, *, source: str, root: Path) -> dict[str, Any]:
    result = (
        _store_claude_session(path, root=root)
        if source == "claude"
        else _store_opencode_session(path, root=root)
    )
    clear_query_search_index_cache()
    return result


@click.command("ingest")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--source",
    type=click.Choice(["claude", "opencode"], case_sensitive=False),
    required=True,
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
def command(path: Path, source: str, root: Path | None, output: str) -> None:
    output_mode = _normalize_output_mode(output)
    root = root if root else get_snowiki_root()
    result: dict[str, Any] | None = None
    try:
        result = run_ingest(path, source=source, root=root)
    except click.ClickException as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="ingest_failed",
            details={"path": path.as_posix(), "source": source},
        )
    except ValueError as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="privacy_blocked",
            details={"path": path.as_posix(), "source": source},
        )
    except Exception as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="unexpected_error",
            details={"path": path.as_posix(), "source": source},
        )
    if result is None:
        raise RuntimeError("ingest did not produce a result")

    emit_result(
        {"ok": True, "command": "ingest", "result": result},
        output=output_mode,
        human_renderer=_render_ingest_human,
    )
