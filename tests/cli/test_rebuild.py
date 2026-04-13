from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app


def test_rebuild_generates_compiled_outputs_and_index_manifest(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    runner = CliRunner()
    fixture = claude_basic_fixture
    ingest = runner.invoke(
        app,
        ["ingest", str(fixture), "--source", "claude", "--output", "json"],
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
    assert payload["result"]["compiled_count"] >= 1


def test_rebuild_repairs_policy_mismatched_manifest(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    runner = CliRunner()
    ingest = runner.invoke(
        app,
        ["ingest", str(claude_basic_fixture), "--source", "claude", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "lexical_policy": "korean-mixed-lexical",
                "lexical_policy_version": 1,
                "search_documents": 0,
            }
        ),
        encoding="utf-8",
    )

    rebuild = runner.invoke(
        app,
        ["rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert rebuild.exit_code == 0, rebuild.output
    payload = json.loads(rebuild.output)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert manifest["lexical_policy"] == "legacy-lexical"
    assert manifest["lexical_policy_version"] == 1


def test_rebuild_repairs_manifest_missing_policy_metadata(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    runner = CliRunner()
    ingest = runner.invoke(
        app,
        ["ingest", str(claude_basic_fixture), "--source", "claude", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"search_documents": 0}), encoding="utf-8")

    rebuild = runner.invoke(
        app,
        ["rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert rebuild.exit_code == 0, rebuild.output
    payload = json.loads(rebuild.output)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert manifest["lexical_policy"] == "legacy-lexical"
    assert manifest["lexical_policy_version"] == 1
