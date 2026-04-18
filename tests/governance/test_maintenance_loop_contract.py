from __future__ import annotations

from snowiki.cli.main import app


def test_maintenance_loop_boundaries_stay_tied_to_shipped_runtime_truth(
    repo_root,
) -> None:
    maintenance_doc = (
        repo_root
        / "docs"
        / "roadmap"
        / "step3_wiki-skill-design"
        / "04-maintenance-loop-and-deferred-workflows.md"
    ).read_text(encoding="utf-8").casefold()

    cli_commands = {command.name for command in app.commands.values() if command.name is not None}

    # Shipped anchors that 04 is allowed to depend on.
    assert {"ingest", "query", "recall", "status", "lint", "fileback", "daemon", "rebuild"}.issubset(
        cli_commands
    )

    # Maintenance concepts that must remain workflow ideas rather than commands.
    for deferred_command in ("absorb", "cleanup", "sync", "edit", "merge"):
        assert deferred_command not in cli_commands

    # Canonical 04 document must keep them explicit and fail-closed.
    assert "absorb" in maintenance_doc
    assert "cleanup" in maintenance_doc
    assert "deferred or unsupported today" in maintenance_doc
    for route in ("`sync`", "`edit`", "`merge`", "graph-oriented workflows"):
        assert route in maintenance_doc

    # Current reviewable-write posture must remain explicit.
    assert "fileback preview" in maintenance_doc
    assert "fileback apply" in maintenance_doc
    assert "reviewable" in maintenance_doc
    assert "mcp is not a mutation path" in maintenance_doc

    # Daemon remains optimization-only, not separate runtime truth.
    assert "daemon-backed reads are optimization only" in maintenance_doc
