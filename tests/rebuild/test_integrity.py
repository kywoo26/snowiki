from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
from snowiki.cli.main import app
from snowiki.rebuild.integrity import verify_rebuild_integrity


def test_verify_rebuild_integrity_restores_compiled_and_index_layers(
    tmp_path: Path,
    claude_basic_fixture: Path,
) -> None:
    runner = CliRunner()

    ingest = runner.invoke(
        app,
        [
            "ingest",
            str(claude_basic_fixture),
            "--source",
            "claude",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    initial_rebuild = runner.invoke(
        app, ["rebuild", "--output", "json"], env={"SNOWIKI_ROOT": str(tmp_path)}
    )
    assert initial_rebuild.exit_code == 0, initial_rebuild.output
    before_paths = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / "compiled").rglob("*.md")
    )
    assert before_paths

    result = verify_rebuild_integrity(tmp_path)

    assert result["compiled_before"] == before_paths
    assert result["compiled_after"] == before_paths
    assert result["compiled_restored"] is True
    assert result["index_restored"] is True
