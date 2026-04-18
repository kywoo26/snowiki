from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Protocol, cast

import pytest


class CommitMessageModule(Protocol):
    def validate(self, message: str) -> list[str]: ...


def _load_module(repo_root: Path) -> CommitMessageModule:
    module_path = repo_root / "scripts/check_commit_message.py"
    spec = importlib.util.spec_from_file_location("check_commit_message", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    _ = spec.loader.exec_module(module)
    return cast(CommitMessageModule, cast(object, module))


class TestValidMessages:
    def test_feat_with_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        assert mod.validate("feat(cli): add new command\n") == []

    def test_fix_with_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        assert mod.validate("fix(search): correct ranking\n") == []

    def test_docs_without_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        assert mod.validate("docs: update readme\n") == []

    def test_refactor_without_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        assert mod.validate("refactor: simplify parser\n") == []

    def test_test_without_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        assert mod.validate("test: add coverage for edge case\n") == []

    def test_ci_without_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        assert mod.validate("ci: update workflow\n") == []

    def test_deps_without_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        assert mod.validate("deps: bump typer\n") == []

    def test_multiline_with_body(self, repo_root: Path):
        mod = _load_module(repo_root)
        message = "feat(cli): add new command\n\nThis adds the new command.\n"
        assert mod.validate(message) == []


class TestInvalidSubject:
    def test_empty_subject(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("\n")
        assert any("empty" in e.lower() for e in errors)

    def test_missing_type_prefix(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("add new command\n")
        assert any("type(scope)" in e.lower() for e in errors)

    def test_invalid_type(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("invalid(scope): something\n")
        assert any("invalid type" in e.lower() for e in errors)

    def test_invalid_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(invalid): something\n")
        assert any("invalid scope" in e.lower() for e in errors)

    def test_feat_missing_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat: missing scope\n")
        assert any("requires a scope" in e.lower() for e in errors)

    def test_fix_missing_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("fix: missing scope\n")
        assert any("requires a scope" in e.lower() for e in errors)

    def test_too_long_subject(self, repo_root: Path):
        mod = _load_module(repo_root)
        long_subject = "feat(cli): " + "a" * 70
        errors = mod.validate(long_subject + "\n")
        assert any("exceeds" in e.lower() for e in errors)

    def test_trailing_period(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(cli): add command.\n")
        assert any("period" in e.lower() for e in errors)

    def test_empty_after_prefix(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(cli): \n")
        assert any("empty" in e.lower() for e in errors)


class TestBannedMarkers:
    def test_co_authored_by_in_body(self, repo_root: Path):
        mod = _load_module(repo_root)
        message = "feat(cli): add new command\n\nCo-authored-by: someone\n"
        errors = mod.validate(message)
        assert any("co-authored-by" in e.lower() for e in errors)

    def test_ultraworked_with_in_body(self, repo_root: Path):
        mod = _load_module(repo_root)
        message = "feat(cli): add new command\n\nUltraworked with agent\n"
        errors = mod.validate(message)
        assert any("ultraworked with" in e.lower() for e in errors)

    def test_coworker_in_body(self, repo_root: Path):
        mod = _load_module(repo_root)
        message = "feat(cli): add new command\n\nCoworker: agent\n"
        errors = mod.validate(message)
        assert any("coworker" in e.lower() for e in errors)

    def test_banned_marker_case_insensitive(self, repo_root: Path):
        mod = _load_module(repo_root)
        message = "feat(cli): add new command\n\nCO-AUTHORED-BY: someone\n"
        errors = mod.validate(message)
        assert any("co-authored-by" in e.lower() for e in errors)

    def test_no_banned_marker(self, repo_root: Path):
        mod = _load_module(repo_root)
        message = "feat(cli): add new command\n\nThis is fine.\n"
        assert mod.validate(message) == []
