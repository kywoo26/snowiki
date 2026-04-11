from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNOWIKI_ROOT = ROOT / "snowiki"

FORBIDDEN_REPO_ROOT_PATTERNS = (
    "Path(__file__).resolve().parents[",
    "Path.cwd()",
)
TEMPORARY_EXEMPT_SURFACES = (
    "tests/**",
    "scripts/**",
    "skill/**",
    "vault-template/**",
)
EXPECTED_HELPERS = (
    "snowiki.config.get_repo_root",
    "snowiki.config.resolve_repo_asset_path",
    "snowiki.storage.zones.relative_to_root",
    "snowiki.storage.zones.relative_to_root_or_posix",
)


def test_path_contract_is_scoped_to_snowiki_runtime_code_for_phase_2() -> None:
    assert SNOWIKI_ROOT.exists()
    assert TEMPORARY_EXEMPT_SURFACES == (
        "tests/**",
        "scripts/**",
        "skill/**",
        "vault-template/**",
    )


def test_runtime_benchmark_modules_use_approved_repo_asset_helpers() -> None:
    target_files = (
        ROOT / "snowiki/bench/corpus.py",
        ROOT / "snowiki/bench/baselines.py",
        ROOT / "snowiki/bench/phase1_latency.py",
        ROOT / "snowiki/bench/phase1_correctness.py",
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


def test_snowiki_scope_does_not_add_new_ad_hoc_repo_root_or_cwd_coupling() -> None:
    python_files = sorted(SNOWIKI_ROOT.rglob("*.py"))

    for path in python_files:
        content = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_REPO_ROOT_PATTERNS:
            assert pattern not in content, (
                f"{path.relative_to(ROOT)} contains {pattern}"
            )


def test_approved_helper_surface_is_defined_in_config_and_storage_modules() -> None:
    config_content = (ROOT / "snowiki/config.py").read_text(encoding="utf-8")
    zones_content = (ROOT / "snowiki/storage/zones.py").read_text(encoding="utf-8")

    assert "def get_repo_root() -> Path:" in config_content
    assert (
        "def resolve_repo_asset_path(relative_path: str | Path) -> Path:"
        in config_content
    )
    assert "def relative_to_root(root: Path, path: Path) -> str:" in zones_content
    assert (
        "def relative_to_root_or_posix(root: Path, path: Path) -> str:" in zones_content
    )
    assert EXPECTED_HELPERS == (
        "snowiki.config.get_repo_root",
        "snowiki.config.resolve_repo_asset_path",
        "snowiki.storage.zones.relative_to_root",
        "snowiki.storage.zones.relative_to_root_or_posix",
    )
