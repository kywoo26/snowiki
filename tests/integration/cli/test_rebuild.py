from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner
from tests.helpers.markdown_ingest import write_markdown_source

from snowiki.cli.main import app
from snowiki.search.workspace import current_runtime_tokenizer_name


def test_rebuild_generates_compiled_outputs_and_index_manifest(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    fixture = write_markdown_source(tmp_path)
    ingest = runner.invoke(
        app,
        ["ingest", str(fixture), "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    rebuild = runner.invoke(
        app,
        ["rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert rebuild.exit_code == 0, rebuild.output
    payload = json.loads(rebuild.output)
    assert payload["ok"] is True
    assert (tmp_path / "compiled/overview.md").exists()
    assert (tmp_path / "index/manifest.json").exists()
    manifest = json.loads(
        (tmp_path / "index/manifest.json").read_text(encoding="utf-8")
    )
    assert payload["result"]["compiled_count"] >= 1
    assert (
        payload["result"]["content_identity"]
        == payload["result"]["current_content_identity"]
    )
    assert payload["result"]["tokenizer_name"] == current_runtime_tokenizer_name()
    assert manifest["tokenizer_name"] == current_runtime_tokenizer_name()


def test_rebuild_fails_closed_when_integrity_freshness_changes(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.cli.commands import rebuild as rebuild_command
    from snowiki.rebuild.integrity import RebuildFreshnessError

    runner = CliRunner()
    mismatch_result = {
        "root": tmp_path.as_posix(),
        "compiled_count": 1,
        "compiled_paths": ["compiled/overview.md"],
        "index_manifest": "index/manifest.json",
        "records_indexed": 1,
        "pages_indexed": 1,
        "content_identity": {
            "normalized": {"latest_mtime_ns": 100, "file_count": 1},
            "compiled": {"latest_mtime_ns": 200, "file_count": 1},
        },
        "current_content_identity": {
            "normalized": {"latest_mtime_ns": 101, "file_count": 2},
            "compiled": {"latest_mtime_ns": 201, "file_count": 2},
        },
    }

    def fail_run_rebuild(_root: Path) -> dict[str, Any]:
        raise RebuildFreshnessError(mismatch_result)

    monkeypatch.setattr(rebuild_command, "run_rebuild", fail_run_rebuild)

    rebuild = runner.invoke(
        app,
        ["rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert rebuild.exit_code == 1
    payload = json.loads(rebuild.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "rebuild_failed"
    assert payload["error"]["details"] == mismatch_result
