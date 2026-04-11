from __future__ import annotations

FORBIDDEN_REPO_ROOT_PATTERNS = (
    "Path(__file__).resolve().parents[",
    "Path.cwd()",
)

APPROVED_HELPERS = (
    "snowiki.config.get_repo_root",
    "snowiki.config.resolve_repo_asset_path",
    "snowiki.storage.zones.relative_to_root",
    "snowiki.storage.zones.relative_to_root_or_posix",
)


def test_runtime_benchmark_modules_use_approved_repo_asset_helpers(
    repo_root,
) -> None:
    target_files = (
        repo_root / "src/snowiki/bench/corpus.py",
        repo_root / "src/snowiki/bench/baselines.py",
        repo_root / "src/snowiki/bench/phase1_latency.py",
        repo_root / "src/snowiki/bench/phase1_correctness.py",
    )

    for path in target_files:
        content = path.read_text(encoding="utf-8")
        assert "Path(__file__).resolve().parents[" not in content, path.as_posix()

    assert "resolve_repo_asset_path" in target_files[0].read_text(encoding="utf-8")
    assert "resolve_repo_asset_path" in target_files[1].read_text(encoding="utf-8")
    assert "get_repo_root" in target_files[2].read_text(encoding="utf-8")
    assert "resolve_repo_asset_path" in target_files[2].read_text(encoding="utf-8")
    assert "relative_to_root_or_posix" in target_files[2].read_text(encoding="utf-8")
    assert "resolve_repo_asset_path" in target_files[3].read_text(encoding="utf-8")


def test_snowiki_scope_does_not_add_new_ad_hoc_repo_root_or_cwd_coupling(
    repo_root,
    snowiki_dir,
) -> None:
    python_files = sorted(snowiki_dir.rglob("*.py"))

    for path in python_files:
        content = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_REPO_ROOT_PATTERNS:
            assert pattern not in content, (
                f"{path.relative_to(repo_root)} contains {pattern}"
            )


def test_tests_use_fixtures_not_root_constants(repo_root) -> None:
    test_files = sorted((repo_root / "tests").rglob("*.py"))

    for path in test_files:
        if path.name == "conftest.py":
            continue
        if "governance" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if "ROOT = Path(__file__)" in content or "ROOT = get_repo_root()" in content:
            msg = (
                f"{path.relative_to(repo_root)} uses ROOT constant. "
                "Use pytest fixtures from conftest.py instead."
            )
            raise AssertionError(msg)
