from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

import pytest

from snowiki.bench import datasets


def test_benchmark_dataset_path_helpers_create_benchmark_subdirectories(
    tmp_path: Path,
) -> None:
    assert datasets.get_benchmark_hf_cache_root(tmp_path) == tmp_path.resolve() / "hf"
    assert datasets.get_benchmark_locks_root(tmp_path) == tmp_path.resolve() / "locks"
    assert (
        datasets.get_benchmark_materialized_root(tmp_path)
        == tmp_path.resolve() / "materialized"
    )
    assert (
        datasets.get_benchmark_downloads_root(tmp_path)
        == tmp_path.resolve() / "downloads"
    )


def test_fetch_benchmark_dataset_writes_multi_source_lock_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot_paths = {
        "BeIR/scifact": tmp_path / "hf" / "datasets--BeIR--scifact" / "snapshots" / "abc123",
        "BeIR/scifact-qrels": tmp_path
        / "hf"
        / "datasets--BeIR--scifact-qrels"
        / "snapshots"
        / "def456",
    }
    for snapshot_path in snapshot_paths.values():
        snapshot_path.mkdir(parents=True, exist_ok=True)
    call_log: list[dict[str, object]] = []

    def fake_snapshot_download(**kwargs: object) -> str:
        call_log.append(dict(kwargs))
        assert os.environ["HF_HOME"] == (tmp_path.resolve() / "hf").as_posix()
        repo_id = str(kwargs["repo_id"])
        return snapshot_paths[repo_id].as_posix()

    monkeypatch.setattr(datasets, "snapshot_download", fake_snapshot_download)
    monkeypatch.setattr(
        datasets,
        "isoformat_utc",
        lambda _value: "2026-04-20T00:00:00Z",
    )

    result = datasets.fetch_benchmark_dataset(
        "beir_scifact",
        data_root=tmp_path,
        refresh="force",
        local_files_only=True,
    )

    assert result.lock_path == tmp_path.resolve() / "locks" / "beir_scifact.json"
    assert [source.label for source in result.sources] == ["corpus_queries", "qrels"]
    assert call_log == [
        {
            "repo_id": "BeIR/scifact",
            "repo_type": "dataset",
            "revision": "main",
            "allow_patterns": ["corpus/*.parquet", "queries/*.parquet"],
            "cache_dir": tmp_path.resolve() / "hf",
            "local_files_only": True,
            "force_download": True,
        },
        {
            "repo_id": "BeIR/scifact-qrels",
            "repo_type": "dataset",
            "revision": "main",
            "allow_patterns": ["test.tsv"],
            "cache_dir": tmp_path.resolve() / "hf",
            "local_files_only": True,
            "force_download": True,
        },
    ]

    payload_raw = json.loads(result.lock_path.read_text(encoding="utf-8"))
    assert isinstance(payload_raw, dict)
    payload = cast(dict[str, object], payload_raw)
    assert payload == {
        "citation": "Wadden et al. Fact or Fiction: Verifying Scientific Claims. EMNLP 2020.",
        "dataset_id": "beir_scifact",
        "fetched_at": "2026-04-20T00:00:00Z",
        "language": "en",
        "license": "cc-by-4.0",
        "source_url": "https://huggingface.co/datasets/BeIR/scifact",
        "sources": [
            {
                "allow_patterns": ["corpus/*.parquet", "queries/*.parquet"],
                "label": "corpus_queries",
                "name": "BEIR SciFact corpus and queries",
                "repo_id": "BeIR/scifact",
                "repo_type": "dataset",
                "requested_revision": "main",
                "resolved_snapshot_path": snapshot_paths["BeIR/scifact"].resolve().as_posix(),
            },
            {
                "allow_patterns": ["test.tsv"],
                "label": "qrels",
                "name": "BEIR SciFact qrels",
                "repo_id": "BeIR/scifact-qrels",
                "repo_type": "dataset",
                "requested_revision": "main",
                "resolved_snapshot_path": snapshot_paths[
                    "BeIR/scifact-qrels"
                ].resolve().as_posix(),
            },
        ],
        "tier": "public_anchor",
    }


def test_fetch_benchmark_dataset_reuses_matching_multi_source_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot_paths = {
        "corpus_queries": tmp_path
        / "hf"
        / "datasets--BeIR--nfcorpus"
        / "snapshots"
        / "cached-corpus",
        "qrels": tmp_path
        / "hf"
        / "datasets--BeIR--nfcorpus-qrels"
        / "snapshots"
        / "cached-qrels",
    }
    for snapshot_path in snapshot_paths.values():
        snapshot_path.mkdir(parents=True, exist_ok=True)
    lock_path = tmp_path / "locks" / "beir_nfcorpus.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _ = lock_path.write_text(
        json.dumps(
            {
                "dataset_id": "beir_nfcorpus",
                "fetched_at": "2026-04-20T00:00:00Z",
                "language": "en",
                "tier": "public_anchor",
                "source_url": "https://huggingface.co/datasets/BeIR/nfcorpus",
                "citation": (
                    "Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot "
                    "Evaluation of Information Retrieval Models."
                ),
                "license": "cc-by-sa-4.0",
                "sources": [
                    {
                        "label": "corpus_queries",
                        "name": "BEIR NFCorpus corpus and queries",
                        "repo_id": "BeIR/nfcorpus",
                        "repo_type": "dataset",
                        "requested_revision": "main",
                        "resolved_snapshot_path": snapshot_paths[
                            "corpus_queries"
                        ].as_posix(),
                        "allow_patterns": ["corpus/*.parquet", "queries/*.parquet"],
                    },
                    {
                        "label": "qrels",
                        "name": "BEIR NFCorpus qrels",
                        "repo_id": "BeIR/nfcorpus-qrels",
                        "repo_type": "dataset",
                        "requested_revision": "main",
                        "resolved_snapshot_path": snapshot_paths["qrels"].as_posix(),
                        "allow_patterns": ["test.tsv"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    def fail_snapshot_download(**_: object) -> str:
        raise AssertionError("snapshot_download should not run when a matching lock exists")

    monkeypatch.setattr(datasets, "snapshot_download", fail_snapshot_download)

    result = datasets.fetch_benchmark_dataset("beir_nfcorpus", data_root=tmp_path)

    assert result.lock_path == lock_path
    assert [source.snapshot_path for source in result.sources] == [
        snapshot_paths["corpus_queries"],
        snapshot_paths["qrels"],
    ]


def test_fetch_benchmark_dataset_materializes_returned_snapshot_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot_path = tmp_path / "hf" / "datasets--mteb--MIRACLRetrieval" / "snapshots" / "empty"

    def fake_snapshot_download(**_: object) -> str:
        return snapshot_path.as_posix()

    monkeypatch.setattr(datasets, "snapshot_download", fake_snapshot_download)
    monkeypatch.setattr(
        datasets,
        "isoformat_utc",
        lambda _value: "2026-04-20T00:00:00Z",
    )

    result = datasets.fetch_benchmark_dataset(
        "miracl_ko",
        data_root=tmp_path,
        refresh="force",
    )

    assert result.sources[0].snapshot_path == snapshot_path.resolve()
    assert result.sources[0].snapshot_path.exists()
    assert result.sources[0].snapshot_path.is_dir()


def test_resolve_cached_benchmark_dataset_requires_fetch_first(tmp_path: Path) -> None:
    with pytest.raises(datasets.BenchmarkDatasetCacheMissingError) as exc_info:
        _ = datasets.resolve_cached_benchmark_dataset("beir_nq", data_root=tmp_path)

    assert (
        str(exc_info.value)
        == "benchmark dataset 'beir_nq' is not cached under "
        f"{tmp_path.resolve().as_posix()}; run `uv run snowiki benchmark-fetch "
        f"--dataset beir_nq` first"
    )
