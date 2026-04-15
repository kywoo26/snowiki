from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

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


class LintIssue(TypedDict):
    code: str
    check: str
    severity: Severity
    path: str
    message: str
    field: NotRequired[str]
    target: NotRequired[str]


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
        ("compiled.frontmatter", "Compiled page frontmatter", "error"),
        ("integrity.raw_provenance", "Normalized raw provenance", "error"),
        ("integrity.raw_target", "Raw provenance targets", "error"),
        ("integrity.compiled_layer", "Compiled layer presence", "error"),
        ("integrity.index_manifest", "Index manifest presence", "error"),
        ("graph.broken_wikilink", "Broken compiled wikilinks", "error"),
        ("graph.orphan_compiled_page", "Orphan compiled pages", "warning"),
    ]
    counts = {name: 0 for name, _, _ in order}
    for issue in issues:
        check_name = issue.get("check")
        if isinstance(check_name, str) and check_name in counts:
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
