from __future__ import annotations


def test_readme_quick_start_uses_cli_runtime(repo_root) -> None:
    content = (repo_root / "README.md").read_text(encoding="utf-8")
    quick_start = content.split("## Quick Start", maxsplit=1)[1].split(
        "## Historical workflow surface", maxsplit=1
    )[0]

    assert "informative mirror" in quick_start
    assert "canonical contract" in quick_start
    assert "installed `snowiki` command" in quick_start
    assert "snowiki --help" in content
    assert "uv tool install --from . snowiki" in content
    assert "/wiki query" not in quick_start
    assert "bun install -g @tobilu/qmd" not in quick_start


def test_skill_declares_cli_as_authoritative_runtime(repo_root) -> None:
    content = (repo_root / "skill" / "SKILL.md").read_text(encoding="utf-8")

    assert (
        "The authoritative runtime contract is the installed `snowiki` CLI." in content
    )
    assert "qmd remains lineage/reference material" in content
    assert "not the current canonical runtime search engine" in content
    assert "sync" in content
    assert "deferred" in content.casefold()


def test_skill_workflow_marks_qmd_flows_as_non_canonical(repo_root) -> None:
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
    assert "deferred ideas" in content


def test_skill_and_agent_interface_contract_is_canonical(repo_root) -> None:
    path = repo_root / "docs" / "architecture" / "skill-and-agent-interface-contract.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")

    assert "canonical contract owner" in content
    assert "normative (authoritative) and informative (reference) surfaces" in content
    assert "`snowiki` CLI" in content
    assert "authoritative runtime contract" in content
