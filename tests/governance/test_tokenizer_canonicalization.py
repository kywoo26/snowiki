from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from snowiki.cli.main import app
from snowiki.search.workspace import content_freshness_identity


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_status_output_canonicalizes_tokenizer_identity(tmp_path: Path) -> None:
    runner = CliRunner()
    root = tmp_path / "root"
    root.mkdir()

    _write_json(
        root / "index" / "manifest.json",
        {
            "tokenizer_name": "regex",
            "records_indexed": 0,
            "pages_indexed": 0,
            "content_identity": content_freshness_identity(root),
        },
    )

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(root)},
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert payload["result"]["manifest"]["tokenizer_name"] == "regex_v1"

    freshness = payload["result"]["freshness"]
    assert freshness["current_content_identity"]["tokenizer"]["name"] == "regex_v1"
    assert freshness["manifest_content_identity"]["tokenizer"]["name"] == "regex_v1"


def test_benchmark_output_canonicalizes_tokenizer_identity_in_baselines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from snowiki.cli.commands import benchmark as benchmark_command

    report_path = tmp_path / "benchmark.json"

    fake_report = {
        "generated_at": "2026-04-10T00:00:00Z",
        "report_version": "1.2",
        "preset": {
            "name": "test",
            "description": "test",
            "query_kinds": [],
            "top_k": 5,
        },
        "corpus": {"queries_evaluated": 0, "fixtures_indexed": 0},
        "protocol": {
            "isolated_root": True,
            "warmups": 0,
            "repetitions": 1,
            "query_mode": "lexical",
            "top_k": 5,
        },
        "performance": {},
        "benchmark_verdict": {"verdict": "PASS", "exit_code": 0},
        "retrieval": {
            "preset": {
                "name": "test",
                "description": "test",
                "query_kinds": [],
                "top_k": 5,
            },
            "corpus": {
                "records_indexed": 0,
                "pages_indexed": 0,
                "raw_documents": 0,
                "blended_documents": 0,
                "queries_evaluated": 0,
            },
            "baselines": {
                "bm25s_kiwi": {
                    "name": "bm25s_kiwi",
                    "tokenizer_name": "kiwi",
                    "quality": {"thresholds": []},
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                }
            },
        },
    }

    monkeypatch.setattr(
        benchmark_command, "seed_canonical_benchmark_root", lambda root: []
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

    assert result.exit_code == 0

    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert "bm25s_kiwi_full" in payload["retrieval"]["baselines"]
    assert "bm25s_kiwi" not in payload["retrieval"]["baselines"]

    baseline = payload["retrieval"]["baselines"]["bm25s_kiwi_full"]
    assert baseline["name"] == "bm25s_kiwi_full"
    assert baseline["tokenizer_name"] == "kiwi_morphology_v1"


def test_benchmark_output_preserves_already_canonical_tokenizer_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from snowiki.cli.commands import benchmark as benchmark_command

    report_path = tmp_path / "benchmark.json"

    fake_report = {
        "generated_at": "2026-04-10T00:00:00Z",
        "report_version": "1.2",
        "preset": {
            "name": "test",
            "description": "test",
            "query_kinds": [],
            "top_k": 5,
        },
        "corpus": {"queries_evaluated": 0, "fixtures_indexed": 0},
        "protocol": {
            "isolated_root": True,
            "warmups": 0,
            "repetitions": 1,
            "query_mode": "lexical",
            "top_k": 5,
        },
        "performance": {},
        "benchmark_verdict": {"verdict": "PASS", "exit_code": 0},
        "retrieval": {
            "preset": {
                "name": "test",
                "description": "test",
                "query_kinds": [],
                "top_k": 5,
            },
            "corpus": {
                "records_indexed": 0,
                "pages_indexed": 0,
                "raw_documents": 0,
                "blended_documents": 0,
                "queries_evaluated": 0,
            },
            "baselines": {
                "bm25s_kiwi_nouns": {
                    "name": "bm25s_kiwi_nouns",
                    "tokenizer_name": "kiwi_nouns_v1",
                    "quality": {"thresholds": []},
                    "latency": {
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "mean_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                    },
                    "queries": [],
                }
            },
        },
    }

    monkeypatch.setattr(
        benchmark_command, "seed_canonical_benchmark_root", lambda root: []
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

    assert result.exit_code == 0

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    baseline = payload["retrieval"]["baselines"]["bm25s_kiwi_nouns"]
    assert baseline["tokenizer_name"] == "kiwi_nouns_v1"


def test_status_human_output_surfaces_canonical_tokenizer(tmp_path: Path) -> None:
    runner = CliRunner()
    root = tmp_path / "root"
    root.mkdir()

    _write_json(
        root / "index" / "manifest.json",
        {
            "tokenizer_name": "regex",
            "records_indexed": 0,
            "pages_indexed": 0,
            "content_identity": content_freshness_identity(root),
        },
    )

    result = runner.invoke(app, ["status"], env={"SNOWIKI_ROOT": str(root)})

    assert result.exit_code == 0
    assert "tokenizer=regex_v1" in result.output


def test_status_output_fails_closed_on_unknown_tokenizer(tmp_path: Path) -> None:
    from snowiki.search.workspace import (
        StaleTokenizerArtifactError,
        build_retrieval_snapshot,
    )

    runner = CliRunner()
    root = tmp_path / "root"
    root.mkdir()

    _write_json(
        root / "index" / "manifest.json",
        {
            "tokenizer_name": "unknown_tokenizer",
            "records_indexed": 0,
            "pages_indexed": 0,
            "content_identity": content_freshness_identity(root),
        },
    )

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(root)},
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["result"]["manifest"]["tokenizer_name"] is None

    with pytest.raises(StaleTokenizerArtifactError, match="rebuild required"):
        build_retrieval_snapshot(root)


def test_bm25_load_fails_closed_on_unknown_tokenizer(tmp_path: Path) -> None:
    from snowiki.search.bm25_index import BM25SearchIndex
    from snowiki.search.workspace import StaleTokenizerArtifactError

    root = tmp_path / "root"
    root.mkdir()
    index_path = root / "bm25.index"
    meta_path = root / "bm25.index.snowiki_meta.json"

    meta_path.write_text(
        json.dumps(
            {
                "method": "lucene",
                "tokenizer_name": "unknown_tokenizer",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(StaleTokenizerArtifactError, match="rebuild required"):
        BM25SearchIndex.load(str(index_path), documents=[])
