from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.config import (
    SNOWIKI_BENCHMARK_DATA_ROOT_ENV_VAR,
    SNOWIKI_ROOT_ENV_VAR,
    get_benchmark_data_root,
)


def test_get_benchmark_data_root_defaults_under_snowiki_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snowiki_root = tmp_path / "snowiki-root"
    monkeypatch.setenv(SNOWIKI_ROOT_ENV_VAR, str(snowiki_root))
    monkeypatch.delenv(SNOWIKI_BENCHMARK_DATA_ROOT_ENV_VAR, raising=False)

    benchmark_root = get_benchmark_data_root()

    assert benchmark_root == (snowiki_root / "benchmarks").resolve()
    assert benchmark_root.is_dir()
    assert not (benchmark_root / "raw").exists()


def test_get_benchmark_data_root_prefers_benchmark_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    benchmark_override = tmp_path / "custom-bench-root"
    monkeypatch.setenv(SNOWIKI_BENCHMARK_DATA_ROOT_ENV_VAR, str(benchmark_override))

    benchmark_root = get_benchmark_data_root()

    assert benchmark_root == benchmark_override.resolve()
    assert benchmark_root.is_dir()
