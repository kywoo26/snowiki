from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest


def test_baselines_parsing_helpers_cover_error_and_path_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    qrels = import_module("snowiki.bench.evaluation.qrels")

    absolute_path = tmp_path / "absolute.json"
    absolute_path.write_text("{}", encoding="utf-8")
    resolved_path, label = qrels._resolve_benchmark_asset_path(
        tmp_path,
        absolute_path,
        default_relative_path="ignored.json",
    )
    assert resolved_path == absolute_path
    assert label == absolute_path.as_posix()

    root_relative = tmp_path / "queries.json"
    root_relative.write_text("{}", encoding="utf-8")
    resolved_path, label = qrels._resolve_benchmark_asset_path(
        tmp_path,
        "queries.json",
        default_relative_path="ignored.json",
    )
    assert resolved_path == root_relative
    assert label == root_relative.as_posix()

    repo_fallback = tmp_path / "repo-queries.json"
    repo_fallback.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(qrels, "resolve_repo_asset_path", lambda relative: repo_fallback)
    resolved_path, label = qrels._resolve_benchmark_asset_path(
        tmp_path,
        None,
        default_relative_path="benchmarks/queries.json",
    )
    assert resolved_path == repo_fallback
    assert label == "benchmarks/queries.json"

    assert qrels._parse_qrel_entry("q1", "doc-1", label="qrels").doc_id == "doc-1"
    assert qrels._parse_qrel_entry(
        "q1",
        {"query_id": "q1", "doc_id": "doc-2", "relevance": "2"},
        label="qrels",
    ).relevance == 2

    with pytest.raises(ValueError):
        _ = qrels._require_mapping_rows("bad", label="rows")
    with pytest.raises(ValueError):
        _ = qrels._require_mapping_rows(["bad"], label="rows")
    with pytest.raises(ValueError):
        _ = qrels._string_list("bad", label="strings")
    with pytest.raises(ValueError):
        _ = qrels._parse_qrel_entry(
            "q1",
            {"query_id": "other", "doc_id": "doc-1"},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = qrels._parse_qrel_entry(
            "q1",
            {"query_id": "q1", "doc_id": "", "relevance": 1},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = qrels._parse_qrel_entry(
            "q1",
            {"query_id": "q1", "doc_id": "doc-1", "relevance": "bad"},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = qrels._parse_qrel_entry(
            "q1",
            {"query_id": "q1", "doc_id": "doc-1", "relevance": 1.5},
            label="qrels",
        )
    with pytest.raises(ValueError):
        _ = qrels._parse_qrel_entries("q1", "bad", label="qrels")

    judgments_path = tmp_path / "judgments.json"
    judgments_path.write_text(
        json.dumps(
            {
                "judgments": [
                    {"query_id": "q1", "doc_id": "doc-1", "relevance": 1},
                    {
                        "query_id": "q2",
                        "qrels": [
                            {"query_id": "q2", "doc_id": "doc-2", "relevance": 2}
                        ],
                    },
                    {"query_id": "q3", "relevant_paths": ["doc-3", "doc-4"]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    loaded_qrels = qrels.load_qrels(judgments_path)
    assert [entry.doc_id for entry in loaded_qrels["q3"]] == ["doc-3", "doc-4"]
    assert loaded_qrels["q2"][0].relevance == 2

    monkeypatch.setattr(
        qrels,
        "load_qrels",
        lambda path: (_ for _ in ()).throw(ValueError("bad qrels")),
    )
    with pytest.raises(ValueError, match="must contain a 'judgments' mapping or list rows"):
        _ = qrels.load_judgments(tmp_path, judgments_path)


def test_baselines_lookup_tokenizer_and_operational_helpers_cover_edge_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = import_module("snowiki.bench.evaluation.candidates")
    evaluation_index = import_module("snowiki.bench.evaluation.index")
    qrels = import_module("snowiki.bench.evaluation.qrels")
    scoring = import_module("snowiki.bench.evaluation.scoring")
    from snowiki.search.indexer import SearchDocument, SearchHit

    path_hit = SearchHit(
        document=SearchDocument(
            id="",
            path="compiled/path-doc.md",
            kind="page",
            title="Path Doc",
            content="content",
        ),
        score=1.0,
        matched_terms=(),
    )
    assert scoring.hit_identifier(path_hit) == "compiled/path-doc.md"
    assert scoring.match_benchmark_hit(
        path_hit,
        [qrels.QrelEntry(query_id="q1", doc_id="fixture-a")],
        {"compiled/path-doc.md": "fixture-a"},
    ) == "fixture-a"

    duplicate_ids = scoring.ranked_doc_ids(
        [path_hit, path_hit],
        [qrels.QrelEntry(query_id="q1", doc_id="fixture-a")],
        hit_lookup={"compiled/path-doc.md": "fixture-a"},
    )
    assert duplicate_ids == ["fixture-a"]

    monkeypatch.setattr(
        evaluation_index, "resolve_legacy_tokenizer", lambda **kwargs: None
    )
    with pytest.raises(ValueError, match="could not resolve tokenizer"):
        _ = evaluation_index.tokenizer_name_for_baseline("bm25s")
    with pytest.raises(ValueError, match="unsupported baseline"):
        _ = evaluation_index.tokenizer_name_for_baseline("bm25s_kiwi_full")
    with pytest.raises(ValueError, match="unsupported baseline"):
        _ = evaluation_index.tokenizer_name_for_baseline("bogus")

    monkeypatch.setattr(
        candidates,
        "measure_regex_candidate_build",
        lambda *, records: (1.0, 2.0),
    )
    monkeypatch.setattr(
        candidates,
        "measure_bm25_candidate_build",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected bm25 measurement")),
    )
    evidence = candidates.measure_operational_evidence(
        records=[],
        bm25_indexes={"not-a-bm25-index": object()},
    )
    assert evidence["regex_v1"].disk_size_mb == 2.0

