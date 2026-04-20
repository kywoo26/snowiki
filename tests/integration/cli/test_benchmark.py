from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from snowiki.bench.corpus import BenchmarkCorpusManifest
from snowiki.cli.commands import benchmark as benchmark_command
from snowiki.cli.main import app

_EXPANDED_BASELINES = [
    "lexical",
    "bm25s",
    "bm25s_kiwi_nouns",
    "bm25s_kiwi_full",
    "bm25s_mecab_full",
    "bm25s_hf_wordpiece",
]


def _fake_report(
    *,
    structural_fail: bool = False,
    retrieval_fail: bool = False,
    performance_fail: bool = False,
    warning_only: bool = False,
    retrieval_blocking: bool = True,
) -> dict[str, object]:
    warning_count = 1 if warning_only else 0
    structural_failures = (
        [
            {
                "stage": "lint",
                "code": "L001",
                "path": "normalized/bad.json",
                "message": "missing required key: id",
            }
        ]
        if structural_fail
        else []
    )
    structural_warnings = (
        [
            {
                "stage": "integrity",
                "code": "L003",
                "severity": "warning",
                "path": "compiled/orphan.md",
                "message": "orphan page",
            }
        ]
        if warning_only
        else []
    )
    performance_thresholds = [
        {
            "gate": "ingest",
            "metric": "p50_ms",
            "value": 12.0,
            "delta": 5938.0,
            "verdict": "PASS",
            "threshold": 5950.0,
            "warnings": [],
        },
        {
            "gate": "ingest",
            "metric": "p95_ms",
            "value": 18.0,
            "delta": 6282.0,
            "verdict": "PASS",
            "threshold": 6300.0,
            "warnings": [],
        },
        {
            "gate": "rebuild",
            "metric": "p50_ms",
            "value": 30.0,
            "delta": 5920.0,
            "verdict": "PASS",
            "threshold": 5950.0,
            "warnings": [],
        },
        {
            "gate": "rebuild",
            "metric": "p95_ms",
            "value": 45.0,
            "delta": 6255.0,
            "verdict": "PASS",
            "threshold": 6300.0,
            "warnings": [],
        },
        {
            "gate": "query",
            "metric": "p50_ms",
            "value": 6.0,
            "delta": 5944.0,
            "verdict": "PASS",
            "threshold": 5950.0,
            "warnings": [],
        },
        {
            "gate": "query",
            "metric": "p95_ms",
            "value": 6400.0 if performance_fail else 9.0,
            "delta": 100.0 if performance_fail else 6291.0,
            "verdict": "FAIL" if performance_fail else "PASS",
            "threshold": 6300.0,
            "warnings": [],
        },
    ]
    return {
        "generated_at": "2026-04-10T00:00:00Z",
        "report_version": "1.3",
        "preset": {
            "name": "retrieval",
            "description": "Known-item and topical retrieval benchmark coverage.",
            "query_kinds": ["known-item", "topical"],
            "top_k": 5,
            "top_ks": [1, 3, 5, 10, 20],
        },
        "structural": {
            "ok": not structural_fail,
            "error_count": len(structural_failures),
            "warning_count": warning_count,
            "failures": structural_failures,
            "warnings": structural_warnings,
        },
        "corpus": {
            "queries_path": "benchmarks/queries.json",
            "judgments_path": "benchmarks/judgments.json",
            "fixtures": [],
            "fixtures_indexed": 12,
            "queries_evaluated": 18,
        },
        "protocol": {
            "isolated_root": True,
            "warmups": 1,
            "repetitions": 5,
            "query_mode": "lexical",
            "top_k": 5,
        },
        "performance": {
            "ingest": {"p50_ms": 12.0, "p95_ms": 18.0},
            "rebuild": {"p50_ms": 30.0, "p95_ms": 45.0},
            "query": {"p50_ms": 6.0, "p95_ms": 6400.0 if performance_fail else 9.0},
        },
        "performance_threshold_policy": [
            {"metric": "p50_ms", "value": 5950.0, "operator": "<="},
            {"metric": "p95_ms", "value": 6300.0, "operator": "<="},
        ],
        "performance_thresholds": performance_thresholds,
        "retrieval": {
            "threshold_policy": {
                "overall": [
                    {"metric": "recall_at_k", "value": 0.72, "operator": ">="},
                    {"metric": "mrr", "value": 0.7, "operator": ">="},
                    {"metric": "ndcg_at_k", "value": 0.67, "operator": ">="},
                ],
                "slices": {
                    "known-item": [
                        {"metric": "recall_at_k", "value": 0.7, "operator": ">="},
                        {"metric": "mrr", "value": 0.6, "operator": ">="},
                    ],
                    "topical": [
                        {"metric": "recall_at_k", "value": 0.49, "operator": ">="},
                        {"metric": "ndcg_at_k", "value": 0.5, "operator": ">="},
                    ],
                    "temporal": [
                        {"metric": "recall_at_k", "value": 0.47, "operator": ">="}
                    ],
                },
            },
            "preset": {
                "name": "retrieval",
                "description": "Known-item and topical retrieval benchmark coverage.",
                "query_kinds": ["known-item", "topical"],
                "top_k": 5,
                "baselines": _EXPANDED_BASELINES,
            },
            "corpus": {
                "records_indexed": 12,
                "pages_indexed": 8,
                "raw_documents": 14,
                "blended_documents": 16,
                "queries_evaluated": 18,
            },
            "candidate_matrix": {
                "candidates": [
                    {
                        "candidate_name": "regex_v1",
                        "role": "control",
                        "admission_status": "admitted",
                        "evidence_baseline": "lexical",
                    },
                    {
                        "candidate_name": "kiwi_morphology_v1",
                        "role": "candidate",
                        "admission_status": "admitted",
                        "evidence_baseline": "bm25s_kiwi_full",
                    },
                    {
                        "candidate_name": "mecab_morphology_v1",
                        "role": "candidate",
                        "admission_status": "admitted",
                        "evidence_baseline": "bm25s_mecab_full",
                    },
                    {
                        "candidate_name": "hf_wordpiece_v1",
                        "role": "candidate",
                        "admission_status": "admitted",
                        "evidence_baseline": "bm25s_hf_wordpiece",
                    },
                ],
                "decisions": [
                    {
                        "candidate_name": "kiwi_morphology_v1",
                        "disposition": "promote",
                        "reasons": ["beats_regex"],
                    }
                ],
            },
            "baselines": {
                "lexical": {
                    "name": "lexical",
                    "tokenizer_name": "regex_v1",
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                    "quality": {
                        "thresholds": [
                            {
                                "gate": "overall",
                                "metric": "recall_at_k",
                                "value": 0.82,
                                "delta": 0.1,
                                "verdict": "PASS",
                                "threshold": 0.72,
                                "warnings": [],
                            }
                        ]
                    },
                },
                "bm25s": {
                    "name": "bm25s",
                    "tokenizer_name": "regex_v1",
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                    "quality": {
                        "thresholds": [
                            {
                                "gate": "overall",
                                "metric": "mrr",
                                "value": 0.68,
                                "delta": 0.02,
                                "verdict": "FAIL" if retrieval_fail else "PASS",
                                "threshold": 0.7,
                                "warnings": [],
                            }
                        ]
                    },
                },
                "bm25s_kiwi_nouns": {
                    "name": "bm25s_kiwi_nouns",
                    "tokenizer_name": "kiwi_nouns_v1",
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                    "quality": {"thresholds": []},
                },
                "bm25s_kiwi_full": {
                    "name": "bm25s_kiwi_full",
                    "tokenizer_name": "kiwi_morphology_v1",
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                    "quality": {"thresholds": []},
                },
                "bm25s_mecab_full": {
                    "name": "bm25s_mecab_full",
                    "tokenizer_name": "mecab_morphology_v1",
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                    "quality": {"thresholds": []},
                },
                "bm25s_hf_wordpiece": {
                    "name": "bm25s_hf_wordpiece",
                    "tokenizer_name": "hf_wordpiece_v1",
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                    "quality": {"thresholds": []},
                },
            },
        },
        "benchmark_verdict": {
            "verdict": (
                "FAIL"
                if structural_fail
                or performance_fail
                or (retrieval_fail and retrieval_blocking)
                else "PASS"
            ),
            "exit_code": 1
            if structural_fail
            or performance_fail
            or (retrieval_fail and retrieval_blocking)
            else 0,
            "blocking_stage": (
                "structural"
                if structural_fail
                else "phase1_thresholds"
                if performance_fail or (retrieval_fail and retrieval_blocking)
                else None
            ),
            "order": [
                "structural",
                "retrieval_thresholds",
                "performance_thresholds",
                "informational",
            ],
            "stages": [
                {
                    "name": "structural",
                    "verdict": "FAIL" if structural_fail else "PASS",
                    "blocking": True,
                    "failure_count": len(structural_failures),
                    "warning_count": warning_count,
                },
                {
                    "name": "retrieval_thresholds",
                    "verdict": "FAIL" if retrieval_fail else "PASS",
                    "blocking": retrieval_blocking,
                    "failure_count": 1 if retrieval_fail else 0,
                },
                {
                    "name": "performance_thresholds",
                    "verdict": "FAIL" if performance_fail else "PASS",
                    "blocking": True,
                    "failure_count": 1 if performance_fail else 0,
                },
                {
                    "name": "informational",
                    "verdict": "WARN" if warning_only else "PASS",
                    "blocking": False,
                    "warning_count": warning_count,
                },
            ],
        },
    }


def test_benchmark_writes_json_report_and_renders_unified_phase1_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    fake_report = _fake_report(warning_only=True)
    seeded_roots: list[Path] = []
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: seeded_roots.append(root) or [],
    )
    monkeypatch.setattr(
        benchmark_command, "generate_report", lambda *args, **kwargs: fake_report
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark", "--preset", "core", "--output", str(report_path)],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert len(seeded_roots) == 1
    assert seeded_roots[0] != tmp_path / "root"
    assert seeded_roots[0].name.startswith("run-")
    assert seeded_roots[0].parent == report_path.parent / ".snowiki-benchmark-root"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    retrieval = payload["retrieval"]
    assert "candidate_matrix" in retrieval
    assert "candidates" in retrieval["candidate_matrix"]
    assert "semantic_slots" not in payload
    assert "semantic_slots" not in retrieval
    assert "token_reduction" not in retrieval
    assert payload["performance"]["ingest"] == {"p50_ms": 12.0, "p95_ms": 18.0}
    assert payload["performance_threshold_policy"] == [
        {"metric": "p50_ms", "value": 5950.0, "operator": "<="},
        {"metric": "p95_ms", "value": 6300.0, "operator": "<="},
    ]
    assert payload["report_version"] == "1.3"
    assert payload["preset"]["top_ks"] == [1, 3, 5, 10, 20]
    assert retrieval["threshold_policy"]["overall"] == [
        {"metric": "recall_at_k", "value": 0.72, "operator": ">="},
        {"metric": "mrr", "value": 0.7, "operator": ">="},
        {"metric": "ndcg_at_k", "value": 0.67, "operator": ">="},
    ]
    assert retrieval["threshold_policy"]["slices"] == {
        "known-item": [
            {"metric": "recall_at_k", "value": 0.7, "operator": ">="},
            {"metric": "mrr", "value": 0.6, "operator": ">="},
        ],
        "topical": [
            {"metric": "recall_at_k", "value": 0.49, "operator": ">="},
            {"metric": "ndcg_at_k", "value": 0.5, "operator": ">="},
        ],
        "temporal": [{"metric": "recall_at_k", "value": 0.47, "operator": ">="}],
    }
    assert retrieval["preset"]["baselines"] == _EXPANDED_BASELINES
    assert payload["performance_thresholds"][-1]["verdict"] == "PASS"
    assert payload["benchmark_verdict"]["exit_code"] == 0
    assert "Structural verdict: PASS (0 failures, 1 warnings)" in result.output
    assert "Informational warnings:" in result.output
    assert "Performance threshold policy:" in result.output
    assert "Performance threshold verdict: PASS (0 failures)" in result.output
    assert "Retrieval threshold policy:" in result.output
    assert "Retrieval threshold verdict: PASS (0 failures)" in result.output
    assert "- lexical (regex_v1) overall recall_at_k: PASS" in result.output
    assert "- bm25s (regex_v1) overall mrr: PASS" in result.output
    assert "Candidate Matrix:" in result.output
    assert (
        "- regex_v1: role=control, status=admitted, baseline=lexical" in result.output
    )
    assert (
        "- kiwi_morphology_v1: role=candidate, status=admitted, baseline=bm25s_kiwi_full"
        in result.output
    )
    assert "Candidate Decisions:" in result.output
    assert "- kiwi_morphology_v1: PROMOTE (beats_regex)" in result.output
    assert "top_ks=[1, 3, 5, 10, 20]" in result.output
    assert (
        "Unified benchmark verdict: PASS (blocking_stage=None, exit_code=0)"
        in result.output
    )
    assert "Tokenizer comparison written to " in result.output
    assert ".cache/tokenizer_comparison.md" in result.output
    match = re.search(r"Tokenizer comparison written to (.+)", result.output)
    assert match is not None
    artifact_path = Path(match.group(1).strip())
    assert artifact_path.exists()
    assert ".snowiki-benchmark-root" in artifact_path.as_posix()
    assert artifact_path.read_text(encoding="utf-8").startswith("Tokenizer comparison:\n")


def test_benchmark_preserves_explicit_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    explicit_root = tmp_path / "explicit-root"
    seeded_roots: list[Path] = []
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: seeded_roots.append(root) or [],
    )
    monkeypatch.setattr(
        benchmark_command, "generate_report", lambda *args, **kwargs: _fake_report()
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "core",
            "--output",
            str(report_path),
            "--root",
            str(explicit_root),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "ignored-root")},
    )

    assert result.exit_code == 0, result.output
    assert seeded_roots == [explicit_root]
    artifact_path = explicit_root / ".cache" / "tokenizer_comparison.md"
    assert artifact_path.exists()
    assert f"Tokenizer comparison written to {artifact_path}" in result.output
    artifact_text = artifact_path.read_text(encoding="utf-8")
    assert "Tokenizer comparison:" in artifact_text
    assert "| Baseline" in artifact_text
    assert "| lexical" in artifact_text


def test_benchmark_regression_ignores_sample_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    seeded_roots: list[Path] = []
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: seeded_roots.append(root) or [],
    )
    monkeypatch.setattr(
        benchmark_command, "generate_report", lambda *args, **kwargs: _fake_report()
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "core",
            "--sample-mode",
            "full",
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert len(seeded_roots) == 1


@pytest.mark.parametrize(
    ("dataset", "extra_args", "expected_sample_mode"),
    [
        ("miracl_ko", ["--sample-mode", "quick"], "quick"),
        ("mr_tydi_ko", ["--sample-mode", "full"], "full"),
        ("beir_scifact", [], "standard"),
        ("beir_nfcorpus", ["--sample-mode", "full"], "full"),
    ],
)
def test_benchmark_public_anchor_cli_propagates_sample_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dataset: str,
    extra_args: list[str],
    expected_sample_mode: str,
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    seeded_calls: list[tuple[Path, str, str]] = []
    monkeypatch.setattr(
        benchmark_command,
        "_ensure_seeded_root",
        lambda root, *, dataset, sample_mode: seeded_calls.append(
            (root, dataset, sample_mode)
        )
        or None,
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(retrieval_blocking=False),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "retrieval",
            "--dataset",
            dataset,
            *extra_args,
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert len(seeded_calls) == 1
    _, seeded_dataset, seeded_sample_mode = seeded_calls[0]
    assert seeded_dataset == dataset
    assert seeded_sample_mode == expected_sample_mode


def test_benchmark_returns_non_zero_when_performance_threshold_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: [],
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(performance_fail=True),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark", "--preset", "retrieval", "--output", str(report_path)],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 1, result.output
    assert "Performance threshold failures:" in result.output
    assert "Performance threshold verdict: FAIL (1 failures)" in result.output
    assert (
        "Unified benchmark verdict: FAIL (blocking_stage=phase1_thresholds, exit_code=1)"
        in result.output
    )
    assert report_path.exists()


def test_benchmark_non_regression_retrieval_failures_are_non_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    monkeypatch.setattr(
        benchmark_command,
        "_ensure_seeded_root",
        lambda root, *, dataset, sample_mode: None,
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(
            retrieval_fail=True,
            retrieval_blocking=False,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "retrieval",
            "--dataset",
            "snowiki_shaped",
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert "Retrieval threshold failures:" in result.output
    assert "Retrieval threshold verdict: FAIL (1 failures)" in result.output
    assert (
        "Unified benchmark verdict: PASS (blocking_stage=None, exit_code=0)"
        in result.output
    )


def test_benchmark_structural_failures_take_precedence_over_threshold_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    monkeypatch.setattr(
        benchmark_command,
        "seed_canonical_benchmark_root",
        lambda root: [],
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(
            structural_fail=True, retrieval_fail=True, performance_fail=True
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark", "--preset", "retrieval", "--output", str(report_path)],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 1, result.output
    assert "Structural failures:" in result.output
    assert "Retrieval threshold failures:" in result.output
    assert "Performance threshold failures:" in result.output
    assert (
        "Unified benchmark verdict: FAIL (blocking_stage=structural, exit_code=1)"
        in result.output
    )


def test_benchmark_help_mentions_isolated_temp_root() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["benchmark", "--help"])

    assert result.exit_code == 0, result.output
    assert "hidden_holdout" in result.output
    assert "beir_small" not in result.output
    assert "--sample-mode" in result.output
    assert "Public-anchor dataset sample mode" in result.output
    assert "quick=200" in result.output
    assert "hidden-holdout tiers" in result.output
    assert "defaults to an isolated" in result.output
    assert "local benchmark root" in result.output
    assert "output" in result.output
    assert "directory" in result.output


def test_benchmark_hidden_holdout_dataset_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    monkeypatch.setattr(
        benchmark_command,
        "_ensure_seeded_root",
        lambda root, *, dataset, sample_mode: None,
    )
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "core",
            "--dataset",
            "hidden_holdout",
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert (
        "Warning: hidden_holdout is a development-only synthetic facsimile" in result.output
    )


def test_benchmark_public_anchor_uses_cached_manifest_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    loader_calls: list[str] = []
    manifest = BenchmarkCorpusManifest(
        tier="public_anchor",
        documents=[
            {
                "id": "miracl-doc-1",
                "content": "서울 도서관 운영 안내",
                "metadata": {
                    "title": "서울 도서관",
                    "summary": "서울 도서관 운영 안내",
                    "recorded_at": "2026-04-20T00:00:00Z",
                    "language": "ko",
                },
            }
        ],
        queries=[
            {
                "id": "miracl-q-1",
                "text": "서울 도서관 운영 시간이 궁금해",
                "group": "ko",
                "kind": "known-item",
            }
        ],
        judgments={
            "miracl-q-1": [
                {
                    "query_id": "miracl-q-1",
                    "doc_id": "miracl-doc-1",
                    "relevance": 1,
                }
            ]
        },
        dataset_id="miracl_ko",
        dataset_name="MIRACL Korean",
        dataset_metadata={"synthetic_sample": False},
    )

    monkeypatch.setattr(
        benchmark_command,
        "load_miracl_ko_cached_manifest",
        lambda *, sample_mode="standard": loader_calls.append(sample_mode) or manifest,
    )
    monkeypatch.setattr(benchmark_command, "load_corpus_from_manifest", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(retrieval_blocking=False),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "retrieval",
            "--dataset",
            "miracl_ko",
            "--sample-mode",
            "quick",
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert loader_calls == ["quick"]


def test_benchmark_public_anchor_default_loader_sample_mode_is_standard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    loader_calls: list[str] = []
    manifest = BenchmarkCorpusManifest(
        tier="public_anchor",
        documents=[
            {
                "id": "scifact-doc-1",
                "content": "Public anchor document.",
                "metadata": {"title": "SciFact", "summary": "Public anchor document."},
            }
        ],
        queries=[
            {
                "id": "scifact-q-1",
                "text": "public anchor query",
                "group": "en",
                "kind": "known-item",
            }
        ],
        judgments={
            "scifact-q-1": [
                {
                    "query_id": "scifact-q-1",
                    "doc_id": "scifact-doc-1",
                    "relevance": 1,
                }
            ]
        },
        dataset_id="beir_scifact",
        dataset_name="BEIR SciFact",
        dataset_metadata={"synthetic_sample": False},
    )

    monkeypatch.setattr(
        benchmark_command,
        "load_beir_scifact_cached_manifest",
        lambda *, sample_mode="standard": loader_calls.append(sample_mode) or manifest,
    )
    monkeypatch.setattr(benchmark_command, "load_corpus_from_manifest", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(retrieval_blocking=False),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "retrieval",
            "--dataset",
            "beir_scifact",
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert loader_calls == ["standard"]


@pytest.mark.parametrize(
    ("dataset", "loader_name"),
    [
        ("snowiki_shaped", "load_snowiki_shaped_suite"),
        ("hidden_holdout", "load_hidden_holdout_suite"),
    ],
)
def test_benchmark_non_public_datasets_ignore_sample_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dataset: str,
    loader_name: str,
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"
    tier = "snowiki_shaped" if dataset == "snowiki_shaped" else "hidden_holdout"
    manifest = BenchmarkCorpusManifest(
        tier=tier,
        documents=[
            {
                "id": f"{dataset}-doc-1",
                "content": "fixture content",
                "metadata": {"title": "fixture title"},
            }
        ],
        queries=[
            {
                "id": f"{dataset}-q-1",
                "text": "fixture query",
                "group": "fixture",
                "kind": "known-item",
            }
        ],
        judgments={
            f"{dataset}-q-1": [
                {
                    "query_id": f"{dataset}-q-1",
                    "doc_id": f"{dataset}-doc-1",
                    "relevance": 1,
                }
            ]
        },
        dataset_id=dataset,
        dataset_name=dataset,
        dataset_metadata={"synthetic_sample": True},
    )
    loader_calls: list[str] = []

    monkeypatch.setattr(
        benchmark_command,
        loader_name,
        lambda: loader_calls.append(dataset) or manifest,
    )
    monkeypatch.setattr(benchmark_command, "load_corpus_from_manifest", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        benchmark_command,
        "generate_report",
        lambda *args, **kwargs: _fake_report(retrieval_blocking=False),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "retrieval",
            "--dataset",
            dataset,
            "--sample-mode",
            "full",
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert loader_calls == [dataset]


def test_benchmark_public_anchor_requires_explicit_fetch_first(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "reports" / "benchmark.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--preset",
            "retrieval",
            "--dataset",
            "beir_scifact",
            "--output",
            str(report_path),
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 1, result.output
    assert "benchmark dataset 'beir_scifact' is not cached under" in result.output
    assert "uv run snowiki benchmark-fetch --dataset beir_scifact" in result.output
