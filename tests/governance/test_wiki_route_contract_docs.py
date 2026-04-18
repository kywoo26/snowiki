from __future__ import annotations

import re
from pathlib import Path

from snowiki.cli.main import app
from snowiki.mcp.server import WRITE_OPERATION_NAMES

PRIMARY_CURRENT_ROUTES = {
    "ingest",
    "query",
    "recall",
    "status",
    "lint",
    "fileback preview",
    "fileback apply",
}
ADVANCED_CURRENT_PASSTHROUGHS = {"export", "benchmark", "daemon", "mcp"}
SHIPPED_SUPPORT_NOT_PRIMARY_ROUTE = "rebuild"
DEFERRED_ROUTES = {"sync", "edit", "merge"}
GRAPH_DEFERRED_MARKERS = (
    "graph-oriented workflows",
    "graph workflows",
    "graph-oriented recall workflows",
)
EXPECTED_CLI_COMMANDS = {
    "ingest",
    "rebuild",
    "query",
    "recall",
    "status",
    "lint",
    "export",
    "fileback",
    "benchmark",
    "daemon",
    "mcp",
}
ROUTE_CONTRACT_TARGET_PATH = Path(
    "docs/roadmap/step3_wiki-skill-design/01-wiki-route-contract.md"
)


def _extract_current_commands(content: str, heading: str) -> set[str]:
    section = content.split(heading, maxsplit=1)[1]
    commands: set[str] = set()
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") and stripped != heading:
            break
        match = re.search(r"`snowiki ([^`]+)`", stripped)
        if match:
            command = match.group(1)
            if " " not in command:
                commands.add(command)
    return commands


def _extract_readme_current_routes(content: str) -> set[str]:
    section = content.split("## Claude Code `/wiki` status", maxsplit=1)[1].split(
        "## Machine-usable surfaces today", maxsplit=1
    )[0]
    match = re.search(r"^- current: (?P<routes>.+)$", section, flags=re.MULTILINE)
    assert match is not None
    return set(re.findall(r"`([^`]+)`", match.group("routes")))


def _extract_workflow_routes_by_status(content: str, status: str) -> set[str]:
    section = content.split("## Step 1: Classify Command", maxsplit=1)[1].split(
        "\n---", maxsplit=1
    )[0]
    routes: set[str] = set()

    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| Input |"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 3 or set(cells[0]) == {"-"}:
            continue

        route_match = re.search(r"`([^`]+)`", cells[0])
        if route_match is None:
            continue

        normalized_status = cells[2].replace("*", "").strip().casefold()
        if normalized_status == status.casefold():
            routes.add(route_match.group(1).split(" <", maxsplit=1)[0])

    return routes


def _optional_route_contract_text(repo_root: Path) -> str | None:
    path = repo_root / ROUTE_CONTRACT_TARGET_PATH
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8")
    if "## Canonical Route Matrix" not in content:
        return None
    return content


def _assert_graph_workflows_stay_deferred(content: str) -> None:
    lowered = content.casefold()
    assert "deferred" in lowered
    assert any(marker in lowered for marker in GRAPH_DEFERRED_MARKERS)


def test_primary_wiki_routes_stay_exact_current_truth(repo_root: Path) -> None:
    readme_content = (repo_root / "README.md").read_text(encoding="utf-8")
    workflow_content = (repo_root / "skill" / "workflows" / "wiki.md").read_text(
        encoding="utf-8"
    )

    assert _extract_readme_current_routes(readme_content) == PRIMARY_CURRENT_ROUTES
    assert (
        _extract_workflow_routes_by_status(workflow_content, "Current")
        == PRIMARY_CURRENT_ROUTES
    )
    assert _extract_workflow_routes_by_status(workflow_content, "Deferred") == {
        "sync",
        "edit",
        "merge",
    }
    _assert_graph_workflows_stay_deferred(workflow_content)


def test_advanced_and_support_routes_stay_distinct_from_primary_wiki_routes(
    repo_root: Path,
) -> None:
    readme_content = (repo_root / "README.md").read_text(encoding="utf-8")
    skill_content = (repo_root / "skill" / "SKILL.md").read_text(encoding="utf-8")
    workflow_content = (repo_root / "skill" / "workflows" / "wiki.md").read_text(
        encoding="utf-8"
    )

    readme_commands = _extract_current_commands(
        readme_content, "## Current shipped CLI surface"
    )
    skill_commands = _extract_current_commands(skill_content, "## Current shipped commands")
    cli_commands = {
        command.name for command in app.commands.values() if command.name is not None
    }

    assert cli_commands == EXPECTED_CLI_COMMANDS
    assert readme_commands == cli_commands
    assert skill_commands == cli_commands

    readme_primary_routes = _extract_readme_current_routes(readme_content)
    workflow_primary_routes = _extract_workflow_routes_by_status(
        workflow_content, "Current"
    )

    assert ADVANCED_CURRENT_PASSTHROUGHS.issubset(cli_commands)
    assert SHIPPED_SUPPORT_NOT_PRIMARY_ROUTE in cli_commands

    for route in ADVANCED_CURRENT_PASSTHROUGHS | {SHIPPED_SUPPORT_NOT_PRIMARY_ROUTE}:
        assert route in readme_commands
        assert route in skill_commands
        assert route not in readme_primary_routes
        assert route not in workflow_primary_routes


def test_deferred_routes_and_mcp_write_claims_fail_closed(repo_root: Path) -> None:
    readme_content = (repo_root / "README.md").read_text(encoding="utf-8")
    skill_content = (repo_root / "skill" / "SKILL.md").read_text(encoding="utf-8")
    workflow_content = (repo_root / "skill" / "workflows" / "wiki.md").read_text(
        encoding="utf-8"
    )
    quickstart_content = (
        repo_root / "docs" / "reference" / "claude-code-wiki-quickstart.md"
    ).read_text(encoding="utf-8")
    contract_content = (
        repo_root / "docs" / "architecture" / "skill-and-agent-interface-contract.md"
    ).read_text(encoding="utf-8")

    current_routes = _extract_readme_current_routes(readme_content)
    workflow_current_routes = _extract_workflow_routes_by_status(
        workflow_content, "Current"
    )

    for route in DEFERRED_ROUTES:
        assert route not in current_routes
        assert route not in workflow_current_routes
        assert f"`{route}`" in readme_content
        assert route in skill_content
        assert f"`{route}`" in workflow_content
        assert f"`{route}`" in quickstart_content

    for content in [readme_content, skill_content, workflow_content, quickstart_content]:
        _assert_graph_workflows_stay_deferred(content)

    assert "read-only MCP via `snowiki mcp`" in readme_content
    assert "Mutation remains CLI-mediated. MCP write support is not shipped." in readme_content
    assert "- read-only MCP via `snowiki mcp`" in skill_content
    assert "- MCP write support is not shipped" in skill_content
    assert "Do not claim MCP write support" in workflow_content
    assert "It does not grant MCP write support." in quickstart_content
    assert "- treat the read-only MCP surface as retrieval-only" in quickstart_content
    assert (
        "Mutation capability**: Must flow through the authoritative CLI/runtime path, not through MCP."
        in contract_content
    )
    assert (
        "Write-oriented names such as `edit`, `ingest`, `merge`, `sync`, `status`, and `write` are not exposed as MCP tools."
        in contract_content
    )
    assert frozenset(
        {"edit", "ingest", "merge", "status", "sync", "write"}
    ) == WRITE_OPERATION_NAMES

    route_contract_content = _optional_route_contract_text(repo_root)
    if route_contract_content is not None:
        for route in (
            PRIMARY_CURRENT_ROUTES
            | ADVANCED_CURRENT_PASSTHROUGHS
            | {SHIPPED_SUPPORT_NOT_PRIMARY_ROUTE}
            | DEFERRED_ROUTES
        ):
            assert route in route_contract_content
        _assert_graph_workflows_stay_deferred(route_contract_content)
        assert (
            "read-only MCP" in route_contract_content
            or "MCP write support is not shipped" in route_contract_content
        )
