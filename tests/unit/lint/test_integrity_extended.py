from __future__ import annotations

import json
from pathlib import Path

import pytest

from snowiki.lint import integrity
from snowiki.search.retrieval_identity import retrieval_identity_for_tokenizer
from snowiki.search.workspace import current_runtime_tokenizer_name
from snowiki.storage.index_manifest import (
    IndexManifest,
    current_index_identity,
    write_index_manifest,
)
from snowiki.storage.zones import StoragePaths


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_check_layer_integrity_reports_missing_provenance_and_compiled_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_json(tmp_path / "normalized" / "record.json", {"provenance": {}})
    monkeypatch.setattr(integrity, "find_stale_wikilinks", lambda base: [])
    monkeypatch.setattr(integrity, "find_orphaned_compiled_pages", lambda base: [])

    result = integrity.check_layer_integrity(tmp_path)

    assert result["root"] == tmp_path.as_posix()
    assert result["error_count"] == 2
    assert result["issues"] == [
        {
            "code": "L101",
            "check": "integrity.raw_provenance",
            "severity": "error",
            "path": "normalized/record.json",
            "message": "normalized record missing raw provenance",
        },
        {
            "code": "L103",
            "check": "integrity.compiled_layer",
            "severity": "error",
            "path": "compiled",
            "message": "compiled layer missing for existing normalized records",
        },
    ]


def test_check_layer_integrity_reports_missing_raw_targets_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_json(
        tmp_path / "normalized" / "record.json",
        {"provenance": {"raw_refs": [{"path": "raw/claude/missing.jsonl"}]}},
    )
    compiled_path = tmp_path / "compiled" / "topic.md"
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text("# Topic\n", encoding="utf-8")
    monkeypatch.setattr(
        integrity,
        "find_stale_wikilinks",
        lambda base: [
            {
                "code": "L201",
                "check": "graph.broken_wikilink",
                "severity": "warning",
                "path": "compiled/topic.md",
                "message": "stale",
            }
        ],
    )
    monkeypatch.setattr(
        integrity,
        "find_orphaned_compiled_pages",
        lambda base: [
            {
                "code": "L202",
                "check": "graph.orphan_compiled_page",
                "severity": "warning",
                "path": "compiled/topic.md",
                "message": "orphaned",
            }
        ],
    )

    result = integrity.check_layer_integrity(tmp_path)

    assert result["error_count"] == 2
    assert result["issues"] == [
        {
            "code": "L102",
            "check": "integrity.raw_target",
            "severity": "error",
            "path": "normalized/record.json",
            "message": "raw provenance target missing: raw/claude/missing.jsonl",
        },
        {
            "code": "L104",
            "check": "integrity.index_manifest",
            "severity": "error",
            "path": "index/manifest.json",
            "message": "index manifest missing for compiled layer",
        },
        {
            "code": "L201",
            "check": "graph.broken_wikilink",
            "severity": "warning",
            "path": "compiled/topic.md",
            "message": "stale",
        },
        {
            "code": "L202",
            "check": "graph.orphan_compiled_page",
            "severity": "warning",
            "path": "compiled/topic.md",
            "message": "orphaned",
        },
    ]


def test_check_layer_integrity_reports_invalid_index_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled_path = tmp_path / "compiled" / "topic.md"
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text("# Topic\n", encoding="utf-8")
    _write_json(tmp_path / "index" / "manifest.json", [])
    monkeypatch.setattr(integrity, "find_stale_wikilinks", lambda base: [])
    monkeypatch.setattr(integrity, "find_orphaned_compiled_pages", lambda base: [])
    result = integrity.check_layer_integrity(tmp_path)

    assert len(result["issues"]) == 1
    issue = result["issues"][0]
    assert issue["code"] == "L104"
    assert issue["check"] == "integrity.index_manifest"
    assert issue["severity"] == "error"
    assert issue["path"] == "index/manifest.json"
    assert issue["message"] == "index manifest is invalid; rebuild required"
    assert issue["reasons"][0]["field_path"] == "content_identity"
    assert issue["reasons"][0]["manifest_value"] == "invalid"
    assert set(issue["reasons"][0]["current_value"]) == {
        "normalized",
        "compiled",
        "tokenizer",
    }


def test_check_layer_integrity_reports_stale_index_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled_path = tmp_path / "compiled" / "topic.md"
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text("# Topic\n", encoding="utf-8")
    paths = StoragePaths(tmp_path)
    retrieval_identity = retrieval_identity_for_tokenizer(current_runtime_tokenizer_name())
    current = current_index_identity(paths, retrieval_identity)
    stale_manifest = IndexManifest(
        schema_version=1,
        records_indexed=0,
        pages_indexed=1,
        search_documents=1,
        compiled_paths=("compiled/topic.md",),
        identity=current_index_identity(paths, retrieval_identity),
    )
    stale_manifest = IndexManifest(
        schema_version=stale_manifest.schema_version,
        records_indexed=stale_manifest.records_indexed,
        pages_indexed=stale_manifest.pages_indexed,
        search_documents=stale_manifest.search_documents,
        compiled_paths=stale_manifest.compiled_paths,
        identity=type(current)(
            normalized=current.normalized,
            compiled=type(current.compiled)(
                latest_mtime_ns=current.compiled.latest_mtime_ns,
                file_count=current.compiled.file_count,
                content_hash="stale",
            ),
            retrieval=current.retrieval,
        ),
    )
    write_index_manifest(paths, stale_manifest)
    monkeypatch.setattr(integrity, "find_stale_wikilinks", lambda base: [])
    monkeypatch.setattr(integrity, "find_orphaned_compiled_pages", lambda base: [])

    result = integrity.check_layer_integrity(tmp_path)

    assert result["issues"] == []


def test_check_layer_integrity_accepts_top_level_raw_ref_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_path = tmp_path / "raw" / "claude" / "fixture.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}\n", encoding="utf-8")
    _write_json(
        tmp_path / "normalized" / "record.json",
        {"raw_ref": {"path": "raw/claude/fixture.jsonl"}},
    )
    monkeypatch.setattr(integrity, "find_stale_wikilinks", lambda base: [])
    monkeypatch.setattr(integrity, "find_orphaned_compiled_pages", lambda base: [])

    result = integrity.check_layer_integrity(tmp_path)

    assert not any(issue["code"] == "L101" for issue in result["issues"])


def test_check_layer_integrity_returns_clean_result_for_healthy_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_path = tmp_path / "raw" / "claude" / "fixture.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}\n", encoding="utf-8")
    _write_json(
        tmp_path / "normalized" / "record.json",
        {"provenance": {"raw_refs": [{"path": "raw/claude/fixture.jsonl"}]}},
    )
    compiled_path = tmp_path / "compiled" / "topic.md"
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text("# Topic\n", encoding="utf-8")
    paths = StoragePaths(tmp_path)
    current = current_index_identity(
        paths,
        retrieval_identity_for_tokenizer(current_runtime_tokenizer_name()),
    )
    write_index_manifest(
        paths,
        IndexManifest(
            schema_version=1,
            records_indexed=1,
            pages_indexed=1,
            search_documents=1,
            compiled_paths=("compiled/topic.md",),
            identity=current,
        ),
    )
    monkeypatch.setattr(integrity, "find_stale_wikilinks", lambda base: [])
    monkeypatch.setattr(integrity, "find_orphaned_compiled_pages", lambda base: [])

    result = integrity.check_layer_integrity(tmp_path)

    assert result == {"root": tmp_path.as_posix(), "issues": [], "error_count": 0}
