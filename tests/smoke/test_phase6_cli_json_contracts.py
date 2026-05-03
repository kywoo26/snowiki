from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from click.testing import CliRunner, Result

from snowiki.cli.main import app

pytestmark = pytest.mark.smoke


def _invoke(args: list[str], *, root: Path | None = None) -> Result:
    env = {"SNOWIKI_ROOT": root.as_posix(), "SNOWIKI_OUTPUT": "json"} if root else None
    runner = CliRunner()
    return runner.invoke(app, args, env=env)


def _payload(result: Result) -> dict[str, Any]:
    data = json.loads(result.output)
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def _write_markdown(path: Path, *, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        f"---\ntitle: {title}\nsummary: {title} summary.\n---\n# {title}\n\n{title} body.\n",
        encoding="utf-8",
    )


def _assert_success_envelope(payload: dict[str, Any], *, command: str) -> None:
    assert set(payload) == {"command", "ok", "result"}
    assert payload["ok"] is True
    assert payload["command"] == command
    assert isinstance(payload["result"], dict)


def _assert_error_envelope(payload: dict[str, Any], *, code: str) -> None:
    assert set(payload) == {"error", "ok"}
    assert payload["ok"] is False
    error = payload["error"]
    assert isinstance(error, dict)
    assert set(error) >= {"code", "message"}
    assert error["code"] == code
    assert isinstance(error["message"], str)
    if "details" in error:
        assert isinstance(error["details"], dict)


@pytest.mark.parametrize(
    ("args", "expected_options"),
    [
        (["ingest", "--help"], ("PATH", "--source-root", "--rebuild", "--root", "--output")),
        (["rebuild", "--help"], ("--root", "--output")),
        (
            ["fileback", "preview", "--help"],
            ("QUESTION", "--answer-markdown", "--summary", "--evidence-path", "--queue"),
        ),
        (["fileback", "apply", "--help"], ("--proposal-file", "--root", "--output")),
        (["fileback", "queue", "list", "--help"], ("--root", "--output")),
        (["fileback", "queue", "show", "--help"], ("PROPOSAL_ID", "--verbose", "--root", "--output")),
        (["fileback", "queue", "apply", "--help"], ("PROPOSAL_ID", "--root", "--output")),
        (["fileback", "queue", "reject", "--help"], ("PROPOSAL_ID", "--reason", "--root", "--output")),
        (
            ["prune", "sources", "--help"],
            ("--dry-run", "--delete", "--yes", "--all-candidates", "--root", "--output"),
        ),
    ],
)
def test_phase6_mutation_command_help_contract(
    args: list[str], expected_options: tuple[str, ...]
) -> None:
    result = _invoke(args)

    assert result.exit_code == 0, result.output
    for expected in expected_options:
        assert expected in result.output


def test_phase6_json_success_envelopes_are_stable_across_mutation_commands(
    tmp_path: Path,
) -> None:
    snowiki_root = tmp_path / "snowiki"
    source = tmp_path / "vault" / "json-contract.md"
    _write_markdown(source, title="Phase 6 JSON Contract")

    ingest = _invoke(["ingest", source.as_posix()], root=snowiki_root)
    assert ingest.exit_code == 0, ingest.output
    _assert_success_envelope(_payload(ingest), command="ingest")

    rebuild = _invoke(["rebuild"], root=snowiki_root)
    assert rebuild.exit_code == 0, rebuild.output
    _assert_success_envelope(_payload(rebuild), command="rebuild")

    evidence_path = sorted((snowiki_root / "compiled" / "summaries").glob("*.md"))[0]
    preview = _invoke(
        [
            "fileback",
            "preview",
            "What JSON envelope remains stable?",
            "--answer-markdown",
            "Mutation commands keep the same JSON success envelope.",
            "--summary",
            "Stable JSON envelope.",
            "--evidence-path",
            evidence_path.relative_to(snowiki_root).as_posix(),
        ],
        root=snowiki_root,
    )
    assert preview.exit_code == 0, preview.output
    _assert_success_envelope(_payload(preview), command="fileback preview")

    queue_list = _invoke(["fileback", "queue", "list"], root=snowiki_root)
    assert queue_list.exit_code == 0, queue_list.output
    _assert_success_envelope(_payload(queue_list), command="fileback queue list")

    prune = _invoke(["prune", "sources", "--dry-run"], root=snowiki_root)
    assert prune.exit_code == 0, prune.output
    _assert_success_envelope(_payload(prune), command="prune sources")


def test_phase6_json_error_envelopes_are_stable_for_mutation_safety_gates(
    tmp_path: Path,
) -> None:
    snowiki_root = tmp_path / "snowiki"
    malformed_file = tmp_path / "malformed-fileback.json"
    malformed_file.write_text(json.dumps({"ok": True}), encoding="utf-8")

    fileback = _invoke(
        ["fileback", "apply", "--proposal-file", malformed_file.as_posix()],
        root=snowiki_root,
    )
    assert fileback.exit_code != 0
    _assert_error_envelope(_payload(fileback), code="fileback_apply_failed")

    prune = _invoke(
        ["prune", "sources", "--delete", "--all-candidates"],
        root=snowiki_root,
    )
    assert prune.exit_code != 0
    _assert_error_envelope(_payload(prune), code="prune_confirmation_required")
