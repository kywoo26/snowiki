"""Phase 1 correctness validation helpers for benchmark runs.

This module ingests benchmark fixtures, validates the workspace, and checks a
small set of canonical queries against expected fixture matches.
"""

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
from snowiki.config import resolve_repo_asset_path
from snowiki.lint.integrity import check_layer_integrity


class FixtureSpec(TypedDict):
    """Specification for a benchmark fixture.

    Attributes:
        fixture_id: Stable identifier for the fixture.
        source: Source system label for the fixture.
        path: Filesystem path to the fixture file.
    """

    fixture_id: str
    source: str
    path: Path


class FixtureResult(TypedDict):
    """Result entry recorded after ingesting a fixture.

    Attributes:
        fixture_id: Stable identifier for the fixture.
        source: Source system label for the fixture.
        root: Workspace root as a string path.
    """

    fixture_id: str
    source: str
    root: str


class ZonesResult(TypedDict):
    """Counts for normalized and compiled zones.

    Attributes:
        normalized: Number of normalized records.
        compiled: Number of compiled records.
    """

    normalized: int
    compiled: int


class IndexManifestResult(TypedDict, total=False):
    """Optional index-manifest fields produced by a status check.

    Attributes:
        compiled_paths: Compiled paths listed in the manifest.
    """

    compiled_paths: list[str]


class StatusResult(TypedDict):
    """Typed status payload returned by the status command.

    Attributes:
        root: Workspace root as a string path.
        zones: Zone counts from the status command.
        index_manifest: Optional compiled-path manifest.
    """

    root: str
    zones: ZonesResult
    index_manifest: IndexManifestResult | None


def _project_benchmark_status(status_payload: dict[str, object]) -> StatusResult:
    """Project the current status payload into the benchmark compatibility shape.

    Args:
        status_payload: Current runtime status payload.

    Returns:
        A benchmark-compatible status payload with legacy zone/manifest fields.
    """
    manifest_path = Path(str(status_payload["root"])) / "index" / "manifest.json"
    manifest = _load_json(manifest_path) if manifest_path.exists() else None
    compiled_paths: list[str] = []
    if isinstance(manifest, dict):
        raw_compiled_paths = manifest.get("compiled_paths")
        if isinstance(raw_compiled_paths, list):
            compiled_paths = [
                path for path in raw_compiled_paths if isinstance(path, str)
            ]

    sources = cast(dict[str, object], status_payload.get("sources", {}))
    pages = cast(dict[str, object], status_payload.get("pages", {}))

    normalized_count = sources.get("total")
    compiled_count = pages.get("total")

    return {
        "root": str(status_payload["root"]),
        "zones": {
            "normalized": normalized_count if isinstance(normalized_count, int) else 0,
            "compiled": compiled_count if isinstance(compiled_count, int) else 0,
        },
        "index_manifest": {"compiled_paths": compiled_paths} if manifest else None,
    }


class RebuildResult(TypedDict):
    """Typed rebuild payload returned by the rebuild command.

    Attributes:
        root: Workspace root as a string path.
        compiled_count: Number of compiled items.
        compiled_paths: Compiled paths returned by rebuild.
        index_manifest: Path to the generated index manifest.
        records_indexed: Number of indexed records.
        pages_indexed: Number of indexed pages.
    """

    root: str
    compiled_count: int
    compiled_paths: list[str]
    index_manifest: str
    records_indexed: int
    pages_indexed: int


class FailureResult(TypedDict):
    """Flattened failure entry used by phase 1 validation.

    Attributes:
        stage: Validation stage name.
        code: Failure code.
        path: Related path or query identifier.
        message: Human-readable failure message.
    """

    stage: str
    code: str
    path: str
    message: str


class QueryExpectation(TypedDict):
    """Expected query outcome for the phase 1 correctness flow.

    Attributes:
        query_id: Query identifier.
        text: Query text.
        expected_ids: Expected fixture IDs.
        matched_ids: Fixture IDs matched by the query.
        ok: Whether the match set is correct.
    """

    query_id: str
    text: str
    expected_ids: list[str]
    matched_ids: list[str]
    ok: bool


class BaseCheckIssue(TypedDict):
    """Common fields for lint and integrity issues.

    Attributes:
        code: Issue code.
        severity: Issue severity string.
        path: Related filesystem path.
        message: Human-readable description.
    """

    code: str
    severity: str
    path: str
    message: str


class CheckIssue(BaseCheckIssue, total=False):
    """Lint or integrity issue with an optional target field.

    Attributes:
        target: Optional target path or identifier associated with the issue.
    """

    target: str


class CheckResult(TypedDict):
    """Typed result for lint or integrity checks.

    Attributes:
        root: Workspace root as a string path.
        issues: Issues returned by the check.
        error_count: Number of error-severity issues.
    """

    root: str
    issues: list[CheckIssue]
    error_count: int


_BENCH_LINT_CHECKS: frozenset[str] = frozenset(
    {
        "normalized.required_key",
        "normalized.invalid_json",
        "normalized.invalid_payload",
        "compiled.frontmatter",
    }
)


def _project_check_issue(issue: dict[str, object]) -> CheckIssue:
    """Project a lint or integrity issue into the benchmark result shape."""
    projected: CheckIssue = {
        "code": str(issue["code"]),
        "severity": str(issue["severity"]),
        "path": str(issue["path"]),
        "message": str(issue["message"]),
    }
    target = issue.get("target")
    if isinstance(target, str):
        projected["target"] = target
    return projected


def _project_benchmark_check_result(
    raw_result: dict[str, object], *, allowed_checks: frozenset[str] | None = None
) -> CheckResult:
    """Project current lint/integrity output into the benchmark compatibility shape.

    Args:
        raw_result: Current runtime lint or integrity result.
        allowed_checks: Optional allowlist of check names to retain.

    Returns:
        A benchmark-compatible result containing error-only projected issues.
    """
    raw_issues = raw_result.get("issues", [])
    issues: list[CheckIssue] = []
    if isinstance(raw_issues, list):
        for raw_issue in raw_issues:
            if not isinstance(raw_issue, dict):
                continue
            issue = cast(dict[str, object], raw_issue)
            if issue.get("severity") != "error":
                continue
            raw_check = issue.get("check")
            if allowed_checks is not None and raw_check not in allowed_checks:
                continue
            issues.append(_project_check_issue(issue))
    return {
        "root": str(raw_result["root"]),
        "issues": issues,
        "error_count": len(issues),
    }


class Phase1FlowResult(TypedDict):
    """Complete result payload for the phase 1 correctness flow.

    Attributes:
        ok: Whether the entire flow passed.
        root: Workspace root as a string path.
        fixtures: Ingest results for each fixture.
        rebuild: Rebuild result payload.
        status: Status result payload.
        lint: Lint check result payload.
        integrity: Integrity check result payload.
        queries: Query expectations and matches.
        failures: Flattened failure list.
    """

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
    """Validation-only result payload for a benchmark workspace.

    Attributes:
        ok: Whether validation passed.
        status: Status result payload.
        lint: Lint check result payload.
        integrity: Integrity check result payload.
        failures: Flattened failure list.
    """

    ok: bool
    status: StatusResult
    lint: CheckResult
    integrity: CheckResult
    failures: list[FailureResult]


_FIXTURES: tuple[FixtureSpec, ...] = (
    {
        "fixture_id": "claude_basic",
        "source": "claude",
        "path": resolve_repo_asset_path("fixtures/claude/basic.jsonl"),
    },
    {
        "fixture_id": "omo_basic",
        "source": "opencode",
        "path": resolve_repo_asset_path("fixtures/opencode/basic.db"),
    },
)
_PHASE_1_QUERY_IDS: tuple[str, ...] = ("ko-001", "mix-001")


def _load_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _load_phase_1_queries() -> list[dict[str, object]]:
    corpus_path = resolve_repo_asset_path(PHASE_1_CORPUS["queries"])
    payload = _load_json(corpus_path)
    entries = cast(list[dict[str, object]], payload["queries"])
    selected = [
        entry for entry in entries if str(entry.get("id")) in _PHASE_1_QUERY_IDS
    ]
    selected.sort(key=lambda entry: _PHASE_1_QUERY_IDS.index(str(entry["id"])))
    return selected


def _load_phase_1_judgments() -> dict[str, list[str]]:
    corpus_path = resolve_repo_asset_path(PHASE_1_CORPUS["judgments"])
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
    """Validate the phase 1 benchmark workspace.

    Args:
        root: Workspace root as a filesystem path.

    Returns:
        A validation result containing status, lint, integrity, and failures.
    """
    status = _project_benchmark_status(run_status(root))
    lint = _project_benchmark_check_result(
        cast(dict[str, object], cast(object, run_lint(root))),
        allowed_checks=_BENCH_LINT_CHECKS,
    )
    integrity = _project_benchmark_check_result(
        cast(dict[str, object], cast(object, check_layer_integrity(root)))
    )
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
    """Run the full phase 1 correctness flow.

    Args:
        root: Workspace root as a filesystem path.

    Returns:
        A complete phase 1 correctness result payload.
    """
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
