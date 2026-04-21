from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import cast

import pytest

from snowiki.bench.anchors.public_cached import (
    PublicAnchorSampleMode,
    load_beir_nfcorpus_cached_manifest,
    load_beir_scifact_cached_manifest,
    load_miracl_ko_cached_manifest,
    load_mr_tydi_ko_cached_manifest,
    resolve_public_anchor_sample_count,
)
from snowiki.bench.corpus import BenchmarkCorpusManifest, load_corpus_from_manifest
from snowiki.bench.datasets import (
    BenchmarkDatasetId,
    get_benchmark_dataset_lock_path,
    get_benchmark_dataset_spec,
)
from snowiki.bench.report import generate_report, render_report_text


def _write_parquet(path: Path, rows: list[dict[str, object]]) -> None:
    pyarrow = import_module("pyarrow")
    pyarrow_parquet = import_module("pyarrow.parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    table_type = pyarrow.Table
    table = cast(object, table_type.from_pylist(rows))
    write_table = cast(Callable[[object, Path], None], pyarrow_parquet.write_table)
    write_table(table, path)


def _write_jsonl_gz(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False))
            stream.write("\n")


def _write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _write_lock(
    *,
    dataset_id: BenchmarkDatasetId,
    data_root: Path,
    source_paths: dict[str, Path],
) -> None:
    spec = get_benchmark_dataset_spec(dataset_id)
    lock_path = get_benchmark_dataset_lock_path(dataset_id, data_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_id": dataset_id,
        "fetched_at": "2026-04-20T00:00:00Z",
        "language": spec.language,
        "tier": spec.tier,
        "source_url": spec.source_url,
        "citation": spec.citation,
        "license": spec.license,
        "sources": [
            {
                "label": source.label,
                "name": source.name,
                "repo_id": source.repo_id,
                "repo_type": source.repo_type,
                "requested_revision": source.default_revision,
                "resolved_snapshot_path": source_paths[source.label].resolve().as_posix(),
                "allow_patterns": list(source.allow_patterns),
            }
            for source in spec.sources
        ],
    }
    _ = lock_path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_miracl_cache(tmp_path: Path) -> Path:
    data_root = tmp_path / "benchmark-data"
    snapshot_path = data_root / "hf" / "miracl-ko" / "snapshots" / "fixture"
    _write_parquet(
        snapshot_path / "ko-corpus" / "corpus-00000-of-00001.parquet",
        [
            {
                "_id": "miracl-doc-1",
                "title": "서울 도서관",
                "text": "서울 도서관 운영 안내 [[분류:도서관]] [[서울시립도서관|도서관 안내]] {{lang|ko|서울}}",
            },
            {"_id": "miracl-doc-2", "title": "부산 영화제", "text": "부산 국제영화제 상영 정보"},
            {"_id": "miracl-doc-3", "title": "제주 올레길", "text": "제주 올레길 7코스 설명"},
        ],
    )
    _write_parquet(
        snapshot_path / "ko-queries" / "queries-00000-of-00001.parquet",
        [
            {"_id": "miracl-q-1", "text": "서울 도서관 운영 시간이 궁금해"},
            {"_id": "miracl-q-2", "text": "부산 영화제 상영 정보 알려줘"},
            {"_id": "miracl-q-3", "text": "제주 올레길 7코스 설명을 찾아줘"},
        ],
    )
    _write_parquet(
        snapshot_path / "ko-qrels" / "qrels-00000-of-00001.parquet",
        [
            {"query-id": "miracl-q-1", "corpus-id": "miracl-doc-1", "score": 1},
            {"query-id": "miracl-q-2", "corpus-id": "miracl-doc-2", "score": 1},
            {"query-id": "miracl-q-3", "corpus-id": "miracl-doc-3", "score": 1},
        ],
    )
    _write_lock(
        dataset_id="miracl_ko",
        data_root=data_root,
        source_paths={"dataset": snapshot_path},
    )
    return data_root


def _seed_mr_tydi_cache(tmp_path: Path) -> Path:
    data_root = tmp_path / "benchmark-data"
    query_snapshot = data_root / "hf" / "mr-tydi" / "snapshots" / "fixture"
    corpus_snapshot = data_root / "hf" / "mr-tydi-corpus" / "snapshots" / "fixture"
    topics_path = query_snapshot / "mrtydi-v1.1-korean/ir-format-data/topics.dev.txt"
    topics_path.parent.mkdir(parents=True, exist_ok=True)
    _ = topics_path.write_text(
        "0\t월드컵 개최 국가는 몇 개인가?\n"
        "2\t합성생물학의 다른 연구 방식은?\n"
        "4\t룩셈부르크의 수도는 어디인가?\n",
        encoding="utf-8",
    )
    qrels_path = query_snapshot / "mrtydi-v1.1-korean/ir-format-data/qrels.dev.txt"
    _ = qrels_path.write_text(
        "0 Q0 mr-doc-1#0 1\n2 Q0 mr-doc-2#0 1\n4 Q0 mr-doc-3#0 1\n",
        encoding="utf-8",
    )
    _write_jsonl_gz(
        corpus_snapshot / "mrtydi-v1.1-korean/corpus.jsonl.gz",
        [
            {"docid": "mr-doc-1#0", "title": "월드컵", "text": "월드컵 개최 국가 수 안내"},
            {"docid": "mr-doc-2#0", "title": "합성생물학", "text": "합성생물학 연구 방식 설명"},
            {"docid": "mr-doc-3#0", "title": "룩셈부르크", "text": "룩셈부르크 수도 안내"},
        ],
    )
    _write_lock(
        dataset_id="mr_tydi_ko",
        data_root=data_root,
        source_paths={"queries_qrels": query_snapshot, "corpus": corpus_snapshot},
    )
    return data_root


def _seed_beir_scifact_cache(tmp_path: Path) -> Path:
    data_root = tmp_path / "benchmark-data"
    corpus_snapshot = data_root / "hf" / "beir-scifact" / "snapshots" / "fixture"
    qrels_snapshot = data_root / "hf" / "beir-scifact-qrels" / "snapshots" / "fixture"
    _write_parquet(
        corpus_snapshot / "corpus" / "corpus-00000-of-00001.parquet",
        [
            {
                "_id": "31715818",
                "title": "Vitamin D randomized controlled trial evidence summary with a very long imported public title that should be bounded safely before Snowiki summary pages are generated downstream",
                "text": "Vitamin D evidence summary",
            },
            {"_id": "14717500", "title": "Blue light", "text": "Blue light sleep timing evidence"},
            {"_id": "13734012", "title": "Coffee", "text": "Coffee cardiovascular review"},
        ],
    )
    _write_parquet(
        corpus_snapshot / "queries" / "queries-00000-of-00001.parquet",
        [
            {"_id": "1", "text": "Vitamin D supplementation helps bone health"},
            {"_id": "3", "text": "Blue light exposure affects sleep timing"},
            {"_id": "5", "text": "Coffee consumption changes cardiovascular risk"},
        ],
    )
    _write_tsv(
        qrels_snapshot / "test.tsv",
        ["query-id", "corpus-id", "score"],
        [
            {"query-id": "1", "corpus-id": "31715818", "score": 1},
            {"query-id": "3", "corpus-id": "14717500", "score": 1},
            {"query-id": "5", "corpus-id": "13734012", "score": 1},
        ],
    )
    _write_lock(
        dataset_id="beir_scifact",
        data_root=data_root,
        source_paths={"corpus_queries": corpus_snapshot, "qrels": qrels_snapshot},
    )
    return data_root


def _seed_beir_nfcorpus_cache(tmp_path: Path) -> Path:
    data_root = tmp_path / "benchmark-data"
    corpus_snapshot = data_root / "hf" / "beir-nfcorpus" / "snapshots" / "fixture"
    qrels_snapshot = data_root / "hf" / "beir-nfcorpus-qrels" / "snapshots" / "fixture"
    _write_parquet(
        corpus_snapshot / "corpus" / "corpus-00000-of-00001.parquet",
        [
            {"_id": "MED-2427", "title": "Allergy travel", "text": "Allergy travel symptom checklist"},
            {"_id": "MED-10", "title": "Telehealth", "text": "Rural telehealth dermatology guide"},
            {"_id": "MED-2429", "title": "Sleep apnea", "text": "Sleep apnea equipment care"},
        ],
    )
    _write_parquet(
        corpus_snapshot / "queries" / "queries-00000-of-00001.parquet",
        [
            {"_id": "PLAIN-2", "text": "seasonal allergy travel planning"},
            {"_id": "PLAIN-4", "text": "rural telehealth dermatology"},
            {"_id": "PLAIN-6", "text": "sleep apnea equipment care"},
        ],
    )
    _write_tsv(
        qrels_snapshot / "test.tsv",
        ["query-id", "corpus-id", "score"],
        [
            {"query-id": "PLAIN-2", "corpus-id": "MED-2427", "score": 2},
            {"query-id": "PLAIN-4", "corpus-id": "MED-10", "score": 2},
            {"query-id": "PLAIN-6", "corpus-id": "MED-2429", "score": 2},
        ],
    )
    _write_lock(
        dataset_id="beir_nfcorpus",
        data_root=data_root,
        source_paths={"corpus_queries": corpus_snapshot, "qrels": qrels_snapshot},
    )
    return data_root


@pytest.mark.parametrize(
    ("loader", "seed_cache", "dataset_id", "query_ids", "doc_ids", "language"),
    [
        (
            load_miracl_ko_cached_manifest,
            _seed_miracl_cache,
            "miracl_ko",
            ["miracl-q-1", "miracl-q-2"],
            ["miracl-doc-1", "miracl-doc-2"],
            "ko",
        ),
        (
            load_mr_tydi_ko_cached_manifest,
            _seed_mr_tydi_cache,
            "mr_tydi_ko",
            ["0", "2"],
            ["mr-doc-1#0", "mr-doc-2#0"],
            "ko",
        ),
        (
            load_beir_scifact_cached_manifest,
            _seed_beir_scifact_cache,
            "beir_scifact",
            ["1", "3"],
            ["31715818", "14717500"],
            "en",
        ),
        (
            load_beir_nfcorpus_cached_manifest,
            _seed_beir_nfcorpus_cache,
            "beir_nfcorpus",
            ["PLAIN-2", "PLAIN-4"],
            ["MED-2427", "MED-10"],
            "en",
        ),
    ],
)
def test_cached_public_anchor_manifest_uses_real_cached_assets(
    tmp_path: Path,
    loader: Callable[..., BenchmarkCorpusManifest],
    seed_cache: Callable[[Path], Path],
    dataset_id: str,
    query_ids: list[str],
    doc_ids: list[str],
    language: str,
) -> None:
    data_root = seed_cache(tmp_path)
    manifest = loader(size=2, data_root=data_root)

    assert isinstance(manifest, BenchmarkCorpusManifest)
    assert manifest.tier == "public_anchor"
    assert manifest.dataset_id == dataset_id
    assert manifest.dataset_metadata is not None
    assert manifest.dataset_metadata["real_public_assets"] is True
    assert manifest.dataset_metadata["queries_available"] == 3
    assert manifest.dataset_metadata["sample_mode"] == "custom"
    assert manifest.dataset_metadata["sample_size"] == 2
    assert manifest.dataset_metadata["sampling_strategy"] == "explicit_query_count_override"
    assert [str(query["id"]) for query in manifest.queries or []] == query_ids
    assert {str(document["id"]) for document in manifest.documents} == set(doc_ids)
    assert manifest.judgments is not None
    assert list(manifest.judgments) == query_ids
    assert [str(entry["doc_id"]) for entry in manifest.judgments[query_ids[0]]] == [doc_ids[0]]
    assert manifest.corpus_assets[0].provenance.source_class == "public_dataset"
    assert manifest.corpus_assets[0].provenance.collection_method == "cached_public_dataset_manifest_sampling"
    assert manifest.corpus_assets[0].provenance.family_dedupe_key == f"public-anchor:{dataset_id}:{language}"
    assert all(query.get("group") == language for query in manifest.queries or [])
    assert {str(query.get("kind")) for query in manifest.queries or []} == {"known-item", "topical"}


@pytest.mark.parametrize(
    ("query_count", "mode", "explicit_size", "expected"),
    [
        (0, "quick", None, 0),
        (50, "quick", None, 50),
        (250, "quick", None, 200),
        (300, "standard", None, 300),
        (700, "standard", None, 500),
        (700, "full", None, 700),
        (1500, "full", None, 1000),
        (0, "full", 25, 0),
        (700, "quick", 25, 25),
        (10, "full", 25, 10),
    ],
)
def test_resolve_public_anchor_sample_count(
    query_count: int,
    mode: PublicAnchorSampleMode,
    explicit_size: int | None,
    expected: int,
) -> None:
    assert (
        resolve_public_anchor_sample_count(query_count, mode, explicit_size=explicit_size)
        == expected
    )


def test_resolve_public_anchor_sample_count_rejects_non_positive_override() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        _ = resolve_public_anchor_sample_count(10, "standard", explicit_size=0)


def test_cached_public_anchor_manifest_defaults_to_standard_mode(tmp_path: Path) -> None:
    data_root = _seed_beir_scifact_cache(tmp_path)

    manifest = load_beir_scifact_cached_manifest(data_root=data_root)

    assert manifest.dataset_metadata is not None
    assert manifest.dataset_metadata["queries_available"] == 3
    assert manifest.dataset_metadata["sample_mode"] == "standard"
    assert manifest.dataset_metadata["sample_size"] == 3
    assert manifest.dataset_metadata["sampling_strategy"] == "deterministic_qrels_bounded_mode"


@pytest.mark.parametrize("sample_mode", ["quick", "full"])
def test_cached_public_anchor_manifest_preserves_requested_sample_mode(
    tmp_path: Path,
    sample_mode: PublicAnchorSampleMode,
) -> None:
    data_root = _seed_beir_nfcorpus_cache(tmp_path)

    manifest = load_beir_nfcorpus_cached_manifest(
        sample_mode=sample_mode,
        data_root=data_root,
    )

    assert manifest.dataset_metadata is not None
    assert manifest.dataset_metadata["queries_available"] == 3
    assert manifest.dataset_metadata["sample_mode"] == sample_mode
    assert manifest.dataset_metadata["sample_size"] == 3
    assert manifest.dataset_metadata["sampling_strategy"] == "deterministic_qrels_bounded_mode"


def test_cached_public_anchor_report_includes_real_dataset_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = _seed_beir_scifact_cache(tmp_path)
    manifest = load_beir_scifact_cached_manifest(size=2, data_root=data_root)
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
                "dataset": "beir_scifact",
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
        dataset_name="beir_scifact",
        isolated_root=True,
    )

    rendered = render_report_text(report)
    dataset_payload = cast(dict[str, object], report["dataset"])

    assert dataset_payload["name"] == "BEIR SciFact"
    assert cast(dict[str, object], dataset_payload["metadata"])["synthetic_sample"] is False
    assert "Dataset sample mode:" in rendered
    assert "Dataset provenance:" in rendered
    assert "Dataset language: en" in rendered
    assert "Dataset source: https://huggingface.co/datasets/BeIR/scifact" in rendered


def test_cached_public_anchor_neutralizes_imported_wiki_markup(tmp_path: Path) -> None:
    data_root = _seed_miracl_cache(tmp_path)

    manifest = load_miracl_ko_cached_manifest(size=1, data_root=data_root)

    content = str(manifest.documents[0]["content"])
    summary = str(cast(dict[str, object], manifest.documents[0]["metadata"])["summary"])

    assert "[[" not in content
    assert "]]" not in content
    assert "{{" not in content
    assert "}}" not in content
    assert "분류:" not in content
    assert "도서관 안내" in content
    assert "서울" in content
    assert "[[" not in summary


def test_cached_public_anchor_bounds_long_imported_titles(tmp_path: Path) -> None:
    data_root = _seed_beir_scifact_cache(tmp_path)

    manifest = load_beir_scifact_cached_manifest(size=1, data_root=data_root)

    title = str(cast(dict[str, object], manifest.documents[0]["metadata"])["title"])
    content = str(manifest.documents[0]["content"])

    assert len(title) <= 96
    assert title.endswith("…")
    assert title in content
