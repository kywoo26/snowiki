from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Protocol, cast


class GovernanceModule(Protocol):
    INHERITANCE_MARKER: str
    CHILD_AGENT_FILES: tuple[Path, ...]


def _load_module(repo_root: Path) -> GovernanceModule:
    module_path = repo_root / "scripts/check_governance.py"
    spec = importlib.util.spec_from_file_location(
        "check_governance_agents", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    _ = spec.loader.exec_module(module)
    return cast(GovernanceModule, cast(object, module))


def test_root_agents_contract_exists(repo_root):
    assert (repo_root / "AGENTS.md").exists()


def test_root_agents_contract_sections(repo_root):
    content = (repo_root / "AGENTS.md").read_text()

    required_sections = [
        "## Commands",
        "## Toolchain",
        "## Always",
        "## Ask First",
        "## Never",
        "## Verification Matrix",
        "## Ownership",
        "## Path Contract",
        "## PR Discipline",
    ]

    for section in required_sections:
        assert section in content, f"Missing required section: {section}"


def test_root_agents_contract_commands(repo_root):
    content = (repo_root / "AGENTS.md").read_text()

    required_commands = [
        "uv sync --group dev",
        "uv run pre-commit install",
        "uv run ruff check src/snowiki tests",
        "uv run ty check",
        "uv run pytest",
        "uv run python -m compileall src/snowiki/",
        "uv run snowiki benchmark",
    ]

    for command in required_commands:
        assert command in content, f"Missing required command: {command}"


def test_root_agents_contract_ownership(repo_root):
    content = (repo_root / "AGENTS.md").read_text()

    required_paths = [
        "src/snowiki/",
        "tests/",
        "scripts/",
        "benchmarks/",
        "vault-template/",
        "skill/",
        "fixtures/",
    ]

    assert "## Ownership" in content

    ownership_section = content.split("## Ownership")[1].split("##")[0]
    for path in required_paths:
        assert path in ownership_section, f"Missing path in ownership table: {path}"


def test_root_agents_contract_policies(repo_root):
    content = (repo_root / "AGENTS.md").read_text()

    content_no_backticks = content.replace("`", "")

    assert ".sisyphus" not in content_no_backticks.lower()
    assert "shared repo" not in content_no_backticks.lower()
    for statement in [
        "repo-wide rules",
        "child AGENTS are delta-only",
        "inherit root policy",
    ]:
        assert statement.lower() in content_no_backticks.lower(), (
            f"Missing required policy statement: {statement}"
        )


def test_child_agents_exist(repo_root):
    module = _load_module(repo_root)

    for path in module.CHILD_AGENT_FILES:
        assert path.exists(), f"Missing child AGENTS file: {path.as_posix()}"


def test_child_agents_inheritance_statement(repo_root):
    module = _load_module(repo_root)

    for path in module.CHILD_AGENT_FILES:
        content = path.read_text()
        assert module.INHERITANCE_MARKER in content, (
            f"Missing inheritance statement in {path.as_posix()}"
        )


def test_child_agents_no_command_duplication(repo_root):
    module = _load_module(repo_root)
    root_content = (repo_root / "AGENTS.md").read_text()
    if "## Commands" in root_content:
        sample_commands = [
            "uv sync --group dev",
            "uv run pre-commit install",
            "uv run ruff check src/snowiki tests",
        ]

        for path in module.CHILD_AGENT_FILES:
            content = path.read_text()
            for cmd in sample_commands:
                assert cmd not in content, (
                    f"Duplicated root command '{cmd}' found in {path.as_posix()}"
                )


def test_child_agents_conciseness(repo_root):
    module = _load_module(repo_root)

    for path in module.CHILD_AGENT_FILES:
        lines = path.read_text().splitlines()
        assert len(lines) <= 40, (
            f"Child AGENTS file {path.as_posix()} is too long ({len(lines)} lines)"
        )
