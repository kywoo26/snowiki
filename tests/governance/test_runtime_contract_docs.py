from __future__ import annotations

from pathlib import Path


def test_readme_quick_start_uses_cli_runtime(repo_root: Path) -> None:
    content = (repo_root / "README.md").read_text(encoding="utf-8")
    quick_start = content.split("## Quick Start", maxsplit=1)[1].split(
        "## Current shipped CLI surface", maxsplit=1
    )[0]

    assert "informative mirror" in quick_start
    assert "canonical contract" in quick_start
    assert "snowiki --help" in content
    assert "uv tool install --from . snowiki" in content
    assert "claude-code-wiki-quickstart.md" in quick_start
    assert "snowiki status --output json" in quick_start
    assert "snowiki lint --output json" in quick_start
    assert "bun install -g @tobilu/qmd" not in quick_start


def test_skill_and_agent_interface_contract_is_canonical(repo_root: Path) -> None:
    path = repo_root / "docs" / "architecture" / "skill-and-agent-interface-contract.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")

    assert "canonical contract owner" in content
    assert "normative (authoritative) and informative (reference) surfaces" in content
    assert "`snowiki` CLI" in content
    assert "authoritative runtime contract" in content
