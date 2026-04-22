from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import cast

import pytest

from snowiki.bench.anchors.english import (
    BEIR_NFCORPUS_METADATA,
    BEIR_SCIFACT_METADATA,
    load_beir_nfcorpus_sample,
    load_beir_scifact_sample,
)
from snowiki.bench.anchors.korean import (
    MIRACL_KO_METADATA,
    load_miracl_ko_sample,
)
from snowiki.bench.anchors.snowiki_shaped import (
    LLM_GENERATED_QUOTA,
    SNOWIKI_SHAPED_METADATA,
    get_coverage_quotas,
    load_snowiki_shaped_suite,
)
from snowiki.bench.corpus import BenchmarkCorpusManifest, load_corpus_from_manifest
from snowiki.bench.report import generate_report, render_report_text


def _has_hangul(text: str) -> bool:
    return any("가" <= character <= "힣" for character in text)


def _has_ascii_letters(text: str) -> bool:
    return any(character.isascii() and character.isalpha() for character in text)


def _anchor_report(
    tmp_path: Path, *, dataset: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[BenchmarkCorpusManifest, dict[str, object]]:
    loaders = {
        "miracl_ko": load_miracl_ko_sample,
        "beir_scifact": load_beir_scifact_sample,
        "beir_nfcorpus": load_beir_nfcorpus_sample,
        "snowiki_shaped": load_snowiki_shaped_suite,
    }
    loader = loaders[dataset]
    manifest = loader(size=6)
    report_module = import_module("snowiki.bench.report")
    monkeypatch.setattr(
        report_module,
        "run_phase1_latency_evaluation",
        lambda root, preset, **kwargs: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 12.0},
            },
            "corpus": {
                "dataset": dataset,
                "tier": manifest.tier,
                "queries_available": len(manifest.queries or []),
                "queries_evaluated": len(manifest.queries or []),
            },
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": preset.top_k,
                "top_ks": list(preset.top_ks),
                "dataset_mode": "manifest",
                "sampling_policy": {
                    "mode": "exhaustive",
                    "population_query_count": len(manifest.queries or []),
                    "sampled_query_count": len(manifest.queries or []),
                    "sampled": False,
                },
            },
        },
    )
    _ = load_corpus_from_manifest(manifest, tmp_path)
    report = generate_report(
        tmp_path,
        preset_name="retrieval",
        manifest=manifest,
        dataset_name=dataset,
        isolated_root=True,
    )
    return manifest, report


def test_miracl_korean_manifest_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, report = _anchor_report(tmp_path, dataset="miracl_ko", monkeypatch=monkeypatch)
    dataset_payload = cast(dict[str, object], report["dataset"])

    assert manifest.tier == "public_anchor"
    assert manifest.dataset_name == MIRACL_KO_METADATA["name"]
    assert len(manifest.documents) == 6
    assert len(manifest.queries or []) == 6
    assert len(manifest.judgments or {}) == 6
    assert dataset_payload["tier"] == "public_anchor"


def test_anchor_provenance_metadata_is_correct() -> None:
    miracl_manifest = load_miracl_ko_sample(size=4)

    miracl_provenance = miracl_manifest.corpus_assets[0].provenance

    assert miracl_manifest.dataset_metadata is not None
    assert miracl_manifest.dataset_metadata["license"] == "Apache-2.0"
    assert (
        miracl_manifest.dataset_metadata["source_url"]
        == MIRACL_KO_METADATA["source_url"]
    )
    assert miracl_provenance.family_dedupe_key == "public-anchor:miracl_ko:ko"
    assert miracl_provenance.authority_tier == "public_anchor"


def test_beir_scifact_manifest_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, report = _anchor_report(
        tmp_path,
        dataset="beir_scifact",
        monkeypatch=monkeypatch,
    )
    dataset_payload = cast(dict[str, object], report["dataset"])

    assert manifest.tier == "public_anchor"
    assert manifest.dataset_name == BEIR_SCIFACT_METADATA["name"]
    assert len(manifest.documents) == 6
    assert len(manifest.queries or []) == 6
    assert len(manifest.judgments or {}) == 6
    assert dataset_payload["name"] == BEIR_SCIFACT_METADATA["name"]


def test_beir_nfcorpus_manifest_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, report = _anchor_report(
        tmp_path,
        dataset="beir_nfcorpus",
        monkeypatch=monkeypatch,
    )
    dataset_payload = cast(dict[str, object], report["dataset"])

    assert manifest.tier == "public_anchor"
    assert manifest.dataset_name == BEIR_NFCORPUS_METADATA["name"]
    assert len(manifest.documents) == 6
    assert len(manifest.queries or []) == 6
    assert len(manifest.judgments or {}) == 6
    assert dataset_payload["tier"] == "public_anchor"


def test_english_anchor_provenance_metadata_is_correct() -> None:
    scifact_manifest = load_beir_scifact_sample(size=4)
    nfcorpus_manifest = load_beir_nfcorpus_sample(size=4)

    scifact_provenance = scifact_manifest.corpus_assets[0].provenance
    nfcorpus_provenance = nfcorpus_manifest.corpus_assets[0].provenance

    assert scifact_manifest.dataset_metadata is not None
    assert scifact_manifest.dataset_metadata["license"] == "CC-BY-4.0"
    assert (
        scifact_manifest.dataset_metadata["source_url"]
        == BEIR_SCIFACT_METADATA["source_url"]
    )
    assert scifact_provenance.source_class == "public_dataset"
    assert scifact_provenance.family_dedupe_key == "public-anchor:beir_scifact:en"
    assert nfcorpus_manifest.dataset_metadata is not None
    assert nfcorpus_manifest.dataset_metadata["license"] == "MIT"
    assert (
        nfcorpus_manifest.dataset_metadata["citation"]
        == BEIR_NFCORPUS_METADATA["citation"]
    )
    assert nfcorpus_provenance.source_class == "public_dataset"
    assert nfcorpus_provenance.family_dedupe_key == "public-anchor:beir_nfcorpus:en"


def test_anchor_documents_have_korean_content() -> None:
    miracl_manifest = load_miracl_ko_sample(size=4)

    assert all(
        _has_hangul(str(document["content"])) for document in miracl_manifest.documents
    )
    assert all(
        _has_hangul(
            str(cast(dict[str, object], document.get("metadata", {})).get("title", ""))
        )
        for document in miracl_manifest.documents
    )


def test_english_anchor_documents_have_english_content() -> None:
    scifact_manifest = load_beir_scifact_sample(size=4)
    nfcorpus_manifest = load_beir_nfcorpus_sample(size=4)

    assert all(
        _has_ascii_letters(str(document["content"]))
        for document in scifact_manifest.documents
    )
    assert all(
        _has_ascii_letters(str(document["content"]))
        for document in nfcorpus_manifest.documents
    )
    assert all(
        cast(dict[str, object], document.get("metadata", {})).get("language") == "en"
        for document in scifact_manifest.documents
    )
    assert all(
        _has_ascii_letters(
            str(cast(dict[str, object], document.get("metadata", {})).get("title", ""))
        )
        for document in nfcorpus_manifest.documents
    )


def test_anchor_report_output_includes_dataset_name_and_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, report = _anchor_report(
        tmp_path,
        dataset="miracl_ko",
        monkeypatch=monkeypatch,
    )

    rendered = render_report_text(report)

    assert manifest.dataset_name is not None
    assert manifest.dataset_name in rendered
    assert "tier=public_anchor" in rendered
    assert "Dataset provenance:" in rendered
    assert "Latency sampling:" in rendered
    assert "Performance:" in rendered


def test_english_anchor_report_output_includes_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, report = _anchor_report(
        tmp_path,
        dataset="beir_scifact",
        monkeypatch=monkeypatch,
    )

    rendered = render_report_text(report)

    assert manifest.dataset_name is not None
    assert manifest.dataset_name in rendered
    assert "Dataset language: en" in rendered
    assert "Dataset provenance:" in rendered


def test_snowiki_shaped_manifest_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_module = import_module("snowiki.bench.report")
    manifest = load_snowiki_shaped_suite(size=20)
    monkeypatch.setattr(
        report_module,
        "run_phase1_latency_evaluation",
        lambda root, preset, **kwargs: {
            "performance": {
                "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
                "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
                "query": {"p50_ms": 6.0, "p95_ms": 12.0},
            },
            "corpus": {
                "dataset": "snowiki_shaped",
                "tier": manifest.tier,
                "queries_available": len(manifest.queries or []),
                "queries_evaluated": len(manifest.queries or []),
            },
            "protocol": {
                "isolated_root": True,
                "warmups": 1,
                "repetitions": 5,
                "query_mode": "lexical",
                "top_k": preset.top_k,
                "top_ks": list(preset.top_ks),
                "dataset_mode": "manifest",
                "sampling_policy": {
                    "mode": "exhaustive",
                    "population_query_count": len(manifest.queries or []),
                    "sampled_query_count": len(manifest.queries or []),
                    "sampled": False,
                },
            },
        },
    )
    _ = load_corpus_from_manifest(manifest, tmp_path)
    report = generate_report(
        tmp_path,
        preset_name="full",
        manifest=manifest,
        dataset_name="snowiki_shaped",
        isolated_root=True,
    )
    dataset_payload = cast(dict[str, object], report["dataset"])

    assert manifest.tier == "snowiki_shaped"
    assert manifest.dataset_name == SNOWIKI_SHAPED_METADATA["name"]
    assert len(manifest.documents) == 20
    assert len(manifest.queries or []) == 20
    assert dataset_payload["tier"] == "snowiki_shaped"
    assert dataset_payload["name"] == SNOWIKI_SHAPED_METADATA["name"]


def test_snowiki_shaped_coverage_quotas_sum_to_one_hundred() -> None:
    quotas = get_coverage_quotas()

    assert quotas == {
        "mixed_language": 30.0,
        "code_doc": 25.0,
        "topical": 30.0,
        "temporal": 10.0,
        "no_answer": 5.0,
    }
    assert sum(quotas.values()) == 100.0


def test_snowiki_shaped_manifest_contains_mixed_language_content() -> None:
    manifest = load_snowiki_shaped_suite(size=20)

    mixed_documents = [
        document
        for document in manifest.documents
        if cast(dict[str, object], document.get("metadata", {})).get("coverage_bucket")
        == "mixed_language"
    ]

    assert mixed_documents
    assert all(_has_hangul(str(document["content"])) for document in mixed_documents)
    assert all(
        _has_ascii_letters(str(document["content"])) for document in mixed_documents
    )


def test_snowiki_shaped_manifest_contains_no_answer_queries() -> None:
    manifest = load_snowiki_shaped_suite(size=20)
    no_answer_queries = [
        query for query in manifest.queries or [] if bool(query.get("no_answer"))
    ]

    assert no_answer_queries
    assert all(
        str(query["id"]) not in (manifest.judgments or {})
        for query in no_answer_queries
    )


def test_snowiki_shaped_family_dedupe_keys_are_set() -> None:
    manifest = load_snowiki_shaped_suite(size=20)

    assert (
        manifest.corpus_assets[0].provenance.family_dedupe_key
        == "snowiki-shaped:v1:corpus"
    )
    assert (
        manifest.query_assets[0].provenance.family_dedupe_key
        == "snowiki-shaped:v1:queries"
    )
    assert all(document.get("metadata") for document in manifest.documents)
    assert all(
        str(
            cast(dict[str, object], document.get("metadata", {})).get(
                "family_dedupe_key", ""
            )
        ).startswith("snowiki-shaped:v1:")
        for document in manifest.documents
    )
    assert all(
        str(query.get("family_dedupe_key", "")).startswith("snowiki-shaped:v1:")
        for query in manifest.queries or []
    )


def test_snowiki_shaped_llm_generated_content_is_disabled() -> None:
    manifest = load_snowiki_shaped_suite(size=20)

    assert manifest.dataset_metadata is not None
    assert manifest.dataset_metadata["llm_generated_share_pct"] == LLM_GENERATED_QUOTA
    assert manifest.dataset_metadata["llm_generated_used"] is False
    assert manifest.dataset_metadata["llm_generated_role"] == "auxiliary_only"


def test_snowiki_shaped_manifest_excludes_removed_benchmark_self_reference_terms() -> None:
    manifest = load_snowiki_shaped_suite(size=20)
    rendered = " ".join(
        [
            *(str(document["content"]) for document in manifest.documents),
            *(
                str(cast(dict[str, object], document.get("metadata", {})).get("title", ""))
                for document in manifest.documents
            ),
            *(
                str(cast(dict[str, object], document.get("metadata", {})).get("summary", ""))
                for document in manifest.documents
            ),
            *(str(query.get("text", "")) for query in manifest.queries or []),
        ]
    ).casefold()

    forbidden_terms = (
        "benchmark",
        "retrieval",
        "snowiki",
        "snowiki.bench",
        "load_miracl_ko_sample",
        "evaluation",
        "testing",
    )

    assert all(term not in rendered for term in forbidden_terms)
