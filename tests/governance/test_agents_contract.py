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

    required_markers = [
        "repo-wide rules",
        "Child `AGENTS.md` files inherit these rules",
        "## Toolchain",
        "## Always",
        "## Never",
        "## Verification Matrix",
        "## Ownership",
        "## Path Contract",
        "## PR Discipline",
    ]

    for marker in required_markers:
        assert marker in content, f"Missing required AGENTS contract marker: {marker}"


def test_root_agents_contract_commands(repo_root):
    content = (repo_root / "AGENTS.md").read_text()

    required_commands = [
        "uv run ruff check src/snowiki tests",
        "uv run ty check",
        "uv run pytest",
        "uv run pytest -m integration",
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
        "docs/architecture/",
        "docs/reference/",
        "docs/roadmap/",
        "docs/archive/",
        "benchmarks/",
        "vault-template/",
        "skill/",
        "fixtures/",
    ]

    assert "## Ownership" in content
    for path in required_paths:
        assert path in content, f"Missing governed path in AGENTS.md: {path}"


def test_root_agents_contract_policies(repo_root):
    content = (repo_root / "AGENTS.md").read_text()

    content_no_backticks = content.replace("`", "")

    assert "shared repo" not in content_no_backticks.lower()
    for statement in [
        "repo-wide rules",
        "child AGENTS are delta-only",
        "inherit root policy",
        "Force-add or commit ignored internal artifacts",
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
    root_commands = [
        "uv run ruff check src/snowiki tests",
        "uv run ty check",
        "uv run pytest",
    ]

    for path in module.CHILD_AGENT_FILES:
        content = path.read_text()
        for cmd in root_commands:
            assert cmd not in content, (
                f"Duplicated root command '{cmd}' found in {path.as_posix()}"
            )
