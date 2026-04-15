from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol, cast

import pytest


class Step1ProofTargetLike(Protocol):
    path: Path
    label: str


class PromotionModule(Protocol):
    STEP1_PROOF_TARGETS: tuple[Step1ProofTargetLike, ...]
    subprocess: Any

    def main(self, argv: list[str]) -> int: ...


def _load_module(repo_root: Path) -> PromotionModule:
    module_path = repo_root / "scripts/promote_lexical_policy.py"
    spec = importlib.util.spec_from_file_location("promote_lexical_policy", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    _ = spec.loader.exec_module(module)
    return cast(PromotionModule, cast(object, module))


def _seed_step1_targets(tmp_path: Path, module: PromotionModule) -> None:
    for target in module.STEP1_PROOF_TARGETS:
        path = tmp_path / target.path
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("", encoding="utf-8")


def test_main_runs_step1_proofs_only_and_exits_zero(
    tmp_path: Path,
    repo_root: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(repo_root)
    _seed_step1_targets(tmp_path, module)
    calls: list[dict[str, object]] = []

    def fake_run(
        command: list[str], *, cwd: Path, check: bool, text: bool
    ) -> SimpleNamespace:
        calls.append({"command": command, "cwd": cwd, "check": check, "text": text})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    exit_code = module.main(["--strict", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert calls == [
        {
            "command": [
                "uv",
                "run",
                "pytest",
                "tests/search/test_runtime_lexical_separation.py",
                "tests/governance/test_retrieval_surface_parity.py",
                "tests/daemon/test_warm_index.py",
                "tests/cli/test_rebuild.py",
                "tests/rebuild/test_integrity.py",
            ],
            "cwd": tmp_path,
            "check": False,
            "text": True,
        }
    ]
    assert "benchmark/runtime separation" in output
    assert "tests/rebuild/test_integrity.py" in output


def test_main_fails_closed_when_a_step1_target_is_missing(
    tmp_path: Path,
    repo_root: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(repo_root)
    for target in module.STEP1_PROOF_TARGETS[:-1]:
        path = tmp_path / target.path
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("", encoding="utf-8")

    def fail_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise AssertionError("pytest must not run when a Step 1 target is missing")

    monkeypatch.setattr(module.subprocess, "run", fail_run)

    exit_code = module.main(["--strict", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 2
    assert "missing Step 1 proof target(s):" in output
    assert "tests/rebuild/test_integrity.py" in output


def test_main_returns_non_zero_when_a_step1_proof_fails(
    tmp_path: Path,
    repo_root: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(repo_root)
    _seed_step1_targets(tmp_path, module)

    def fake_run(
        command: list[str], *, cwd: Path, check: bool, text: bool
    ) -> SimpleNamespace:
        del cwd, check, text
        assert command[0:3] == ["uv", "run", "pytest"]
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    exit_code = module.main(["--strict", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Step 1 promotion gate failed (exit_code=1)" in output
