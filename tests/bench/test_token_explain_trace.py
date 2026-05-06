from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import cast

import pytest
from click.testing import CliRunner, Result

from snowiki.cli.main import app
from snowiki.search.registry import get as get_tokenizer_spec

TOKEN_EXPLAIN_TRACE_SCHEMA_VERSION = "experimental.token_explain.v1"
REGRESSION_MATRIX_PATH = "benchmarks/contracts/snowiki_regression_matrix.yaml"
DIAGNOSTIC_TARGET_ID = "bm25_kiwi_morphology_v1"
REQUIRED_EXPLAIN_TRACE_QUERY_IDS = frozenset(
    {
        "ko_source_provenance_inflection",
        "cjk_mixed_code_bm25_cache",
        "identifier_bm25_index",
    }
)
EXPECTED_TRACE_LIMITS = {
    "max_query_tokens": 128,
    "max_traced_returned_docs": 5,
    "max_matched_terms_per_doc": 64,
}
EXPECTED_VISIBLE_TRACE_TOKENS = {
    "ko_source_provenance_inflection": {"무너뜨리", "provenance", "계층", "근거"},
    "cjk_mixed_code_bm25_cache": {
        "한국어",
        "bm25searchindex",
        "tokenizer",
        "cache",
        "serialization",
    },
    "identifier_bm25_index": {
        "bm25searchindex",
        "tokenizer",
        "cache",
        "serialization",
        "search",
        "results",
    },
}


@pytest.fixture(scope="module")
def diagnostic_regression_report(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[dict[str, object]]:
    tmp_path = tmp_path_factory.mktemp("token-explain-diagnostics")
    report_path = tmp_path / "snowiki-regression-diagnostics.json"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    try:
        result = _invoke_benchmark(
            "--matrix",
            REGRESSION_MATRIX_PATH,
            "--level",
            "regression",
            "--target",
            DIAGNOSTIC_TARGET_ID,
            "--include-diagnostics",
            "--report",
            str(report_path),
        )

        assert result.exit_code == 0, result.output
        yield _read_json(report_path)
    finally:
        monkeypatch.undo()


def test_explain_trace_schema_version(
    diagnostic_regression_report: dict[str, object],
) -> None:
    trace = _token_explain_trace(
        diagnostic_regression_report,
        "ko_source_provenance_inflection",
    )

    assert trace["schema_version"] == TOKEN_EXPLAIN_TRACE_SCHEMA_VERSION


def test_explain_trace_identity_fields(
    diagnostic_regression_report: dict[str, object],
) -> None:
    tokenizer_spec = get_tokenizer_spec("kiwi_morphology_v1")
    trace = _token_explain_trace(
        diagnostic_regression_report,
        "ko_source_provenance_inflection",
    )

    assert trace["analyzer_name"] == "bm25"
    assert trace["tokenizer_name"] == tokenizer_spec.name
    assert trace["tokenizer_version"] == tokenizer_spec.version
    assert trace["tokenizer_config"] == {
        "family": tokenizer_spec.family,
        "runtime_supported": tokenizer_spec.runtime_supported,
    }


def test_explain_trace_query_tokens_are_visible_for_korean_cjk_queries(
    diagnostic_regression_report: dict[str, object],
) -> None:
    for query_id in REQUIRED_EXPLAIN_TRACE_QUERY_IDS:
        trace = _token_explain_trace(diagnostic_regression_report, query_id)
        query_tokens = trace["query_tokens"]

        assert isinstance(query_tokens, list)
        assert query_tokens
        assert all(isinstance(token, str) for token in query_tokens)


def test_explain_trace_matched_terms_are_compact_returned_doc_evidence(
    diagnostic_regression_report: dict[str, object],
) -> None:
    trace = _token_explain_trace(
        diagnostic_regression_report,
        "cjk_mixed_code_bm25_cache",
    )
    matched_terms = trace["matched_terms"]
    ranked_doc_ids = _ranked_doc_ids(diagnostic_regression_report, "cjk_mixed_code_bm25_cache")

    assert isinstance(matched_terms, list)
    assert 0 < len(matched_terms) <= EXPECTED_TRACE_LIMITS["max_traced_returned_docs"]
    for entry in matched_terms:
        assert isinstance(entry, Mapping)
        entry_mapping = cast(Mapping[str, object], entry)
        assert set(entry_mapping) == {"rank", "doc_id", "terms"}
        assert isinstance(entry_mapping["rank"], int)
        assert entry_mapping["doc_id"] in ranked_doc_ids
        terms = entry_mapping["terms"]
        assert isinstance(terms, list)
        assert len(terms) <= EXPECTED_TRACE_LIMITS["max_matched_terms_per_doc"]
        assert all(isinstance(term, str) for term in terms)
        assert "document_tokens" not in entry_mapping
        assert "document" not in entry_mapping
        assert "content" not in entry_mapping


def test_explain_trace_limits_and_truncation_flags(
    diagnostic_regression_report: dict[str, object],
) -> None:
    trace = _token_explain_trace(
        diagnostic_regression_report,
        "identifier_bm25_index",
    )
    truncated = trace["truncated"]

    assert trace["limits"] == EXPECTED_TRACE_LIMITS
    assert isinstance(truncated, Mapping)
    assert set(truncated) == {"query_tokens", "returned_docs", "matched_terms"}
    assert all(isinstance(value, bool) for value in truncated.values())


def test_explain_trace_omitted_without_diagnostics_and_report_shape_stays_stable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    report_path = tmp_path / "snowiki-regression.json"

    result = _invoke_benchmark(
        "--matrix",
        REGRESSION_MATRIX_PATH,
        "--level",
        "regression",
        "--target",
        DIAGNOSTIC_TARGET_ID,
        "--report",
        str(report_path),
    )

    assert result.exit_code == 0, result.output
    payload = _read_json(report_path)
    cell = _single_cell(payload)
    per_query = _per_query(payload)

    assert set(cell) == {
        "dataset_id",
        "level_id",
        "target_id",
        "status",
        "metrics",
        "latency",
        "per_query",
        "slices",
        "error",
        "cache",
    }
    assert "run_classification" not in cell
    assert "public_baseline_comparable" not in cell
    assert isinstance(cell["metrics"], list)
    assert isinstance(cell["latency"], Mapping)
    assert isinstance(cell["slices"], Mapping)
    for query_id in REQUIRED_EXPLAIN_TRACE_QUERY_IDS:
        evidence = cast(Mapping[str, object], per_query[query_id])
        assert set(evidence) == {
            "query",
            "ranked_doc_ids",
            "relevant_doc_ids",
            "latency_ms",
            "metrics",
        }
        assert "diagnostics" not in evidence
        assert "token_explain_trace" not in evidence


def test_explain_trace_korean_token_visibility(
    diagnostic_regression_report: dict[str, object],
) -> None:
    for query_id, expected_tokens in EXPECTED_VISIBLE_TRACE_TOKENS.items():
        trace = _token_explain_trace(diagnostic_regression_report, query_id)
        query_tokens = set(cast(list[str], trace["query_tokens"]))
        matched_tokens = {
            term
            for entry in cast(list[Mapping[str, object]], trace["matched_terms"])
            for term in cast(list[str], entry["terms"])
        }
        visible_tokens = query_tokens | matched_tokens

        assert visible_tokens >= expected_tokens


def _invoke_benchmark(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(app, ["benchmark", *args])


def _read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def _single_cell(payload: Mapping[str, object]) -> Mapping[str, object]:
    cells = payload["cells"]
    assert isinstance(cells, list)
    assert len(cells) == 1
    cell = cells[0]
    assert isinstance(cell, Mapping)
    return cast(Mapping[str, object], cell)


def _per_query(payload: Mapping[str, object]) -> Mapping[str, object]:
    cell = _single_cell(payload)
    per_query = cell["per_query"]
    assert isinstance(per_query, Mapping)
    per_query_mapping = cast(Mapping[str, object], per_query)
    assert set(per_query_mapping) >= REQUIRED_EXPLAIN_TRACE_QUERY_IDS
    return per_query_mapping


def _token_explain_trace(
    payload: Mapping[str, object],
    query_id: str,
) -> Mapping[str, object]:
    per_query = _per_query(payload)
    evidence = per_query[query_id]
    assert isinstance(evidence, Mapping)
    evidence_mapping = cast(Mapping[str, object], evidence)
    trace = evidence_mapping.get("token_explain_trace")
    assert isinstance(trace, Mapping)
    return cast(Mapping[str, object], trace)


def _ranked_doc_ids(payload: Mapping[str, object], query_id: str) -> list[str]:
    per_query = _per_query(payload)
    evidence = per_query[query_id]
    assert isinstance(evidence, Mapping)
    evidence_mapping = cast(Mapping[str, object], evidence)
    ranked_doc_ids = evidence_mapping["ranked_doc_ids"]
    assert isinstance(ranked_doc_ids, list)
    assert all(isinstance(doc_id, str) for doc_id in ranked_doc_ids)
    return cast(list[str], ranked_doc_ids)
