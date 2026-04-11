from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypedDict, cast

from snowiki.bench.contract import PHASE_1_CORPUS
from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.lint import run_lint
from snowiki.cli.commands.query import QueryResult, run_query
from snowiki.cli.commands.rebuild import run_rebuild
from snowiki.cli.commands.status import run_status
from snowiki.compiler.engine import CompilerEngine
from snowiki.lint.integrity import check_layer_integrity


class FixtureSpec(TypedDict):
    fixture_id: str
    source: str
    path: Path


class FixtureResult(TypedDict):
    fixture_id: str
    source: str
    root: str


class ZonesResult(TypedDict):
    normalized: int
    compiled: int


class IndexManifestResult(TypedDict, total=False):
    compiled_paths: list[str]


class StatusResult(TypedDict):
    root: str
    zones: ZonesResult
    index_manifest: IndexManifestResult | None


class RebuildResult(TypedDict):
    root: str
    compiled_count: int
    compiled_paths: list[str]
    index_manifest: str
    records_indexed: int
    pages_indexed: int


class FailureResult(TypedDict):
    stage: str
    code: str
    path: str
    message: str


class QueryExpectation(TypedDict):
    query_id: str
    text: str
    expected_ids: list[str]
    matched_ids: list[str]
    ok: bool


class BaseCheckIssue(TypedDict):
    code: str
    severity: str
    path: str
    message: str


class CheckIssue(BaseCheckIssue, total=False):
    target: str


class CheckResult(TypedDict):
    root: str
    issues: list[CheckIssue]
    error_count: int


class Phase1FlowResult(TypedDict):
    ok: bool
    root: str
    fixtures: list[FixtureResult]
    rebuild: RebuildResult
    status: StatusResult
    lint: CheckResult
    integrity: CheckResult
    queries: list[QueryExpectation]
    failures: list[FailureResult]


class ValidationResult(TypedDict):
    ok: bool
    status: StatusResult
    lint: CheckResult
    integrity: CheckResult
    failures: list[FailureResult]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES: tuple[FixtureSpec, ...] = (
    {
        "fixture_id": "claude_basic",
        "source": "claude",
        "path": _REPO_ROOT / "fixtures" / "claude" / "basic.jsonl",
    },
    {
        "fixture_id": "omo_basic",
        "source": "opencode",
        "path": _REPO_ROOT / "fixtures" / "opencode" / "basic.db",
    },
)
_PHASE_1_QUERY_IDS: tuple[str, ...] = ("en-001", "en-008")


def _load_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _load_phase_1_queries() -> list[dict[str, object]]:
    corpus_path = _REPO_ROOT / PHASE_1_CORPUS["queries"]
    payload = _load_json(corpus_path)
    entries = cast(list[dict[str, object]], payload["queries"])
    selected = [
        entry for entry in entries if str(entry.get("id")) in _PHASE_1_QUERY_IDS
    ]
    selected.sort(key=lambda entry: _PHASE_1_QUERY_IDS.index(str(entry["id"])))
    return selected


def _load_phase_1_judgments() -> dict[str, list[str]]:
    corpus_path = _REPO_ROOT / PHASE_1_CORPUS["judgments"]
    payload = _load_json(corpus_path)
    judgments = cast(dict[str, list[str]], payload["judgments"])
    return {query_id: list(judgments[query_id]) for query_id in _PHASE_1_QUERY_IDS}


def _fixture_sources() -> dict[str, str]:
    return {
        fixture["path"].resolve().as_posix(): fixture["fixture_id"]
        for fixture in _FIXTURES
    }


def _fixture_digests() -> dict[str, str]:
    return {
        hashlib.sha256(fixture["path"].read_bytes()).hexdigest(): fixture["fixture_id"]
        for fixture in _FIXTURES
    }


def _record_fixture_lookup(root: Path) -> dict[str, str]:
    fixture_sources = _fixture_sources()
    fixture_digests = _fixture_digests()
    lookup: dict[str, str] = {}
    for path in sorted(
        (root / "normalized").rglob("*.json"), key=lambda item: item.as_posix()
    ):
        payload = _load_json(path)
        record_id = payload.get("id")
        if not isinstance(record_id, str):
            continue
        fixture_id: str | None = None
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            metadata_dict = cast(dict[str, object], metadata)
            source_path = metadata_dict.get("source_path")
            if isinstance(source_path, str):
                fixture_id = fixture_sources.get(Path(source_path).resolve().as_posix())
        if fixture_id is None:
            raw_ref = payload.get("raw_ref")
            if isinstance(raw_ref, dict):
                raw_ref_dict = cast(dict[str, object], raw_ref)
                sha256 = raw_ref_dict.get("sha256")
                if isinstance(sha256, str):
                    fixture_id = fixture_digests.get(sha256)
        if fixture_id is not None:
            lookup[record_id] = fixture_id
    return lookup


def _page_fixture_lookup(root: Path, record_lookup: dict[str, str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for page in CompilerEngine(root).build_pages():
        fixture_ids = {
            record_lookup[record_id]
            for record_id in page.record_ids
            if record_id in record_lookup
        }
        if len(fixture_ids) == 1:
            lookup[page.path] = next(iter(fixture_ids))
    return lookup


def _hit_fixture_lookup(root: Path) -> dict[str, str]:
    record_lookup = _record_fixture_lookup(root)
    return {**record_lookup, **_page_fixture_lookup(root, record_lookup)}


def _flatten_check_failures(
    stage: str, issues: list[CheckIssue]
) -> list[FailureResult]:
    return [
        {
            "stage": stage,
            "code": issue["code"],
            "path": issue["path"],
            "message": issue["message"],
        }
        for issue in issues
        if issue.get("severity") == "error"
    ]


def _query_failures(expectations: list[QueryExpectation]) -> list[FailureResult]:
    failures: list[FailureResult] = []
    for expectation in expectations:
        if expectation["ok"]:
            continue
        failures.append(
            {
                "stage": "query",
                "code": "Q001",
                "path": expectation["query_id"],
                "message": (
                    "expected ids "
                    f"{expectation['expected_ids']} but matched {expectation['matched_ids']}"
                ),
            }
        )
    return failures


def _collect_matches(
    query_result: QueryResult,
    expected_ids: list[str],
    *,
    hit_lookup: dict[str, str],
) -> list[str]:
    expected = set(expected_ids)
    matched_ids: list[str] = []
    for hit in query_result["hits"]:
        fixture_id = hit_lookup.get(hit["id"])
        if fixture_id not in expected or fixture_id in matched_ids:
            continue
        matched_ids.append(fixture_id)
    return matched_ids


def _run_phase_1_queries(root: Path) -> list[QueryExpectation]:
    judgments = _load_phase_1_judgments()
    hit_lookup = _hit_fixture_lookup(root)
    expectations: list[QueryExpectation] = []
    for query_entry in _load_phase_1_queries():
        query_id = str(query_entry["id"])
        text = str(query_entry["text"])
        expected_ids = judgments[query_id]
        result = run_query(root, text, mode="lexical", top_k=5)
        matched_ids = _collect_matches(result, expected_ids, hit_lookup=hit_lookup)
        expectations.append(
            {
                "query_id": query_id,
                "text": text,
                "expected_ids": expected_ids,
                "matched_ids": matched_ids,
                "ok": matched_ids == expected_ids,
            }
        )
    return expectations


def validate_phase1_workspace(root: Path) -> ValidationResult:
    status = cast(StatusResult, cast(object, run_status(root)))
    lint = cast(CheckResult, cast(object, run_lint(root)))
    integrity = cast(CheckResult, cast(object, check_layer_integrity(root)))
    failures = [
        *_flatten_check_failures("lint", lint["issues"]),
        *_flatten_check_failures("integrity", integrity["issues"]),
    ]
    return {
        "ok": not failures,
        "status": status,
        "lint": lint,
        "integrity": integrity,
        "failures": failures,
    }


def run_phase1_correctness_flow(root: Path) -> Phase1FlowResult:
    fixtures: list[FixtureResult] = []
    for fixture in _FIXTURES:
        _ = run_ingest(fixture["path"], source=fixture["source"], root=root)
        fixtures.append(
            {
                "fixture_id": fixture["fixture_id"],
                "source": fixture["source"],
                "root": root.as_posix(),
            }
        )

    rebuild = cast(RebuildResult, cast(object, run_rebuild(root)))
    validation = validate_phase1_workspace(root)
    queries = _run_phase_1_queries(root)
    failures = [*validation["failures"], *_query_failures(queries)]
    return {
        "ok": not failures,
        "root": root.as_posix(),
        "fixtures": fixtures,
        "rebuild": rebuild,
        "status": validation["status"],
        "lint": validation["lint"],
        "integrity": validation["integrity"],
        "queries": queries,
        "failures": failures,
    }
