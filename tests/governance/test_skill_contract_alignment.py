from __future__ import annotations

import re
from pathlib import Path

from snowiki.cli.main import app


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


def _cli_commands() -> set[str]:
    return {
        command.name for command in app.commands.values() if command.name is not None
    }


def test_skill_declares_cli_as_authoritative_runtime(repo_root: Path) -> None:
    content = (repo_root / "skill" / "SKILL.md").read_text(encoding="utf-8")

    assert (
        "The authoritative runtime contract is the installed `snowiki` CLI." in content
    )
    assert "fileback" in content
    assert "qmd remains lineage/reference material" in content
    assert "not the current canonical runtime search engine" in content
    assert "sync" in content
    assert "deferred" in content.casefold()


def test_skill_workflow_marks_qmd_flows_as_non_canonical(repo_root: Path) -> None:
    content = (repo_root / "skill" / "workflows" / "wiki.md").read_text(
        encoding="utf-8"
    )

    assert (
        "authoritative shipped runtime contract is the installed `snowiki` command"
        in content
    )
    assert (
        "Do not assume a qmd update/embed loop is the current shipped behavior"
        in content
    )
    assert "fileback" in content
    assert "Deferred" in content


def test_skill_docs_current_commands_align_with_cli_registry(repo_root: Path) -> None:
    cli_commands = _cli_commands()

    skill_content = (repo_root / "skill" / "SKILL.md").read_text(encoding="utf-8")
    workflow_content = (repo_root / "skill" / "workflows" / "wiki.md").read_text(
        encoding="utf-8"
    )

    assert (
        _extract_current_commands(skill_content, "## Current shipped commands")
        == cli_commands
    )
    assert (
        _extract_current_commands(workflow_content, "Current shipped CLI surface:")
        == cli_commands
    )

    assert "fileback preview" in skill_content
    assert "fileback apply" in skill_content
    assert "fileback preview" in workflow_content
    assert "fileback apply" in workflow_content


def test_canonical_contract_names_skill_as_informative_surface(repo_root: Path) -> None:
    content = (
        repo_root / "docs" / "architecture" / "skill-and-agent-interface-contract.md"
    ).read_text(encoding="utf-8")

    assert "`snowiki` CLI" in content
    assert "authoritative runtime contract" in content
    assert "`skill/SKILL.md`" in content
    assert "reference layer, not a runtime contract" in content
