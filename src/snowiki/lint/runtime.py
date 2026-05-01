from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

from snowiki.compiler.paths import summary_path_for_record
from snowiki.compiler.taxonomy import NormalizedRecord
from snowiki.gardening.sources import collect_source_gardening_proposals
from snowiki.markdown.source_state import collect_markdown_source_state
from snowiki.search.workspace import current_runtime_tokenizer_name
from snowiki.storage.index_manifest import (
    compare_index_identity,
    current_index_identity,
    load_index_manifest,
    to_lint_issue_payload,
)
from snowiki.storage.provenance import raw_refs_from_record
from snowiki.storage.zones import StoragePaths, ensure_utc_datetime

from .integrity import check_layer_integrity

Severity = Literal["error", "warning", "info"]

_SEVERITY_ORDER: dict[Severity, int] = {"error": 0, "warning": 1, "info": 2}
_NORMALIZED_REQUIRED_KEYS = ("id", "source_type", "record_type")
_COMPILED_FRONTMATTER_REQUIRED_KEYS = (
    "title",
    "type",
    "created",
    "updated",
    "summary",
    "sources",
    "related",
    "tags",
    "record_ids",
)
_FRONTMATTER_KEY_PATTERN = re.compile(r"^(?P<key>[A-Za-z0-9_]+):", re.MULTILINE)
_FRONTMATTER_FIELD_PATTERN = re.compile(
    r"^(?P<key>[A-Za-z0-9_]+):\s*(?P<value>.*)$", re.MULTILINE
)
_STALE_PAGE_MAX_AGE = timedelta(days=30)
_SOURCE_FRESHNESS_ISSUES: dict[str, tuple[str, str, Severity, str]] = {
    "modified": (
        "L501",
        "source.modified",
        "warning",
        "source file changed since ingest",
    ),
    "missing": ("L502", "source.missing", "warning", "source file is missing"),
    "untracked": (
        "L503",
        "source.untracked",
        "info",
        "source file has not been ingested",
    ),
    "invalid": (
        "L504",
        "source.invalid_metadata",
        "warning",
        "source metadata is invalid",
    ),
}


class LintIssue(TypedDict):
    code: str
    check: str
    severity: Severity
    path: str
    message: str
    field: NotRequired[str]
    target: NotRequired[str]
    proposal_id: NotRequired[str]
    proposal_type: NotRequired[str]
    recommended_action: NotRequired[str]
    evidence: NotRequired[list[object]]


class LintCheck(TypedDict):
    name: str
    label: str
    severity: Severity
    issue_count: int


class LintResult(TypedDict):
    root: str
    summary: dict[str, int]
    checks: list[LintCheck]
    issues: list[LintIssue]
    error_count: int


def _make_issue(
    *,
    code: str,
    check: str,
    severity: Severity,
    path: str,
    message: str,
    field: str | None = None,
    target: str | None = None,
) -> LintIssue:
    issue: LintIssue = {
        "code": code,
        "check": check,
        "severity": severity,
        "path": path,
        "message": message,
    }
    if field is not None:
        issue["field"] = field
    if target is not None:
        issue["target"] = target
    return issue


def _extract_frontmatter_keys(text: str) -> set[str]:
    if not text.startswith("---\n"):
        return set()
    delimiter_index = text.find("\n---\n", 4)
    if delimiter_index == -1:
        return set()
    block = text[4:delimiter_index]
    return {match.group("key") for match in _FRONTMATTER_KEY_PATTERN.finditer(block)}


def _extract_frontmatter_values(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    delimiter_index = text.find("\n---\n", 4)
    if delimiter_index == -1:
        return {}
    block = text[4:delimiter_index]
    values: dict[str, str] = {}
    for match in _FRONTMATTER_FIELD_PATTERN.finditer(block):
        value = match.group("value").strip()
        values[match.group("key")] = value.strip('"').strip("'")
    return values


def _load_normalized_record(path: Path, root: Path) -> NormalizedRecord | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None

    def _string_field(key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        return None

    record_id = _string_field("id")
    source_type = _string_field("source_type")
    record_type = _string_field("record_type")
    recorded_at = _string_field("recorded_at")
    if (
        record_id is None
        or source_type is None
        or record_type is None
        or recorded_at is None
    ):
        return None
    return NormalizedRecord(
        id=record_id,
        path=path.relative_to(root).as_posix(),
        source_type=source_type,
        record_type=record_type,
        recorded_at=recorded_at,
        payload=payload,
        raw_refs=raw_refs_from_record(payload),
    )


def collect_freshness_issues(root: str | Path) -> list[LintIssue]:
    base = Path(root)
    issues: list[LintIssue] = []
    paths = StoragePaths(base)
    try:
        manifest = load_index_manifest(paths)
        manifest_for_comparison = manifest
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        manifest_for_comparison = "invalid"
    explanation = compare_index_identity(
        manifest_for_comparison,
        current_index_identity(paths, current_runtime_tokenizer_name()),
    )
    if explanation.status == "stale":
        issues.extend(cast(list[LintIssue], to_lint_issue_payload(explanation)))
    cutoff = datetime.now(tz=UTC) - _STALE_PAGE_MAX_AGE
    for path in sorted(
        (base / "compiled").rglob("*.md"), key=lambda item: item.as_posix()
    ):
        frontmatter = _extract_frontmatter_values(path.read_text(encoding="utf-8"))
        updated = frontmatter.get("updated") or frontmatter.get("created")
        if not updated:
            continue
        try:
            updated_at = ensure_utc_datetime(updated)
        except ValueError:
            continue
        if updated_at >= cutoff:
            continue
        issues.append(
            _make_issue(
                code="L401",
                check="freshness.stale_compiled_page",
                severity="info",
                path=path.relative_to(base).as_posix(),
                message=f"compiled page has not been updated since {updated_at.date().isoformat()}",
            )
        )
    return issues


def collect_source_freshness_issues(root: str | Path) -> list[LintIssue]:
    base = Path(root)
    issues: list[LintIssue] = []
    report = collect_markdown_source_state(base)
    for item in report["items"]:
        issue_spec = _SOURCE_FRESHNESS_ISSUES.get(item["state"])
        if issue_spec is None:
            continue
        code, check, severity, message = issue_spec
        issues.append(
            _make_issue(
                code=code,
                check=check,
                severity=severity,
                path=item.get("normalized_path", item["source_path"]),
                message=f"{message}: {item['relative_path']}",
                target=item["source_path"] if item["state"] != "untracked" else item["source_root"],
            )
        )
    return issues


def collect_source_gardening_issues(root: str | Path) -> list[LintIssue]:
    """Return agent-readable source gardening proposal diagnostics."""
    issues: list[LintIssue] = []
    report = collect_source_gardening_proposals(root)
    for proposal in report["proposals"]:
        if proposal["proposal_type"] != "source_rename_candidate":
            continue
        missing_evidence = next(
            evidence
            for evidence in proposal["evidence"]
            if evidence["kind"] == "missing_record"
        )
        untracked_evidence = next(
            evidence
            for evidence in proposal["evidence"]
            if evidence["kind"] == "untracked_source"
        )
        issue = _make_issue(
            code="L505",
            check="source.rename_candidate",
            severity="info",
            path=str(missing_evidence.get("normalized_path", missing_evidence["source_path"])),
            message=(
                "missing source has an exact-hash untracked rename candidate: "
                f"{missing_evidence['relative_path']} -> {untracked_evidence['relative_path']}"
            ),
            target=untracked_evidence["source_path"],
        )
        issue["proposal_id"] = proposal["proposal_id"]
        issue["proposal_type"] = proposal["proposal_type"]
        issue["recommended_action"] = proposal["recommended_action"]
        issue["evidence"] = list(proposal["evidence"])
        issues.append(issue)
    return issues


def collect_summary_coverage_issues(root: str | Path) -> list[LintIssue]:
    base = Path(root)
    issues: list[LintIssue] = []
    for path in sorted(
        (base / "normalized").rglob("*.json"), key=lambda item: item.as_posix()
    ):
        try:
            record = _load_normalized_record(path, base)
        except json.JSONDecodeError:
            continue
        if record is None:
            continue
        try:
            summary_path = summary_path_for_record(record)
        except ValueError:
            continue
        if (base / summary_path).exists():
            continue
        issues.append(
            _make_issue(
                code="L402",
                check="coverage.source_without_summary",
                severity="info",
                path=record.path,
                message=f"normalized record is missing compiled summary page: {summary_path}",
                target=summary_path,
            )
        )
    return issues


def collect_structural_issues(root: str | Path) -> list[LintIssue]:
    base = Path(root)
    issues: list[LintIssue] = []

    for path in sorted(
        (base / "normalized").rglob("*.json"), key=lambda item: item.as_posix()
    ):
        relative_path = path.relative_to(base).as_posix()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                _make_issue(
                    code="L010",
                    check="normalized.invalid_json",
                    severity="error",
                    path=relative_path,
                    message=f"normalized record is not valid JSON: {exc}",
                )
            )
            continue

        if not isinstance(payload, dict):
            issues.append(
                _make_issue(
                    code="L011",
                    check="normalized.invalid_payload",
                    severity="error",
                    path=relative_path,
                    message="normalized record must be a JSON object",
                )
            )
            continue

        for key in _NORMALIZED_REQUIRED_KEYS:
            if key in payload:
                continue
            issues.append(
                _make_issue(
                    code="L001",
                    check="normalized.required_key",
                    severity="error",
                    path=relative_path,
                    message=f"normalized record missing required key: {key}",
                    field=key,
                )
            )

        projection = payload.get("projection")
        if not isinstance(projection, Mapping):
            issues.append(
                _make_issue(
                    code="L003",
                    check="normalized.compiler_projection",
                    severity="error",
                    path=relative_path,
                    message="normalized record missing required compiler projection",
                    field="projection",
                )
            )

    for path in sorted(
        (base / "compiled").rglob("*.md"), key=lambda item: item.as_posix()
    ):
        relative_path = path.relative_to(base).as_posix()
        text = path.read_text(encoding="utf-8")
        frontmatter_keys = _extract_frontmatter_keys(text)
        if not frontmatter_keys:
            issues.append(
                _make_issue(
                    code="L002",
                    check="compiled.frontmatter",
                    severity="error",
                    path=relative_path,
                    message="compiled page missing YAML frontmatter",
                )
            )
            continue

        missing_keys = [
            key
            for key in _COMPILED_FRONTMATTER_REQUIRED_KEYS
            if key not in frontmatter_keys
        ]
        for key in missing_keys:
            issues.append(
                _make_issue(
                    code="L002",
                    check="compiled.frontmatter",
                    severity="error",
                    path=relative_path,
                    message=f"compiled page frontmatter missing required key: {key}",
                    field=key,
                )
            )

    return sorted(issues, key=_issue_sort_key)


def _issue_sort_key(issue: LintIssue) -> tuple[int, str, str, str]:
    severity = issue.get("severity", "info")
    return (
        _SEVERITY_ORDER.get(severity, len(_SEVERITY_ORDER)),
        str(issue.get("path", "")),
        str(issue.get("code", "")),
        str(issue.get("message", "")),
    )


def _count_by_severity(issues: list[LintIssue]) -> dict[str, int]:
    return {
        "error": sum(1 for issue in issues if issue.get("severity") == "error"),
        "warning": sum(1 for issue in issues if issue.get("severity") == "warning"),
        "info": sum(1 for issue in issues if issue.get("severity") == "info"),
    }


def _build_checks(issues: list[LintIssue]) -> list[LintCheck]:
    order: list[tuple[str, str, Severity]] = [
        ("normalized.required_key", "Required normalized keys", "error"),
        ("normalized.invalid_json", "Normalized JSON syntax", "error"),
        ("normalized.invalid_payload", "Normalized payload object shape", "error"),
        ("normalized.compiler_projection", "Compiler projection contract", "error"),
        ("compiled.frontmatter", "Compiled page frontmatter", "error"),
        ("integrity.raw_provenance", "Normalized raw provenance", "error"),
        ("integrity.raw_target", "Raw provenance targets", "error"),
        ("integrity.compiled_layer", "Compiled layer presence", "error"),
        ("integrity.index_manifest", "Index manifest presence", "error"),
        ("graph.broken_wikilink", "Broken compiled wikilinks", "error"),
        ("graph.orphan_compiled_page", "Orphan compiled pages", "warning"),
        ("freshness.stale_compiled_page", "Stale compiled pages", "info"),
        ("source.modified", "Modified Markdown sources", "warning"),
        ("source.missing", "Missing Markdown sources", "warning"),
        ("source.rename_candidate", "Markdown source rename candidates", "info"),
        ("source.untracked", "Untracked Markdown sources", "info"),
        ("source.invalid_metadata", "Invalid Markdown source metadata", "warning"),
        ("coverage.source_without_summary", "Sources without summary pages", "info"),
    ]
    counts = {name: 0 for name, _, _ in order}
    for issue in issues:
        check_name = issue["check"]
        if check_name in counts:
            counts[check_name] += 1
    checks: list[LintCheck] = []
    for name, label, severity in order:
        checks.append(
            {
                "name": name,
                "label": label,
                "severity": severity,
                "issue_count": counts[name],
            }
        )
    return checks


def run_lint(root: str | Path) -> LintResult:
    base = Path(root)
    issues = [
        *collect_structural_issues(base),
        *check_layer_integrity(base)["issues"],
        *collect_freshness_issues(base),
        *collect_source_freshness_issues(base),
        *collect_source_gardening_issues(base),
        *collect_summary_coverage_issues(base),
    ]
    sorted_issues = sorted(issues, key=_issue_sort_key)
    severity_counts = _count_by_severity(sorted_issues)
    summary = {**severity_counts, "total": len(sorted_issues)}
    return {
        "root": base.as_posix(),
        "summary": summary,
        "checks": _build_checks(sorted_issues),
        "issues": sorted_issues,
        "error_count": summary["error"],
    }
