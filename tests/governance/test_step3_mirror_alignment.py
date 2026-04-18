from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app
from snowiki.mcp.server import WRITE_OPERATION_NAMES

README_PATH = Path("README.md")
SKILL_PATH = Path("skill/SKILL.md")
WORKFLOW_PATH = Path("skill/workflows/wiki.md")
QUICKSTART_PATH = Path("docs/reference/claude-code-wiki-quickstart.md")
ROUTE_CONTRACT_PATH = Path(
    "docs/roadmap/step3_wiki-skill-design/01-wiki-route-contract.md"
)


def _read(repo_root: Path, relative_path: Path) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8")


def _invoke_help() -> str:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    return result.output


def _extract_help_commands(help_output: str) -> set[str]:
    section = help_output.split("Commands:", maxsplit=1)[1]
    commands: set[str] = set()

    for line in section.splitlines():
        match = re.match(r"^\s{2,}([a-z0-9_-]+)(?:\s{2,}.*)?$", line)
        if match is not None:
            commands.add(match.group(1))

    return commands


def _extract_documented_cli_commands(content: str, heading: str) -> set[str]:
    section = content.split(heading, maxsplit=1)[1]
    commands: set[str] = set()

    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") and stripped != heading:
            break
        match = re.search(r"`snowiki ([^`]+)`", stripped)
        if match is None:
            continue
        command = match.group(1)
        if " " not in command:
            commands.add(command)

    return commands


def _extract_route_contract_bucket(content: str, bucket: str) -> set[str]:
    section = content.split("## Canonical Route Matrix", maxsplit=1)[1].split(
        "## Route Families", maxsplit=1
    )[0]
    routes: set[str] = set()

    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| Skill Route |"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 4 or set(cells[0]) == {":", "-"}:
            continue
        route = cells[0].strip("`")
        route_bucket = cells[2]
        if route and route_bucket == bucket:
            routes.add(route)

    return routes


def _extract_readme_current_routes(content: str) -> set[str]:
    section = content.split("## Claude Code `/wiki` status", maxsplit=1)[1].split(
        "## Machine-usable surfaces today", maxsplit=1
    )[0]
    match = re.search(r"^- current: (?P<routes>.+)$", section, flags=re.MULTILINE)
    assert match is not None
    return set(re.findall(r"`([^`]+)`", match.group("routes")))


def _extract_readme_deferred_routes(content: str) -> set[str]:
    section = content.split("## Claude Code `/wiki` status", maxsplit=1)[1].split(
        "## Machine-usable surfaces today", maxsplit=1
    )[0]
    match = re.search(r"^- deferred: (?P<routes>.+)$", section, flags=re.MULTILINE)
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


def _extract_skill_deferred_routes(content: str) -> set[str]:
    section = content.split("### Deferred / broader workflow ideas", maxsplit=1)[1].split(
        "## Search Strategy", maxsplit=1
    )[0]
    routes: set[str] = set()

    for line in section.splitlines():
        match = re.match(r"^-\s+([a-z]+)$", line.strip())
        if match is not None:
            routes.add(match.group(1))

    return routes


def _extract_quickstart_deferred_routes(content: str) -> set[str]:
    section = content.split("## 5. What is deferred", maxsplit=1)[1].split(
        "## 6. Current `/wiki` mental model", maxsplit=1
    )[0]
    routes: set[str] = set()

    for line in section.splitlines():
        match = re.match(r"^-\s+`([a-z]+)`$", line.strip())
        if match is not None:
            routes.add(match.group(1))

    return routes


def test_cli_help_command_surface_matches_direct_mirrors(repo_root: Path) -> None:
    help_commands = _extract_help_commands(_invoke_help())

    assert _extract_documented_cli_commands(
        _read(repo_root, README_PATH), "## Current shipped CLI surface"
    ) == help_commands
    assert _extract_documented_cli_commands(
        _read(repo_root, SKILL_PATH), "## Current shipped commands"
    ) == help_commands
    assert _extract_documented_cli_commands(
        _read(repo_root, WORKFLOW_PATH), "Current shipped CLI surface:"
    ) == help_commands


def test_readme_primary_current_routes_match_route_contract(repo_root: Path) -> None:
    route_contract_content = _read(repo_root, ROUTE_CONTRACT_PATH)
    readme_content = _read(repo_root, README_PATH)

    assert _extract_readme_current_routes(readme_content) == _extract_route_contract_bucket(
        route_contract_content, "Primary Current"
    )


def test_deferred_write_like_routes_stay_in_lockstep_across_direct_mirrors(
    repo_root: Path,
) -> None:
    readme_deferred_routes = _extract_readme_deferred_routes(_read(repo_root, README_PATH))
    skill_deferred_routes = _extract_skill_deferred_routes(_read(repo_root, SKILL_PATH))
    workflow_deferred_routes = _extract_workflow_routes_by_status(
        _read(repo_root, WORKFLOW_PATH), "Deferred"
    )
    quickstart_deferred_routes = _extract_quickstart_deferred_routes(
        _read(repo_root, QUICKSTART_PATH)
    )

    assert skill_deferred_routes == readme_deferred_routes
    assert workflow_deferred_routes == readme_deferred_routes
    assert quickstart_deferred_routes == readme_deferred_routes


def test_write_operation_names_fail_closed_over_mirrored_deferred_routes(
    repo_root: Path,
) -> None:
    deferred_routes = _extract_readme_deferred_routes(_read(repo_root, README_PATH))

    assert deferred_routes.issubset(WRITE_OPERATION_NAMES)


def test_help_and_version_entrypoints_stay_aligned(repo_root: Path) -> None:
    help_output = _invoke_help()

    assert "-h, --help" in help_output
    assert "--version" not in help_output

    for relative_path in (README_PATH, WORKFLOW_PATH, QUICKSTART_PATH):
        content = _read(repo_root, relative_path)
        assert "snowiki --help" in content
        assert "snowiki --version" not in content
