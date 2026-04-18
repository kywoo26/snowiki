from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Protocol, cast


class PRGovernanceModule(Protocol):
    def validate(self, title: str, body: str) -> list[str]: ...


def _load_module(repo_root: Path) -> PRGovernanceModule:
    module_path = repo_root / "scripts/check_pr_governance.py"
    spec = importlib.util.spec_from_file_location("check_pr_governance", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    _ = spec.loader.exec_module(module)
    return cast(PRGovernanceModule, cast(object, module))


class TestValidateTitle:
    def test_valid_title_with_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(cli): add new command", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert not any("title" in e.lower() for e in errors)

    def test_valid_title_without_scope_for_docs(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("docs: update readme", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] Docs\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert not any("title" in e.lower() for e in errors)

    def test_valid_title_without_scope_for_refactor(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("refactor: simplify parser", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert not any("title" in e.lower() for e in errors)

    def test_invalid_type(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("invalid(scope): something", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("invalid type" in e.lower() for e in errors)

    def test_invalid_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(invalid): something", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("invalid scope" in e.lower() for e in errors)

    def test_feat_requires_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat: missing scope", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("requires a scope" in e.lower() for e in errors)

    def test_fix_requires_scope(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("fix: missing scope", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("requires a scope" in e.lower() for e in errors)

    def test_too_long_title(self, repo_root: Path):
        mod = _load_module(repo_root)
        long_title = "feat(cli): " + "a" * 70
        errors = mod.validate(long_title, "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("exceeds" in e.lower() for e in errors)

    def test_trailing_period(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(cli): add command.", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("period" in e.lower() for e in errors)

    def test_empty_title(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("empty" in e.lower() for e in errors)

    def test_missing_subject_after_prefix(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(cli): ", "## Problem\n\n## Proposed Change\n\n## Surfaces Touched\n- [x] CLI\n\n## Verification\n- [x] tests\n\n## Contract Sync\n- [x] N/A")
        assert any("empty" in e.lower() for e in errors)


class TestValidateBody:
    def test_valid_body(self, repo_root: Path):
        mod = _load_module(repo_root)
        body = """## Problem / Motivation
Slow query.

## Proposed Change
Add index.

## Surfaces Touched
- [x] Search / Retrieval

## Verification
- [x] `uv run pytest`

## Contract Sync
- [x] N/A (no surface change)
"""
        errors = mod.validate("feat(search): add index", body)
        assert errors == []

    def test_missing_problem_section(self, repo_root: Path):
        mod = _load_module(repo_root)
        body = """## Proposed Change
Add index.

## Surfaces Touched
- [x] Search / Retrieval

## Verification
- [x] `uv run pytest`

## Contract Sync
- [x] N/A
"""
        errors = mod.validate("feat(search): add index", body)
        assert any("problem / motivation" in e.lower() for e in errors)

    def test_empty_placeholder_section(self, repo_root: Path):
        mod = _load_module(repo_root)
        body = """## Problem / Motivation
<!-- Why this change? -->

## Proposed Change
Add index.

## Surfaces Touched
- [x] Search / Retrieval

## Verification
- [x] `uv run pytest`

## Contract Sync
- [x] N/A
"""
        errors = mod.validate("feat(search): add index", body)
        assert any("placeholder" in e.lower() for e in errors)

    def test_no_checked_surfaces(self, repo_root: Path):
        mod = _load_module(repo_root)
        body = """## Problem / Motivation
Slow query.

## Proposed Change
Add index.

## Surfaces Touched
- [ ] CLI
- [ ] Search / Retrieval

## Verification
- [x] `uv run pytest`

## Contract Sync
- [x] N/A
"""
        errors = mod.validate("feat(search): add index", body)
        assert any("surfaces touched" in e.lower() for e in errors)

    def test_no_checked_verification(self, repo_root: Path):
        mod = _load_module(repo_root)
        body = """## Problem / Motivation
Slow query.

## Proposed Change
Add index.

## Surfaces Touched
- [x] Search / Retrieval

## Verification
- [ ] `uv run pytest`

## Contract Sync
- [x] N/A
"""
        errors = mod.validate("feat(search): add index", body)
        assert any("verification" in e.lower() for e in errors)

    def test_no_checked_contract_sync(self, repo_root: Path):
        mod = _load_module(repo_root)
        body = """## Problem / Motivation
Slow query.

## Proposed Change
Add index.

## Surfaces Touched
- [x] Search / Retrieval

## Verification
- [x] `uv run pytest`

## Contract Sync
- [ ] N/A
- [ ] AGENTS.md updated
"""
        errors = mod.validate("feat(search): add index", body)
        assert any("contract sync" in e.lower() for e in errors)

    def test_empty_body(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("feat(search): add index", "")
        assert any("empty" in e.lower() for e in errors)


class TestValidateBoth:
    def test_both_valid(self, repo_root: Path):
        mod = _load_module(repo_root)
        body = """## Problem / Motivation
Slow query.

## Proposed Change
Add index.

## Surfaces Touched
- [x] Search / Retrieval

## Verification
- [x] `uv run pytest`

## Contract Sync
- [x] N/A (no surface change)
"""
        errors = mod.validate("feat(search): add index", body)
        assert errors == []

    def test_both_invalid(self, repo_root: Path):
        mod = _load_module(repo_root)
        errors = mod.validate("bad title", "")
        assert len(errors) >= 2
