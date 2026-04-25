from __future__ import annotations

import json

import click
import pytest

from snowiki.cli.output import emit_error, emit_result, normalize_output_mode


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
