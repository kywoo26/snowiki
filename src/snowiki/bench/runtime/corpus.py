from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict, cast

from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.rebuild import run_rebuild
from snowiki.config import resolve_repo_asset_path
from snowiki.storage import StorageEngine

from ..reporting.models import AuditSample, BenchmarkAssetManifest, PooledReview

CANONICAL_BENCHMARK_FIXTURE_PATHS: dict[str, str] = {
    "claude_basic": "fixtures/claude/basic.jsonl",
    "claude_tools": "fixtures/claude/with_tools.jsonl",
    "claude_attachments": "fixtures/claude/with_attachments.jsonl",
    "claude_sidechains": "fixtures/claude/with_sidechains.jsonl",
    "claude_resumed": "fixtures/claude/resumed.jsonl",
    "claude_large_output": "fixtures/claude/large_output.jsonl",
    "claude_secret": "fixtures/claude/secret_bearing.jsonl",
    "omo_basic": "fixtures/opencode/basic.db",
    "omo_todos": "fixtures/opencode/with_todos.db",
    "omo_diffs": "fixtures/opencode/with_diffs.db",
    "omo_reasoning": "fixtures/opencode/with_reasoning.db",
    "omo_compaction": "fixtures/opencode/with_compaction.db",
}

type BenchmarkCorpusTier = Literal["official_suite", "regression_harness"]


@dataclass(frozen=True)
class BenchmarkFixture:
    fixture_id: str
    source: str
    path: Path


class SeededFixture(TypedDict):
    fixture_id: str
    source: str
    path: str


@dataclass(frozen=True)
class BenchmarkCorpusManifest:
    tier: BenchmarkCorpusTier
    documents: list[dict[str, object]]
    queries: list[dict[str, object]] | None = None
    judgments: dict[str, list[dict[str, object]]] | None = None
    queries_path: str | None = None
    judgments_path: str | None = None
    fixture_paths: dict[str, str] | None = None
    dataset_id: str | None = None
    dataset_name: str | None = None
    dataset_description: str | None = None
    dataset_metadata: dict[str, object] | None = None
    corpus_assets: tuple[BenchmarkAssetManifest, ...] = ()
    query_assets: tuple[BenchmarkAssetManifest, ...] = ()
    judgment_assets: tuple[BenchmarkAssetManifest, ...] = ()
    pooled_reviews: tuple[PooledReview, ...] = ()
    audit_samples: tuple[AuditSample, ...] = ()
    review_policy: dict[str, object] | None = None
    audit_policy: dict[str, object] | None = None


def canonical_benchmark_fixtures() -> tuple[BenchmarkFixture, ...]:
    return tuple(
        BenchmarkFixture(
            fixture_id=fixture_id,
            source="claude" if relative_path.endswith(".jsonl") else "opencode",
            path=resolve_repo_asset_path(relative_path),
        )
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    )


def _fixture_source(relative_path: str) -> str:
    return "claude" if relative_path.endswith(".jsonl") else "opencode"


def _benchmark_fixtures_from_paths(
    fixture_paths: dict[str, str],
) -> tuple[BenchmarkFixture, ...]:
    return tuple(
        BenchmarkFixture(
            fixture_id=fixture_id,
            source=_fixture_source(relative_path),
            path=resolve_repo_asset_path(relative_path),
        )
        for fixture_id, relative_path in fixture_paths.items()
    )


def _seed_fixtures(
    fixtures: tuple[BenchmarkFixture, ...], *, root: Path
) -> list[SeededFixture]:
    for fixture in fixtures:
        _ = run_ingest(fixture.path, source=fixture.source, root=root)
    return [
        {
            "fixture_id": fixture.fixture_id,
            "source": fixture.source,
            "path": fixture.path.as_posix(),
        }
        for fixture in fixtures
    ]


def _manifest_source_type(tier: BenchmarkCorpusTier) -> str:
    return f"benchmark_manifest_{tier}"


def _document_record_payload(
    document: dict[str, object], *, tier: BenchmarkCorpusTier
) -> tuple[str, str, dict[str, object], str]:
    document_id = str(document.get("id", "")).strip()
    if not document_id:
        raise ValueError("benchmark manifest documents must include a non-empty 'id'")

    content = document.get("content")
    if not isinstance(content, str):
        raise ValueError(
            f"benchmark manifest document '{document_id}' must include string 'content'"
        )

    raw_metadata = document.get("metadata")
    metadata = (
        {str(key): value for key, value in cast(dict[object, object], raw_metadata).items()}
        if isinstance(raw_metadata, dict)
        else {}
    )
    recorded_at_value = metadata.get("recorded_at")
    recorded_at = (
        str(recorded_at_value)
        if isinstance(recorded_at_value, str) and recorded_at_value.strip()
        else "2026-01-01T00:00:00Z"
    )
    title_value = metadata.get("title")
    summary_value = metadata.get("summary")
    title = str(title_value).strip() if isinstance(title_value, str) else document_id
    summary = (
        str(summary_value).strip()
        if isinstance(summary_value, str) and summary_value.strip()
        else f"Benchmark corpus document `{document_id}` from the {tier} corpus."
    )
    payload_metadata: dict[str, object] = {
        **metadata,
        "benchmark_tier": tier,
        "document_id": document_id,
    }
    payload: dict[str, object] = {
        "title": title,
        "summary": summary,
        "content": content,
        "metadata": payload_metadata,
    }
    return document_id, content, payload, recorded_at


def _seed_manifest_documents(
    documents: list[dict[str, object]], *, tier: BenchmarkCorpusTier, root: Path
) -> list[SeededFixture]:
    storage = StorageEngine(root)
    source_type = _manifest_source_type(tier)
    seeded: list[SeededFixture] = []
    for document in documents:
        document_id, content, payload, recorded_at = _document_record_payload(
            document, tier=tier
        )
        stored = storage.ingest_record(
            source_type=source_type,
            source_name=f"{document_id}.txt",
            content=content.encode("utf-8"),
            record_type="session",
            payload=payload,
            recorded_at=recorded_at,
            identity_key=f"benchmark-manifest:{tier}:{document_id}",
            record_id=document_id,
        )
        seeded.append(
            {
                "fixture_id": document_id,
                "source": source_type,
                "path": str(cast(object, stored["path"])),
            }
        )
    return seeded


def load_corpus_from_manifest(
    manifest: BenchmarkCorpusManifest, root: Path
) -> list[SeededFixture]:
    seeded: list[SeededFixture] = []
    if manifest.fixture_paths:
        seeded.extend(
            _seed_fixtures(
                _benchmark_fixtures_from_paths(manifest.fixture_paths),
                root=root,
            )
        )
    if manifest.documents:
        seeded.extend(
            _seed_manifest_documents(manifest.documents, tier=manifest.tier, root=root)
        )
    if not seeded:
        raise ValueError(
            "benchmark corpus manifest must define fixture_paths or documents"
        )
    _ = run_rebuild(root)
    return seeded


def seed_canonical_benchmark_root(root: Path) -> list[SeededFixture]:
    return load_corpus_from_manifest(
        BenchmarkCorpusManifest(
            tier="regression_harness",
            documents=[],
            fixture_paths=CANONICAL_BENCHMARK_FIXTURE_PATHS,
        ),
        root,
    )
