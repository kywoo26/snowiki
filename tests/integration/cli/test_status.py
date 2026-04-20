from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app
from snowiki.search.workspace import content_freshness_identity


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _compiled_page(*, title: str, page_type: str, updated: str, body: str) -> str:
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            f'type: "{page_type}"',
            'created: "2026-04-15"',
            f'updated: "{updated}"',
            f'summary: "Summary for {title}"',
            "sources:",
            '  - "raw/claude/source-a.jsonl"',
            "related:",
            '  - "compiled/overview.md"',
            "tags:",
            f'  - "{page_type}"',
            "record_ids:",
            f'  - "{title.lower().replace(" ", "-")}"',
            "---",
            body,
        ]
    )


def _workspace_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix())
        if path.is_file()
    }


def _build_status_workspace(root: Path) -> None:
    _write_text(root / "raw" / "claude" / "source-a.jsonl", "{}\n")
    _write_text(root / "raw" / "opencode" / "source-b.jsonl", "{}\n")
    _write_json(
        root / "normalized" / "claude" / "2026-04-15" / "session-a.json",
        {
            "id": "session-a",
            "source_type": "claude",
            "record_type": "session",
            "recorded_at": "2026-04-15T09:00:00Z",
            "provenance": {"raw_refs": [{"path": "raw/claude/source-a.jsonl"}]},
        },
    )
    _write_json(
        root / "normalized" / "opencode" / "2026-04-16" / "session-b.json",
        {
            "id": "session-b",
            "source_type": "opencode",
            "record_type": "session",
            "recorded_at": "2026-04-16T08:30:00Z",
            "provenance": {"raw_refs": [{"path": "raw/opencode/source-b.jsonl"}]},
        },
    )

    _write_text(
        root / "compiled" / "overview.md",
        _compiled_page(
            title="Overview",
            page_type="overview",
            updated="2026-04-16",
            body="# Overview\n\n[[compiled/topics/wiki-dashboard]]\n[[compiled/questions/what-is-status]]\n",
        ),
    )
    _write_text(
        root / "compiled" / "topics" / "wiki-dashboard.md",
        _compiled_page(
            title="Wiki Dashboard",
            page_type="topic",
            updated="2026-04-15",
            body="# Wiki Dashboard\n\n[[compiled/overview]]\n[[compiled/questions/what-is-status]]\n",
        ),
    )
    _write_text(
        root / "compiled" / "questions" / "what-is-status.md",
        _compiled_page(
            title="What Is Status",
            page_type="question",
            updated="2026-04-14",
            body="# What Is Status\n\n[[compiled/overview]]\n[[compiled/topics/wiki-dashboard]]\n",
        ),
    )

    _write_json(
        root / "index" / "manifest.json",
        {
            "tokenizer_name": "regex_v1",
            "records_indexed": 2,
            "pages_indexed": 3,
            "search_documents": 5,
            "compiled_paths": [
                "compiled/overview.md",
                "compiled/questions/what-is-status.md",
                "compiled/topics/wiki-dashboard.md",
            ],
            "content_identity": content_freshness_identity(root),
        },
    )


def test_status_json_output_reports_wiki_native_dashboard_sections(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "command": "status",
        "result": {
            "root": tmp_path.as_posix(),
            "pages": {
                "total": 3,
                "by_type": {
                    "summary": 0,
                    "concept": 0,
                    "entity": 0,
                    "topic": 1,
                    "question": 1,
                    "project": 0,
                    "decision": 0,
                    "session": 0,
                    "overview": 1,
                },
            },
            "sources": {
                "total": 2,
                "by_type": {"claude": 1, "opencode": 1},
            },
            "lint": {
                "summary": {"error": 0, "warning": 0, "info": 2, "total": 2},
                "error_count": 0,
            },
            "freshness": {
                "status": "current",
                "manifest_content_identity": content_freshness_identity(tmp_path),
                "current_content_identity": content_freshness_identity(tmp_path),
                "latest_normalized_recorded_at": "2026-04-16T08:30:00Z",
                "latest_compiled_update": "2026-04-16",
            },
            "manifest": {
                "path": "index/manifest.json",
                "present": True,
                "tokenizer_name": "regex_v1",
                "records_indexed": 2,
                "pages_indexed": 3,
                "search_documents": 5,
                "compiled_path_count": 3,
            },
            "candidate_matrix": [
                {
                    "candidate_name": "regex_v1",
                    "evidence_baseline": "lexical",
                    "role": "control",
                    "admission_status": "admitted",
                    "control": True,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "supported",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "supported",
                            "windows": "supported",
                            "fallback_behavior": "none",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "low",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "current_runtime_default",
                    },
                },
                {
                    "candidate_name": "kiwi_morphology_v1",
                    "evidence_baseline": "bm25s_kiwi_full",
                    "role": "candidate",
                    "admission_status": "admitted",
                    "control": False,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "supported",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "supported",
                            "windows": "unknown",
                            "fallback_behavior": "unknown",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "medium",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "admitted_kiwi_candidate",
                    },
                },
                {
                    "candidate_name": "kiwi_nouns_v1",
                    "evidence_baseline": "bm25s_kiwi_nouns",
                    "role": "candidate",
                    "admission_status": "admitted",
                    "control": False,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "supported",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "supported",
                            "windows": "unknown",
                            "fallback_behavior": "unknown",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "medium",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "admitted_kiwi_candidate",
                    },
                },
                {
                    "candidate_name": "mecab_morphology_v1",
                    "evidence_baseline": "bm25s_mecab_full",
                    "role": "candidate",
                    "admission_status": "admitted",
                    "control": False,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "unknown",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "unknown",
                            "windows": "unknown",
                            "fallback_behavior": "unknown",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "medium",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "admitted_mecab_candidate",
                    },
                },
                {
                    "candidate_name": "hf_wordpiece_v1",
                    "evidence_baseline": "bm25s_hf_wordpiece",
                    "role": "candidate",
                    "admission_status": "admitted",
                    "control": False,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "supported",
                            "linux_x86_64": "supported",
                            "linux_aarch64": "supported",
                            "windows": "supported",
                            "fallback_behavior": "none",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": True,
                            "build_from_source_required": False,
                            "hidden_bootstrap_steps": False,
                            "operational_complexity": "medium",
                        },
                        "zero_cost_admission": True,
                        "admission_reason": "admitted_subword_candidate",
                    },
                },
                {
                    "candidate_name": "lindera_ko_v1",
                    "evidence_baseline": None,
                    "role": "candidate",
                    "admission_status": "not_admitted",
                    "control": False,
                    "operational_evidence": {
                        "memory_peak_rss_mb": None,
                        "memory_evidence_status": "not_measured",
                        "disk_size_mb": None,
                        "disk_size_evidence_status": "not_measured",
                        "platform_support": {
                            "macos": "unknown",
                            "linux_x86_64": "unknown",
                            "linux_aarch64": "unknown",
                            "windows": "unknown",
                            "fallback_behavior": "unknown",
                        },
                        "install_ergonomics": {
                            "prebuilt_available": None,
                            "build_from_source_required": None,
                            "hidden_bootstrap_steps": None,
                            "operational_complexity": "unknown",
                        },
                        "zero_cost_admission": False,
                        "admission_reason": "zero_cost_local_install_unavailable",
                    },
                },
            ],
        },
    }


def test_status_human_output_renders_dashboard_summary(tmp_path: Path) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)

    result = runner.invoke(app, ["status"], env={"SNOWIKI_ROOT": str(tmp_path)})

    assert result.exit_code == 0, result.output
    assert f"Snowiki status for {tmp_path.as_posix()}" in result.output
    assert "Pages: 3 total" in result.output
    assert (
        "By type: summary: 0, concept: 0, entity: 0, topic: 1, question: 1, project: 0, decision: 0, session: 0, overview: 1"
        in result.output
    )
    assert "Sources: 2 total" in result.output
    assert "By source: claude: 1, opencode: 1" in result.output
    assert "Lint: 0 errors, 0 warnings, 2 info" in result.output
    assert (
        "Freshness: state=current, tokenizer=regex_v1, latest normalized=2026-04-16T08:30:00Z, latest compiled=2026-04-16"
        in result.output
    )
    assert (
        "Manifest: tokenizer=regex_v1, records indexed=2, pages indexed=3, search documents=5, compiled paths=3"
        in result.output
    )
    assert "Tokenizer Candidates:" in result.output
    assert "  - regex_v1: role=control, status=admitted" in result.output
    assert "  - kiwi_morphology_v1: role=candidate, status=admitted" in result.output
    assert "  - kiwi_nouns_v1: role=candidate, status=admitted" in result.output
    assert "  - lindera_ko_v1: role=candidate, status=not_admitted" in result.output


def test_status_is_read_only_and_does_not_mutate_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)
    before = _workspace_snapshot(tmp_path)

    result = runner.invoke(
        app,
        ["status", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert _workspace_snapshot(tmp_path) == before
