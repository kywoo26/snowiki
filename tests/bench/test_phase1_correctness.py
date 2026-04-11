from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypedDict, cast

from click.testing import CliRunner
from snowiki.cli.main import app

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


JSONScalar = None | bool | int | float | str
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject = dict[str, JSONValue]


class FixtureResult(TypedDict):
    fixture_id: str
    source: str
    root: str


class RebuildResult(TypedDict):
    compiled_count: int


class ZonesResult(TypedDict):
    normalized: int
    compiled: int


class IndexManifestResult(TypedDict):
    compiled_paths: list[str]


class StatusResult(TypedDict):
    zones: ZonesResult
    index_manifest: IndexManifestResult


class LintIssue(TypedDict):
    code: str
    severity: str
    path: str
    message: str


class IntegrityIssue(LintIssue, total=False):
    target: str


class CheckResult(TypedDict):
    root: str
    issues: list[LintIssue] | list[IntegrityIssue]
    error_count: int


class QueryExpectation(TypedDict):
    query_id: str
    text: str
    expected_ids: list[str]
    matched_ids: list[str]
    ok: bool


class FailureResult(TypedDict):
    stage: str
    code: str
    path: str
    message: str


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


if TYPE_CHECKING:

    class Phase1Module(Protocol):
        def run_phase1_correctness_flow(self, root: Path) -> Phase1FlowResult: ...

        def validate_phase1_workspace(self, root: Path) -> ValidationResult: ...


def _load_phase1_module() -> Phase1Module:
    module = cast(object, import_module("snowiki.bench.phase1_correctness"))
    return cast("Phase1Module", module)


def _invoke_json(root: Path, args: Sequence[str]) -> JSONObject:
    runner = CliRunner()
    result = runner.invoke(app, args, env={"SNOWIKI_ROOT": str(root)})
    assert result.exit_code == 0, result.output
    return cast(JSONObject, json.loads(result.output))


def _seed_phase1_root(root: Path) -> None:
    _ = _invoke_json(
        root,
        [
            "ingest",
            str(ROOT / "fixtures" / "claude" / "basic.jsonl"),
            "--source",
            "claude",
            "--output",
            "json",
        ],
    )
    _ = _invoke_json(
        root,
        [
            "ingest",
            str(ROOT / "fixtures" / "opencode" / "basic.db"),
            "--source",
            "opencode",
            "--output",
            "json",
        ],
    )
    _ = _invoke_json(root, ["rebuild", "--output", "json"])


def _read_json(path: Path) -> JSONObject:
    return cast(JSONObject, json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: JSONObject) -> None:
    _ = path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _first_normalized_record(root: Path) -> Path:
    return sorted(
        (root / "normalized").rglob("*.json"), key=lambda item: item.as_posix()
    )[0]


def _first_compiled_page(root: Path) -> Path:
    compiled_paths = sorted(
        (root / "compiled").rglob("*.md"), key=lambda item: item.as_posix()
    )
    return next(path for path in compiled_paths if path.name != "overview.md")


def test_run_phase1_correctness_flow_uses_isolated_root_and_known_answers(
    tmp_path: Path,
) -> None:
    phase1 = _load_phase1_module()

    result = phase1.run_phase1_correctness_flow(tmp_path)

    assert result["ok"] is True
    assert result["root"] == tmp_path.as_posix()
    assert [fixture["fixture_id"] for fixture in result["fixtures"]] == [
        "claude_basic",
        "omo_basic",
    ]
    assert [fixture["source"] for fixture in result["fixtures"]] == [
        "claude",
        "opencode",
    ]
    assert all(fixture["root"] == tmp_path.as_posix() for fixture in result["fixtures"])
    assert result["rebuild"]["compiled_count"] >= 3
    assert result["status"]["zones"]["normalized"] >= 2
    assert result["status"]["zones"]["compiled"] >= 1
    assert result["status"]["index_manifest"]["compiled_paths"]
    assert result["lint"] == {
        "root": tmp_path.as_posix(),
        "issues": [],
        "error_count": 0,
    }
    assert result["integrity"] == {
        "root": tmp_path.as_posix(),
        "issues": [],
        "error_count": 0,
    }
    queries = {item["query_id"]: item for item in result["queries"]}
    assert queries["en-001"] == {
        "query_id": "en-001",
        "text": "Which Claude session gives the minimal one-line description of Snowiki as a personal wiki?",
        "expected_ids": ["claude_basic"],
        "matched_ids": ["claude_basic"],
        "ok": True,
    }
    assert queries["en-008"] == {
        "query_id": "en-008",
        "text": "Which OpenCode fixture talks about the fixture inventory contract itself?",
        "expected_ids": ["omo_basic"],
        "matched_ids": ["omo_basic"],
        "ok": True,
    }
    assert result["failures"] == []


def test_validate_phase1_workspace_reports_broken_provenance_and_missing_compiled_layer(
    tmp_path: Path,
) -> None:
    phase1 = _load_phase1_module()
    _seed_phase1_root(tmp_path)

    normalized_path = _first_normalized_record(tmp_path)
    payload = _read_json(normalized_path)
    provenance = cast(JSONObject, payload["provenance"])
    raw_refs = cast(list[JSONObject], provenance["raw_refs"])
    raw_refs[0]["path"] = "raw/claude/missing.jsonl"
    _write_json(normalized_path, payload)
    shutil.rmtree(tmp_path / "compiled")

    result = phase1.validate_phase1_workspace(tmp_path)

    assert result["ok"] is False
    assert result["status"]["zones"]["compiled"] == 0
    assert result["lint"]["error_count"] == 0
    assert result["integrity"]["error_count"] == 2
    assert result["integrity"]["issues"] == [
        {
            "code": "L102",
            "severity": "error",
            "path": normalized_path.relative_to(tmp_path).as_posix(),
            "message": "raw provenance target missing: raw/claude/missing.jsonl",
        },
        {
            "code": "L103",
            "severity": "error",
            "path": "compiled",
            "message": "compiled layer missing for existing normalized records",
        },
    ]
    assert result["failures"] == [
        {
            "stage": "integrity",
            "code": "L102",
            "path": normalized_path.relative_to(tmp_path).as_posix(),
            "message": "raw provenance target missing: raw/claude/missing.jsonl",
        },
        {
            "stage": "integrity",
            "code": "L103",
            "path": "compiled",
            "message": "compiled layer missing for existing normalized records",
        },
    ]


def test_validate_phase1_workspace_reports_stale_compiled_links_and_structural_lint_failures(
    tmp_path: Path,
) -> None:
    phase1 = _load_phase1_module()
    _seed_phase1_root(tmp_path)

    normalized_path = _first_normalized_record(tmp_path)
    normalized_payload = _read_json(normalized_path)
    _ = normalized_payload.pop("id")
    _write_json(normalized_path, normalized_payload)

    compiled_path = _first_compiled_page(tmp_path)
    compiled_text = compiled_path.read_text(encoding="utf-8")
    _ = compiled_path.write_text(
        compiled_text.replace("---\n", "", 1)
        + "\n\nBroken link to [[compiled/missing-page]].\n",
        encoding="utf-8",
    )

    result = phase1.validate_phase1_workspace(tmp_path)

    assert result["ok"] is False
    assert result["lint"]["error_count"] == 2
    assert result["lint"]["issues"] == [
        {
            "code": "L001",
            "severity": "error",
            "path": normalized_path.relative_to(tmp_path).as_posix(),
            "message": "missing required key: id",
        },
        {
            "code": "L002",
            "severity": "error",
            "path": compiled_path.relative_to(tmp_path).as_posix(),
            "message": "compiled page missing YAML frontmatter",
        },
    ]
    assert result["integrity"]["error_count"] == 1
    assert result["integrity"]["issues"] == [
        {
            "code": "L002",
            "severity": "error",
            "path": compiled_path.relative_to(tmp_path).as_posix(),
            "message": "broken wikilink: [[compiled/missing-page]]",
            "target": "compiled/missing-page.md",
        }
    ]
    assert result["failures"] == [
        {
            "stage": "lint",
            "code": "L001",
            "path": normalized_path.relative_to(tmp_path).as_posix(),
            "message": "missing required key: id",
        },
        {
            "stage": "lint",
            "code": "L002",
            "path": compiled_path.relative_to(tmp_path).as_posix(),
            "message": "compiled page missing YAML frontmatter",
        },
        {
            "stage": "integrity",
            "code": "L002",
            "path": compiled_path.relative_to(tmp_path).as_posix(),
            "message": "broken wikilink: [[compiled/missing-page]]",
        },
    ]
