from __future__ import annotations

import importlib.util
from importlib import import_module
from pathlib import Path
from typing import cast

import pytest

pytestmark = pytest.mark.integration


def _load_benchmark_modules():
    baselines = import_module("snowiki.bench.baselines")
    models = import_module("snowiki.bench.models")
    presets = import_module("snowiki.bench.presets")
    return baselines, models, presets


def _load_retrieval_fixtures():
    conftest_path = Path(__file__).resolve().parent.parent / "retrieval" / "conftest.py"
    spec = importlib.util.spec_from_file_location("retrieval_conftest", conftest_path)
    assert spec is not None and spec.loader is not None
    retrieval_fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retrieval_fixtures)
    return retrieval_fixtures


def test_run_baseline_comparison_emits_phase1_retrieval_metrics(
    monkeypatch, benchmarks_dir: Path
) -> None:
    repo_root = benchmarks_dir.parent
    baselines, models, presets = _load_benchmark_modules()
    retrieval_fixtures = _load_retrieval_fixtures()

    search = retrieval_fixtures.load_search_api()
    records = retrieval_fixtures.normalized_records()
    pages = retrieval_fixtures.compiled_pages()
    lexical_index = search.build_lexical_index(records)
    wiki_index = search.build_wiki_index(pages)
    corpus = baselines.CorpusBundle(
        records=tuple(models.validate_record_dict(item) for item in records),
        pages=tuple(
            models.validate_page_dict(
                {
                    "id": page["id"],
                    "path": page["path"],
                    "title": page["title"],
                    "summary": page.get("summary"),
                    "body": page["body"],
                    "updated_at": page.get("updated_at"),
                }
            )
            for page in pages
        ),
        raw_index=lexical_index.index,
        blended_index=search.build_blended_index(
            lexical_index.documents,
            wiki_index.documents,
        ),
    )

    monkeypatch.setattr(baselines, "_build_corpus", lambda root: corpus)

    report = baselines.run_baseline_comparison(
        repo_root,
        presets.get_preset("full"),
    )
    legacy = report.to_legacy_dict()
    legacy_baselines = cast(dict[str, object], legacy["baselines"])

    assert list(report.baselines) == [
        "lexical",
        "bm25s",
        "bm25s_kiwi_nouns",
        "bm25s_kiwi_full",
    ]
    assert report.corpus.queries_evaluated == 60
    assert "semantic_slots" not in legacy
    assert "token_reduction" not in legacy

    for baseline_name, payload in report.baselines.items():
        quality = payload.quality
        legacy_payload = cast(dict[str, object], legacy_baselines[baseline_name])
        legacy_quality = cast(dict[str, object], legacy_payload["quality"])
        legacy_overall = cast(dict[str, object], legacy_quality["overall"])
        assert quality.overall.queries_evaluated == 60
        assert set(quality.slices.group) == {"ko", "en", "mixed"}
        assert set(quality.slices.kind) == {
            "known-item",
            "topical",
            "temporal",
        }
        assert {entry.gate for entry in quality.thresholds} >= {
            "overall",
            "kind:known-item",
            "kind:topical",
            "kind:temporal",
        }
        assert quality.overall.top_k == 5
        assert payload.name == baseline_name
        assert payload.latency.mean_ms >= payload.latency.min_ms
        assert legacy_overall["queries_evaluated"] == 60
        assert "semantic_slots" not in payload.to_legacy_dict()
        assert "token_usage" not in payload.to_legacy_dict()


def test_loaders_fail_fast_on_malformed_top_level_fixture_shapes(
    monkeypatch, benchmarks_dir: Path
) -> None:
    repo_root = benchmarks_dir.parent
    baselines, _, _ = _load_benchmark_modules()
    monkeypatch.setattr(baselines, "_load_json", lambda path: {"queries": {"bad": []}})

    with pytest.raises(ValueError, match="queries"):
        baselines._load_queries(repo_root)

    monkeypatch.setattr(baselines, "_load_json", lambda path: {"judgments": "bad"})

    with pytest.raises(ValueError, match="judgments"):
        baselines._load_judgments(repo_root)


def test_ranked_fixture_ids_deduplicate_mapped_hits_before_scoring(
    repo_root: Path,
) -> None:
    baselines, _, _ = _load_benchmark_modules()
    from snowiki.search.indexer import SearchDocument, SearchHit

    hits = [
        SearchHit(
            document=SearchDocument(
                id="record-a",
                path="normalized/a.json",
                kind="session",
                title="A record",
                content="first hit",
            ),
            score=3.0,
            matched_terms=(),
        ),
        SearchHit(
            document=SearchDocument(
                id="compiled/a.md",
                path="compiled/a.md",
                kind="page",
                title="A page",
                content="duplicate fixture hit",
            ),
            score=2.0,
            matched_terms=(),
        ),
        SearchHit(
            document=SearchDocument(
                id="record-b",
                path="normalized/b.json",
                kind="session",
                title="B record",
                content="second fixture hit",
            ),
            score=1.0,
            matched_terms=(),
        ),
    ]

    ranked_ids = baselines._ranked_fixture_ids(
        hits,
        ["fixture-a", "fixture-b"],
        hit_lookup={
            "record-a": "fixture-a",
            "compiled/a.md": "fixture-a",
            "record-b": "fixture-b",
        },
    )

    assert ranked_ids == ["fixture-a", "fixture-b"]
    assert (
        baselines.evaluate_sliced_quality(
            {"q1": ranked_ids},
            {"q1": ["fixture-a", "fixture-b"]},
            query_groups={"q1": "en"},
            query_kinds={"q1": "known-item"},
            top_k=5,
        ).overall.ndcg_at_k
        == 1.0
    )
