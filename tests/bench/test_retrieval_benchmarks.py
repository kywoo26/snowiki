from __future__ import annotations

import importlib.util
import sys
from importlib import import_module
from pathlib import Path

from snowiki.search.indexer import SearchDocument, SearchHit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_BASELINES = import_module("snowiki.bench.baselines")
_PRESETS = import_module("snowiki.bench.presets")

THIS_DIR = ROOT / "tests" / "retrieval"
CONFTST_PATH = THIS_DIR / "conftest.py"
SPEC = importlib.util.spec_from_file_location("retrieval_conftest", CONFTST_PATH)
assert SPEC is not None and SPEC.loader is not None
retrieval_fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retrieval_fixtures)


def test_run_baseline_comparison_emits_phase1_retrieval_metrics(monkeypatch) -> None:
    search = retrieval_fixtures.load_search_api()
    records = retrieval_fixtures.normalized_records()
    pages = retrieval_fixtures.compiled_pages()
    lexical_index = search.build_lexical_index(records)
    wiki_index = search.build_wiki_index(pages)
    corpus = _BASELINES.CorpusBundle(
        records=records,
        pages=pages,
        raw_index=lexical_index.index,
        blended_index=search.build_blended_index(
            lexical_index.documents,
            wiki_index.documents,
        ),
    )

    monkeypatch.setattr(_BASELINES, "_build_corpus", lambda root: corpus)

    report = _BASELINES.run_baseline_comparison(
        ROOT,
        _PRESETS.get_preset("full"),
        semantic_slots=_BASELINES.SemanticSlotsConfig(enabled=False),
    )

    assert list(report["baselines"]) == ["lexical", "bm25s", "bm25s_kiwi"]
    assert report["corpus"]["queries_evaluated"] == 60

    for baseline_name, payload in report["baselines"].items():
        quality = payload["quality"]
        assert quality["overall"]["queries_evaluated"] == 60
        assert set(quality["slices"]["group"]) == {"ko", "en", "mixed"}
        assert set(quality["slices"]["kind"]) == {
            "known-item",
            "topical",
            "temporal",
        }
        assert {entry["gate"] for entry in quality["thresholds"]} >= {
            "overall",
            "kind:known-item",
            "kind:topical",
            "kind:temporal",
        }
        assert quality["overall"]["top_k"] == 5
        assert payload["name"] == baseline_name


def test_ranked_fixture_ids_deduplicate_mapped_hits_before_scoring() -> None:
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

    ranked_ids = _BASELINES._ranked_fixture_ids(
        hits,
        ["fixture-a", "fixture-b"],
        hit_lookup={
            "record-a": "fixture-a",
            "compiled/a.md": "fixture-a",
            "record-b": "fixture-b",
        },
    )

    assert ranked_ids == ["fixture-a", "fixture-b"]
    assert _BASELINES.evaluate_sliced_quality(
        {"q1": ranked_ids},
        {"q1": ["fixture-a", "fixture-b"]},
        query_groups={"q1": "en"},
        query_kinds={"q1": "known-item"},
        top_k=5,
    ).overall.ndcg_at_k == 1.0
