from __future__ import annotations

import json

import click
import pytest

from snowiki.cli.output import (
    emit_command_result,
    emit_error,
    emit_result,
    normalize_output_mode,
    validate_destructive_flags,
)


def test_normalize_output_mode_maps_click_choice_values() -> None:
    assert normalize_output_mode("json") == "json"
    assert normalize_output_mode("human") == "human"


def test_emit_result_json_sorts_payload_keys(capsys: pytest.CaptureFixture[str]) -> None:
    emit_result({"z": 1, "a": "한글"}, output="json")

    captured = capsys.readouterr()
    assert captured.out == '{\n  "a": "한글",\n  "z": 1\n}\n'
    assert captured.err == ""


def test_emit_result_human_uses_renderer(capsys: pytest.CaptureFixture[str]) -> None:
    emit_result(
        {"result": {"count": 3}},
        output="human",
        human_renderer=lambda payload: f"count={payload['result']['count']}",
    )

    captured = capsys.readouterr()
    assert captured.out == "count=3\n"
    assert captured.err == ""


def test_emit_result_human_falls_back_to_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_result({"message": "done"}, output="human")

    captured = capsys.readouterr()
    assert captured.out == "done\n"
    assert captured.err == ""


def test_emit_command_result_wraps_standard_success_envelope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_command_result({"count": 1}, command="example", output="json")

    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "ok": True,
        "command": "example",
        "result": {"count": 1},
    }
    assert captured.err == ""


def test_emit_error_json_payload_and_exit_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(click.exceptions.Exit) as exc_info:
        emit_error(
            "broken",
            output="json",
            code="broken_code",
            details={"path": "source.md"},
            exit_code=7,
        )

    assert exc_info.value.exit_code == 7
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "ok": False,
        "error": {
            "code": "broken_code",
            "message": "broken",
            "details": {"path": "source.md"},
        },
    }
    assert captured.err == ""


def test_emit_error_human_writes_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(click.exceptions.Exit) as exc_info:
        emit_error("broken", output="human", exit_code=3)

    assert exc_info.value.exit_code == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Error: broken\n"


def test_validate_destructive_flags_rejects_conflicting_modes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(click.exceptions.Exit) as exc_info:
        validate_destructive_flags(
            dry_run=True,
            delete_artifacts=True,
            yes=True,
            output="json",
            code="delete_failed",
        )

    assert exc_info.value.exit_code == 1
    assert json.loads(capsys.readouterr().out)["error"] == {
        "code": "delete_failed",
        "message": "--dry-run cannot be combined with --delete",
    }


def test_validate_destructive_flags_allows_distinct_conflict_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(click.exceptions.Exit):
        validate_destructive_flags(
            dry_run=True,
            delete_artifacts=True,
            yes=True,
            output="json",
            code="confirmation_required",
            conflict_code="invalid_delete_flags",
        )

    assert json.loads(capsys.readouterr().out)["error"] == {
        "code": "invalid_delete_flags",
        "message": "--dry-run cannot be combined with --delete",
    }


def test_validate_destructive_flags_requires_confirmation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(click.exceptions.Exit):
        validate_destructive_flags(
            dry_run=False,
            delete_artifacts=True,
            yes=False,
            output="json",
            code="delete_failed",
            confirmation_message="delete requires --yes",
        )

    assert json.loads(capsys.readouterr().out)["error"] == {
        "code": "delete_failed",
        "message": "delete requires --yes",
    }
