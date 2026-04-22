from __future__ import annotations

import json
from pathlib import Path

import pytest

from snowiki.bench import baselines, corpus
from snowiki.search.workspace import load_normalized_records


def test_seed_canonical_benchmark_root_uses_full_canonical_fixture_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingested: list[tuple[Path, str, Path]] = []
    rebuilt: list[Path] = []

    def fake_ingest(path: Path, *, source: str, root: Path) -> dict[str, object]:
        ingested.append((path, source, root))
        return {"path": path.as_posix(), "source": source, "root": root.as_posix()}

    def fake_rebuild(root: Path) -> dict[str, object]:
        rebuilt.append(root)
        return {"root": root.as_posix()}

    monkeypatch.setattr(corpus, "run_ingest", fake_ingest)
    monkeypatch.setattr(corpus, "run_rebuild", fake_rebuild)

    seeded = corpus.seed_canonical_benchmark_root(tmp_path)

    assert [item["fixture_id"] for item in seeded] == list(
        corpus.CANONICAL_BENCHMARK_FIXTURE_PATHS
    )
    assert len(ingested) == len(corpus.CANONICAL_BENCHMARK_FIXTURE_PATHS)
    assert all(root == tmp_path for _, _, root in ingested)
    assert {source for _, source, _ in ingested} == {"claude", "opencode"}
    assert rebuilt == [tmp_path]


def test_load_corpus_from_manifest_ingests_documents_correctly(tmp_path: Path) -> None:
    manifest = corpus.BenchmarkCorpusManifest(
        tier="official_suite",
        documents=[
            {
                "id": "public-anchor-doc-1",
                "content": "Aurora benchmark note about lexical retrieval behavior.",
                "metadata": {
                    "title": "Aurora retrieval note",
                    "summary": "Covers lexical benchmark behavior.",
                    "recorded_at": "2026-01-02T00:00:00Z",
                },
            },
            {
                "id": "public-anchor-doc-2",
                "content": "Second manifest-backed corpus entry with BM25 context.",
                "metadata": {"title": "BM25 corpus note"},
            },
        ],
    )

    seeded = corpus.load_corpus_from_manifest(manifest, tmp_path)
    records = load_normalized_records(tmp_path)
    compiled_pages = list((tmp_path / "compiled").rglob("*.md"))

    assert [item["fixture_id"] for item in seeded] == [
        "public-anchor-doc-1",
        "public-anchor-doc-2",
    ]
    assert {item["source"] for item in seeded} == {"benchmark_manifest_official_suite"}
    assert {record["id"] for record in records} >= {
        "public-anchor-doc-1",
        "public-anchor-doc-2",
    }
    first_record = next(
        record for record in records if record["id"] == "public-anchor-doc-1"
    )
    assert first_record["record_type"] == "session"
    assert first_record["source_type"] == "benchmark_manifest_official_suite"
    assert first_record["content"] == "Aurora benchmark note about lexical retrieval behavior."
    assert first_record["metadata"]["benchmark_tier"] == "official_suite"
    assert compiled_pages


def test_load_corpus_from_manifest_regression_tier_uses_all_canonical_fixtures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingested: list[tuple[Path, str, Path]] = []
    rebuilt: list[Path] = []

    def fake_ingest(path: Path, *, source: str, root: Path) -> dict[str, object]:
        ingested.append((path, source, root))
        return {"path": path.as_posix(), "source": source, "root": root.as_posix()}

    def fake_rebuild(root: Path) -> dict[str, object]:
        rebuilt.append(root)
        return {"root": root.as_posix()}

    monkeypatch.setattr(corpus, "run_ingest", fake_ingest)
    monkeypatch.setattr(corpus, "run_rebuild", fake_rebuild)

    seeded = corpus.load_corpus_from_manifest(
        corpus.BenchmarkCorpusManifest(
            tier="regression_harness",
            documents=[],
            fixture_paths=corpus.CANONICAL_BENCHMARK_FIXTURE_PATHS,
        ),
        tmp_path,
    )

    assert [item["fixture_id"] for item in seeded] == list(
        corpus.CANONICAL_BENCHMARK_FIXTURE_PATHS
    )
    assert len(seeded) == 12
    assert len(ingested) == len(corpus.CANONICAL_BENCHMARK_FIXTURE_PATHS)
    assert all(root == tmp_path for _, _, root in ingested)
    assert {source for _, source, _ in ingested} == {"claude", "opencode"}
    assert rebuilt == [tmp_path]


def test_generic_document_ids_work_without_fixture_provenance(tmp_path: Path) -> None:
    manifest = corpus.BenchmarkCorpusManifest(
        tier="official_suite",
        documents=[
            {
                "id": "snowiki-shaped-doc-7",
                "content": "nebula retrieval token unique-id-marker",
                "metadata": {"title": "Snowiki shaped note"},
            }
        ],
        queries_path="queries.json",
        judgments_path="judgments.json",
    )
    _ = (tmp_path / "queries.json").write_text(
        json.dumps(
            {
                "queries": [
                    {
                        "id": "q1",
                        "text": "nebula retrieval token",
                        "group": "en",
                        "kind": "known-item",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _ = (tmp_path / "judgments.json").write_text(
        json.dumps(
            {"judgments": {"q1": ["snowiki-shaped-doc-7"]}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _ = corpus.load_corpus_from_manifest(manifest, tmp_path)
    bundle = baselines._build_corpus(tmp_path)
    hits = bundle.raw_index.search("nebula retrieval token", limit=5)
    hit_lookup = baselines._benchmark_hit_lookup(bundle)
    ranked_ids = baselines._ranked_doc_ids(
        hits,
        baselines._load_judgments(tmp_path, manifest.judgments_path)["q1"],
        hit_lookup=hit_lookup,
    )

    assert hit_lookup == {}
    assert ranked_ids[0] == "snowiki-shaped-doc-7"
