"""Guard tests for the lean benchmark contract surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest

from snowiki.bench.contract.policy import (
    REGRESSION_HARNESS_DATASET_ID,
    get_dataset_authority,
    is_regression_harness,
    resolve_policy,
)
from snowiki.bench.runtime.catalog import (
    OFFICIAL_BENCHMARK_SUITE,
    is_official,
    official_suite_dataset_ids,
)
from snowiki.bench.runtime.context import LAYER_POLICIES, ExecutionLayer

pytestmark = pytest.mark.bench

REPO_ROOT = Path(__file__).resolve().parents[3]
OFFICIAL_SIX_DATASET_IDS: tuple[str, ...] = (
    "ms_marco_passage",
    "trec_dl_2020_passage",
    "miracl_ko",
    "miracl_en",
    "beir_nq",
    "beir_scifact",
)
LEAN_EXECUTION_LAYERS: tuple[str, ...] = (
    "pr_official_quick",
    "scheduled_official_standard",
    "release_proof",
)
REMOVED_DATASET_SURFACES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("bench runtime", "src/snowiki/bench", (".py",)),
    ("benchmark CLI", "src/snowiki/cli/commands", (".py",)),
    ("bench tests", "tests/bench", (".py",)),
    ("benchmark integration tests", "tests/integration/cli", (".py",)),
    ("benchmark docs", "benchmarks", (".md",)),
    ("GitHub workflows", ".github/workflows", (".yml", ".yaml")),
)


def _removed_dataset_ids() -> tuple[str, ...]:
    return (
        "snowiki" + "_shaped",
        "hidden_" + "holdout",
        "beir_" + "nfcorpus",
        "mr_tydi_" + "ko",
    )


def _legacy_scheduled_layer_name() -> str:
    return "scheduled_" + "official_" + "broad"


def _iter_surface_files(
    relative_dir: str, allowed_suffixes: tuple[str, ...]
) -> tuple[Path, ...]:
    base_dir = REPO_ROOT / relative_dir
    return tuple(
        sorted(
            path
            for path in base_dir.rglob("*")
            if path.is_file() and path.suffix in allowed_suffixes
        )
    )


def _relative_files_containing_token(
    relative_dir: str, allowed_suffixes: tuple[str, ...], token: str
) -> tuple[str, ...]:
    return tuple(
        str(path.relative_to(REPO_ROOT))
        for path in _iter_surface_files(relative_dir, allowed_suffixes)
        if token in path.read_text(encoding="utf-8")
    )


def _benchmark_contract_docs_text() -> str:
    docs_path = REPO_ROOT / "benchmarks/README.md"
    workflow_paths = sorted((REPO_ROOT / ".github/workflows").glob("benchmark*.yml"))
    text_parts = [docs_path.read_text(encoding="utf-8")]
    text_parts.extend(path.read_text(encoding="utf-8") for path in workflow_paths)
    return "\n".join(text_parts)


def test_official_six_order_is_frozen_in_catalog() -> None:
    assert official_suite_dataset_ids() == OFFICIAL_SIX_DATASET_IDS
    assert tuple(entry.dataset_id for entry in OFFICIAL_BENCHMARK_SUITE) == OFFICIAL_SIX_DATASET_IDS
    assert len(OFFICIAL_BENCHMARK_SUITE) == 6


@pytest.mark.parametrize("dataset_id", OFFICIAL_SIX_DATASET_IDS)
def test_is_official_accepts_every_dataset_in_the_official_six(dataset_id: str) -> None:
    assert is_official(dataset_id)


@pytest.mark.parametrize(
    "dataset_id",
    (REGRESSION_HARNESS_DATASET_ID, *_removed_dataset_ids(), "unknown_dataset"),
)
def test_is_official_rejects_regression_removed_and_unknown_datasets(
    dataset_id: str,
) -> None:
    assert not is_official(dataset_id)


@pytest.mark.parametrize(
    ("dataset_id", "expected_authority"),
    (
        *((dataset_id, "official_suite") for dataset_id in OFFICIAL_SIX_DATASET_IDS),
        (REGRESSION_HARNESS_DATASET_ID, "regression_harness"),
    ),
)
def test_get_dataset_authority_matches_the_lean_contract(
    dataset_id: str, expected_authority: str
) -> None:
    assert get_dataset_authority(dataset_id) == expected_authority


@pytest.mark.parametrize("dataset_id", _removed_dataset_ids())
def test_removed_datasets_have_no_runtime_authority(dataset_id: str) -> None:
    with pytest.raises(ValueError, match="unsupported benchmark dataset"):
        _ = get_dataset_authority(dataset_id)


def test_regression_is_only_a_regression_harness_authority() -> None:
    assert is_regression_harness(REGRESSION_HARNESS_DATASET_ID)
    assert not is_official(REGRESSION_HARNESS_DATASET_ID)

    regression_policy = resolve_policy("pr_official_quick", REGRESSION_HARNESS_DATASET_ID)

    assert regression_policy.authority == "regression_harness"
    assert regression_policy.dataset_id == REGRESSION_HARNESS_DATASET_ID


def test_execution_layers_are_locked_to_the_three_lean_layers() -> None:
    assert tuple(get_args(ExecutionLayer)) == LEAN_EXECUTION_LAYERS
    assert tuple(LAYER_POLICIES) == LEAN_EXECUTION_LAYERS
    assert len(LAYER_POLICIES) == 3


@pytest.mark.parametrize(
    ("surface_name", "relative_dir", "allowed_suffixes"),
    REMOVED_DATASET_SURFACES,
)
@pytest.mark.parametrize("token", _removed_dataset_ids())
def test_removed_dataset_tokens_do_not_reappear_on_guarded_surfaces(
    surface_name: str,
    relative_dir: str,
    allowed_suffixes: tuple[str, ...],
    token: str,
) -> None:
    matching_files = _relative_files_containing_token(relative_dir, allowed_suffixes, token)
    assert not matching_files, (
        f"removed dataset token {token!r} reappeared in {surface_name}: {matching_files}"
    )


@pytest.mark.parametrize(
    ("surface_name", "relative_dir", "allowed_suffixes"),
    (
        ("benchmark docs", "benchmarks", (".md",)),
        ("GitHub workflows", ".github/workflows", (".yml", ".yaml")),
    ),
)
def test_docs_and_workflows_do_not_reintroduce_the_legacy_scheduled_layer_name(
    surface_name: str, relative_dir: str, allowed_suffixes: tuple[str, ...]
) -> None:
    matching_files = _relative_files_containing_token(
        relative_dir,
        allowed_suffixes,
        _legacy_scheduled_layer_name(),
    )
    assert not matching_files, (
        "legacy layer alias leaked back into "
        + f"{surface_name}: {matching_files}"
    )


def test_benchmark_docs_and_workflows_match_the_lean_runtime_contract() -> None:
    contract_text = _benchmark_contract_docs_text()

    assert "official_suite" in contract_text
    assert "regression_harness" in contract_text
    assert REGRESSION_HARNESS_DATASET_ID in contract_text

    for dataset_id in OFFICIAL_SIX_DATASET_IDS:
        assert dataset_id in contract_text

    for execution_layer in LEAN_EXECUTION_LAYERS:
        assert execution_layer in contract_text
