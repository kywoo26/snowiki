"""Tests for the lean official benchmark catalog and run-layer contract."""

from __future__ import annotations

import pytest

from snowiki.bench.catalog import (
    OFFICIAL_BENCHMARK_SUITE,
    get_dataset_entry,
    get_official_datasets_by_language,
    is_official,
    official_suite_dataset_ids,
)
from snowiki.bench.run_context import (
    canonicalize_execution_layer,
    get_execution_layer_policy,
)

pytestmark = pytest.mark.bench


def test_official_suite_preserves_canonical_six_dataset_order() -> None:
    assert official_suite_dataset_ids() == (
        "ms_marco_passage",
        "trec_dl_2020_passage",
        "miracl_ko",
        "miracl_en",
        "beir_nq",
        "beir_scifact",
    )
    assert tuple(entry.dataset_id for entry in OFFICIAL_BENCHMARK_SUITE) == (
        "ms_marco_passage",
        "trec_dl_2020_passage",
        "miracl_ko",
        "miracl_en",
        "beir_nq",
        "beir_scifact",
    )


def test_official_catalog_entries_collapse_to_official_suite_authority() -> None:
    for entry in OFFICIAL_BENCHMARK_SUITE:
        assert entry.authority_class == "official_suite"
        assert is_official(entry.dataset_id)


def test_catalog_entry_lookup_and_language_filters() -> None:
    assert get_dataset_entry("unsupported_dataset") is None
    assert get_dataset_entry("legacy_dataset") is None

    ms_marco = get_dataset_entry("ms_marco_passage")
    assert ms_marco is not None
    assert ms_marco.name == "MS MARCO Passage Ranking"

    assert tuple(
        entry.dataset_id for entry in get_official_datasets_by_language("ko")
    ) == ("miracl_ko",)
    assert tuple(
        entry.dataset_id for entry in get_official_datasets_by_language("multilingual")
    ) == ()


def test_execution_layers_preserve_official_sample_contracts() -> None:
    quick = get_execution_layer_policy("pr_official_quick")
    scheduled = get_execution_layer_policy("scheduled_official_standard")
    release = get_execution_layer_policy("release_proof")

    assert quick.sample_mode == "quick"
    assert quick.sample_size == 150
    assert quick.blocking is True

    assert scheduled.sample_mode == "standard"
    assert scheduled.sample_size == 500
    assert scheduled.blocking is False

    assert release.sample_mode == "full"
    assert release.sample_size is None
    assert release.enabled_by_default is False


def test_execution_layer_alias_normalizes_legacy_scheduled_name() -> None:
    assert (
        canonicalize_execution_layer("scheduled_official_broad")
        == "scheduled_official_standard"
    )
