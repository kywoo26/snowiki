from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Protocol, cast

import pytest


class FindingLike(Protocol):
    code: str
    path: str
    message: str


class ClickModuleLike(Protocol):
    def echo(self, message: str) -> None: ...


class GovernanceModule(Protocol):
    INHERITANCE_MARKER: str
    CHILD_AGENT_FILES: tuple[Path, ...]
    click: ClickModuleLike

    def collect_findings(self, root: Path) -> list[FindingLike]: ...

    def render_report(self, findings: list[FindingLike]) -> str: ...

    def main(self, argv: list[str]) -> int: ...


def _load_module(repo_root: Path) -> GovernanceModule:
    module_path = repo_root / "scripts/check_governance.py"
    spec = importlib.util.spec_from_file_location("check_governance", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    _ = spec.loader.exec_module(module)
    return cast(GovernanceModule, cast(object, module))


def _write(tmp_path: Path, relative_path: str, content: str) -> None:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")


def _seed_valid_repo(tmp_path: Path, module: GovernanceModule) -> None:
    root_agents = """# Root Governance

## Commands

```bash
uv sync --group dev
uv run pre-commit install
uv run pytest
```
"""
    child_agents = f"# Child Governance\n\n{module.INHERITANCE_MARKER}\n"

    _write(tmp_path, "AGENTS.md", root_agents)
    for relative_path in module.CHILD_AGENT_FILES:
        _write(tmp_path, relative_path.as_posix(), child_agents)
    _write(tmp_path, "benchmarks/README.md", "# Benchmarks\n")
    _write(tmp_path, "vault-template/CLAUDE.md", "# Vault Schema\n")
    _write(tmp_path, "skill/SKILL.md", "# Skill\n")


def test_collect_findings_is_clean_for_valid_repo(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    module = _load_module(repo_root)
    _seed_valid_repo(tmp_path, module)

    findings = module.collect_findings(tmp_path)

    assert findings == []
    assert module.render_report(findings).splitlines() == [
        "Governance advisory report",
        "status: clean",
        "No governance drift findings.",
    ]


def test_collect_findings_reports_missing_and_drift_cases(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    module = _load_module(repo_root)
    _seed_valid_repo(tmp_path, module)

    _write(
        tmp_path,
        "benchmarks/AGENTS.md",
        "# Child Governance\n\nuv run pytest\n",
    )
    (tmp_path / "skill/SKILL.md").unlink()
    (tmp_path / "vault-template/AGENTS.md").unlink()

    findings = module.collect_findings(tmp_path)
    codes_to_paths = {(finding.code, finding.path) for finding in findings}

    assert ("missing-agents", "vault-template/AGENTS.md") in codes_to_paths
    assert ("missing-canonical-surface", "skill/SKILL.md") in codes_to_paths
    assert (
        "missing-inheritance-marker",
        "benchmarks/AGENTS.md",
    ) in codes_to_paths
    assert ("duplicated-root-command", "benchmarks/AGENTS.md") in codes_to_paths


def test_main_is_advisory_by_default_and_blocking_in_strict_mode(
    tmp_path: Path,
    repo_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_module(repo_root)
    _seed_valid_repo(tmp_path, module)
    (tmp_path / "benchmarks/README.md").unlink()

    report_exit_code = module.main(["--report", "--root", str(tmp_path)])
    report_output = capsys.readouterr().out

    strict_exit_code = module.main(["--strict", "--root", str(tmp_path)])
    strict_output = capsys.readouterr().out

    assert report_exit_code == 0
    assert strict_exit_code == 1
    assert "status: advisory" in report_output
    assert "status: advisory" in strict_output
    assert "benchmarks/README.md" in strict_output


def test_main_uses_click_echo_for_output(
    tmp_path: Path,
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(repo_root)
    _seed_valid_repo(tmp_path, module)

    emitted: list[str] = []

    def _fake_echo(message: str) -> None:
        emitted.append(message)

    monkeypatch.setattr(module.click, "echo", _fake_echo)

    exit_code = module.main(["--report", "--root", str(tmp_path)])

    assert exit_code == 0
    assert emitted == [module.render_report([])]
