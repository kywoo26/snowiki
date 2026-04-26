from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import cast

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


BENCHMARK_DOC_PATHS = {
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


def _read_json(path: Path) -> object:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def _require_list_of_dicts(data: object) -> list[dict[str, object]]:
    assert isinstance(data, list)
    assert all(isinstance(item, dict) for item in data)
    result: list[dict[str, object]] = []
    for item in data:
        assert isinstance(item, dict)
        result.append({str(key): value for key, value in item.items()})
    return result


@lru_cache(maxsize=1)
def supported_benchmark_query_ids() -> frozenset[str]:
    data = _read_json(_repo_root() / "benchmarks" / "queries.json")
    if isinstance(data, dict):
        data_map = {str(key): value for key, value in data.items()}
        rows_data = data_map.get("queries")
    else:
        rows_data = data
    rows = _require_list_of_dicts(rows_data)
    return frozenset(
        str(row.get("id", ""))
        for row in rows
        if str(row.get("group", "")) in {"ko", "mixed"}
    )


def load_search_api():
    return importlib.import_module("snowiki.search")


@pytest.fixture(scope="session")
def search_api_module():
    return load_search_api()


@pytest.fixture(scope="session")
def benchmark_queries_data(benchmark_queries_path: Path) -> list[dict[str, object]]:
    return benchmark_queries_from_path(benchmark_queries_path)


@pytest.fixture(scope="session")
def benchmark_judgments_data(benchmark_judgments_path: Path) -> dict[str, list[str]]:
    return benchmark_judgments_from_path(benchmark_judgments_path)


@pytest.fixture(scope="session")
def normalized_records_data() -> tuple[dict[str, object], ...]:
    return normalized_records()


@pytest.fixture(scope="session")
def compiled_pages_data() -> tuple[dict[str, object], ...]:
    return compiled_pages()


@pytest.fixture(scope="session")
def runtime_index_data(search_api_module, normalized_records_data, compiled_pages_data):
    search = search_api_module
    return search.RetrievalService.from_records_and_pages(
        records=list(normalized_records_data),
        pages=list(compiled_pages_data),
    ).index


@lru_cache(maxsize=1)
def benchmark_queries() -> list[dict[str, object]]:
    return benchmark_queries_from_path(_repo_root() / "benchmarks" / "queries.json")


@lru_cache(maxsize=1)
def benchmark_queries_from_path(path: Path) -> list[dict[str, object]]:
    supported_ids = supported_benchmark_query_ids()
    data = _read_json(path)
    if isinstance(data, dict):
        data_map = {str(key): value for key, value in data.items()}
        rows_data = data_map.get("queries")
    else:
        rows_data = data
    rows = _require_list_of_dicts(rows_data)
    normalized_rows: list[dict[str, object]] = []
    for row in rows:
        query_id = str(row.get("id", ""))
        if query_id not in supported_ids:
            continue
        normalized_rows.append({**row, "query": row.get("query", row.get("text", ""))})
    return normalized_rows


@lru_cache(maxsize=1)
def benchmark_judgments() -> dict[str, list[str]]:
    return benchmark_judgments_from_path(_repo_root() / "benchmarks" / "judgments.json")


@lru_cache(maxsize=1)
def benchmark_judgments_from_path(path: Path) -> dict[str, list[str]]:
    supported_ids = supported_benchmark_query_ids()
    rows = _read_json(path)
    if isinstance(rows, dict):
        rows_map = {str(key): value for key, value in rows.items()}
        judgments_data = rows_map.get("judgments")
        judgments = cast(dict[str, list[str]], judgments_data)
        assert isinstance(judgments, dict)
        normalized: dict[str, list[str]] = {}
        for query_id, paths in judgments.items():
            if str(query_id) not in supported_ids:
                continue
            assert isinstance(paths, list)
            normalized[str(query_id)] = [
                BENCHMARK_DOC_PATHS.get(str(path), str(path)) for path in paths
            ]
        return normalized

    rows = _require_list_of_dicts(rows)
    judgments: dict[str, list[str]] = {}
    for row in rows:
        if str(row["query_id"]) not in supported_ids:
            continue
        paths = row["relevant_paths"]
        assert isinstance(paths, list)
        judgments[str(row["query_id"])] = [str(path) for path in paths]
    return judgments


@lru_cache(maxsize=1)
def normalized_records() -> tuple[dict[str, object], ...]:
    recorded_at = (
        datetime(2026, 4, 8, 12, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z")
    )
    return (
        {
            "id": "fixtures/claude/basic.jsonl",
            "path": "fixtures/claude/basic.jsonl",
            "title": "Basic Claude JSONL fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Basic Claude session fixture path.",
            "text": "Basic Claude JSONL session fixture. 기본 세션 fixture 위치. Canonical sample for a basic Claude session export. Snowiki를 개인 위키로 설명하는 가장 기본 Claude 세션이며 지식을 축적하는 개인 위키와 knowledge compounding personal wiki 개념을 다룬다.",
            "aliases": [
                "basic Claude fixture",
                "클로드 기본 세션",
                "fixture_lookup",
                "personal wiki",
                "개인 위키",
                "knowledge compounding",
                "지식을 축적하는 개인 위키",
            ],
        },
        {
            "id": "fixtures/claude/with_tools.jsonl",
            "path": "fixtures/claude/with_tools.jsonl",
            "title": "Claude tool call fixture",
            "record_type": "fixture",
            "recorded_at": "2026-04-02T09:30:00Z",
            "summary": "Fixture for tool calls and tool results.",
            "text": "Claude fixture with tool calls and tool results. 도구 호출과 tool result를 검증하는 JSONL 예시. with_tools fixture purpose is exercising tool call flows. qmd search를 Bash tool_use로 실행했고 2026-04-02에 qmd search 실행이 있었던 세션이다.",
            "aliases": [
                "with_tools",
                "tool call",
                "도구 호출",
                "tool results",
                "qmd search",
                "Bash tool_use",
                "2026-04-02",
            ],
        },
        {
            "id": "fixtures/claude/with_attachments.jsonl",
            "path": "fixtures/claude/with_attachments.jsonl",
            "title": "Claude attachments fixture",
            "record_type": "fixture",
            "recorded_at": "2026-04-03T10:00:00Z",
            "summary": "Fixture with attachments.",
            "text": "Claude fixture with attachments and attachment handling. 첨부파일이 있는 fixture. with_attachments sample purpose is exercising attachment handling. design-notes.md와 queries.csv 첨부 파일이 있고 2026-04-03 attachment-based planning과 benchmark coverage, query inventory, evaluation planning 자료를 담는다.",
            "aliases": [
                "attachment",
                "attachments",
                "with_attachments",
                "첨부파일",
                "design-notes.md",
                "queries.csv",
                "attachment-based planning",
                "benchmark coverage",
                "query inventory",
                "evaluation planning",
                "2026-04-03",
            ],
        },
        {
            "id": "fixtures/claude/with_sidechains.jsonl",
            "path": "fixtures/claude/with_sidechains.jsonl",
            "title": "Claude sidechain fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture with sidechain branches.",
            "text": "JSONL sample with sidechain branches. 사이드체인 분기 테스트 샘플. branch-audit sidechain slug와 sidechain branch metadata example을 보여준다.",
            "aliases": [
                "sidechain",
                "branches",
                "사이드체인",
                "branch-audit",
                "sidechain branch metadata",
            ],
        },
        {
            "id": "fixtures/claude/resumed.jsonl",
            "path": "fixtures/claude/resumed.jsonl",
            "title": "Resumed Claude session fixture",
            "record_type": "fixture",
            "recorded_at": "2026-04-05T08:30:00Z",
            "summary": "Fixture for resumed sessions.",
            "text": "Fixture that models a resumed Claude session. 재개된 세션 fixture. resume_continuation marker와 resume context, continuation 흐름, carry-over context를 담고 2026-04-05에 이전 세션을 이어서 작업한 자료다.",
            "aliases": [
                "resumed",
                "재개된 세션",
                "resume_continuation",
                "resume context",
                "continuation",
                "carry-over context",
                "2026-04-05",
            ],
        },
        {
            "id": "fixtures/claude/large_output.jsonl",
            "path": "fixtures/claude/large_output.jsonl",
            "title": "Large stdout fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture with large command output.",
            "text": "Fixture containing large stdout and large command output. 큰 stdout 출력을 가진 fixture. 대용량 fixture generation log와 oversized tool_result 응답을 포함해 large tool output stress fixture 역할을 한다.",
            "aliases": [
                "large output",
                "stdout",
                "큰 stdout",
                "fixture generation log",
                "large generation log",
                "oversized tool_result",
            ],
        },
        {
            "id": "fixtures/opencode/basic.db",
            "path": "fixtures/opencode/basic.db",
            "title": "OpenCode basic database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Baseline OpenCode database and basic OMO session.",
            "text": "OpenCode basic database fixture for baseline session and inventory-style fixture lookup work. 기본 OMO 세션이며 basic OMO session wording으로도 찾을 수 있다. knowledge compounding personal wiki notes also mention the personal wiki concept alongside inventory work.",
            "aliases": [
                "basic opencode",
                "omo basic",
                "기본 OMO 세션",
                "basic OMO session",
                "knowledge compounding personal wiki",
                "개인 위키",
            ],
        },
        {
            "id": "fixtures/opencode/with_todos.db",
            "path": "fixtures/opencode/with_todos.db",
            "title": "OpenCode todos database fixture",
            "record_type": "fixture",
            "recorded_at": "2026-04-02T15:00:00Z",
            "summary": "Database with todos.",
            "text": "OpenCode database fixture that includes todos and todo rows. todo가 들어있는 OpenCode 데이터베이스. todo에 한국어 query 검증 작업과 Korean/English benchmark work가 들어 있고 benchmark coverage, query inventory, evaluation planning, qmd search follow-up를 기록한다.",
            "aliases": [
                "todos",
                "todo rows",
                "todo가 들어있는",
                "한국어 query 검증 작업",
                "Korean/English benchmark work",
                "benchmark coverage",
                "query inventory",
                "evaluation planning",
                "qmd search",
                "2026-04-02",
            ],
        },
        {
            "id": "fixtures/opencode/with_diffs.db",
            "path": "fixtures/opencode/with_diffs.db",
            "title": "OpenCode diffs database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Database with diffs, including the benchmark judgments diff.",
            "text": "OpenCode sqlite sample and database fixture that includes diffs and diff rows. diff 정보가 있는 OpenCode fixture. benchmarks/judgments.json diff가 포함된 OMO 세션이며 benchmarks/judgments.json diff part가 있는 OMO session으로 찾을 수 있다. benchmark coverage와 query inventory planning 문맥도 함께 들어 있다.",
            "aliases": [
                "diff",
                "diff rows",
                "diff 정보",
                "sqlite sample",
                "benchmarks/judgments.json diff",
                "OMO session",
                "benchmark coverage",
                "query inventory",
            ],
        },
        {
            "id": "fixtures/opencode/with_reasoning.db",
            "path": "fixtures/opencode/with_reasoning.db",
            "title": "OpenCode reasoning database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Database with reasoning blocks.",
            "text": "OpenCode sqlite sample with reasoning blocks. reasoning 블록이 저장된 sqlite 샘플. privacy gate reasoning part와 secret redaction, 민감정보 차단, rejection behavior를 설명한다.",
            "aliases": [
                "reasoning",
                "reasoning block",
                "reasoning 블록",
                "privacy gate reasoning",
                "secret redaction",
                "민감정보 차단",
                "rejection behavior",
            ],
        },
        {
            "id": "fixtures/opencode/with_compaction.db",
            "path": "fixtures/opencode/with_compaction.db",
            "title": "OpenCode compaction database fixture",
            "record_type": "fixture",
            "recorded_at": "2026-04-05T11:30:00Z",
            "summary": "Database with compaction events.",
            "text": "OpenCode db fixture with compaction events. compaction 이벤트를 담은 db. compaction marker와 compaction timing이 있고 resumed work, resume flow, continuation, carry-over context가 2026-04-05 자료와 함께 저장되어 있다.",
            "aliases": [
                "compaction",
                "compaction event",
                "compaction marker",
                "compaction timing",
                "resume flow",
                "continuation",
                "carry-over context",
                "2026-04-05",
            ],
        },
        {
            "id": "fixtures/claude/secret_bearing.jsonl",
            "path": "fixtures/claude/secret_bearing.jsonl",
            "title": "Secret-bearing Claude fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture for privacy gate validation.",
            "text": "Claude fixture intentionally containing synthetic API keys and passwords for privacy testing. synthetic API key와 password가 함께 들어 있는 privacy 테스트 세션이며 privacy gate reasoning, secret redaction, 민감정보 차단 behavior are covered here.",
            "aliases": [
                "privacy gate",
                "synthetic secrets",
                "synthetic API key",
                "password가 함께 들어 있는 privacy 테스트 세션",
                "password",
                "민감정보 차단",
            ],
        },
        {
            "id": "fixtures/secrets/test_api_keys.jsonl",
            "path": "fixtures/secrets/test_api_keys.jsonl",
            "title": "Fake API key fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fake secrets fixture.",
            "text": "Fake API key fixture stored under fixtures/secrets. 테스트 키 파일 path.",
            "aliases": ["fake API key", "test_api_keys", "테스트 키 파일"],
        },
        {
            "id": "benchmarks/queries.json",
            "path": "benchmarks/queries.json",
            "title": "Benchmark queries dataset",
            "record_type": "benchmark",
            "recorded_at": recorded_at,
            "summary": "Benchmark query metadata.",
            "text": "queries.json stores all benchmark queries. Total benchmark query count is 90. Korean benchmark queries count is 30. English and mixed-language queries are included, with explicit tags and no-answer cases. 한국어 질의 benchmark는 30개이고 전체는 90개이며 태그와 no-answer case를 포함한다.",
            "aliases": [
                "queries.json",
                "benchmark queries",
                "mixed language queries",
                "한국어 질의 benchmark",
                "영문과 혼합 질의",
                "포함된다",
            ],
        },
        {
            "id": "benchmarks/judgments.json",
            "path": "benchmarks/judgments.json",
            "title": "Gold judgments dataset",
            "record_type": "benchmark",
            "recorded_at": recorded_at,
            "summary": "Gold labels for retrieval.",
            "text": "This benchmark asset stores gold judgments and gold labels for retrieval benchmark queries. It is the canonical labels dataset, not the OMO diff session that edits those labels.",
            "aliases": ["gold judgments", "gold label", "labels dataset"],
        },
        {
            "id": "session-yesterday-korean-english",
            "path": "sessions/2026/04/07/mixed-retrieval-session.json",
            "title": "Mixed language retrieval session",
            "record_type": "session",
            "recorded_at": "2026-04-07T18:00:00Z",
            "summary": "Yesterday retrieval work.",
            "text": "Worked on bilingual lexical retrieval, Korean tokenization, and benchmark recall yesterday. 어제 한국어 검색과 mixed query retrieval 작업을 진행했다.",
            "aliases": ["yesterday retrieval", "어제"],
        },
        {
            "id": "session-today-indexing",
            "path": "sessions/2026/04/08/indexing-session.json",
            "title": "Index builder session",
            "record_type": "session",
            "recorded_at": "2026-04-08T09:00:00Z",
            "summary": "Today indexing work.",
            "text": "Today we worked on index building and blended search results. 오늘 인덱스 빌드 작업을 했다.",
            "aliases": ["today", "오늘", "index building"],
        },
    )


@lru_cache(maxsize=1)
def compiled_pages() -> tuple[dict[str, object], ...]:
    return (
        {
            "id": "wiki-mixed-search-overview",
            "path": "compiled/wiki/search/mixed-language-overview.md",
            "title": "Mixed-language lexical retrieval overview",
            "summary": "Overview page for bilingual search.",
            "body": "This compiled page explains blended session and wiki page retrieval for Korean and English mixed queries. 한국어와 영어 혼합 질의를 위해 session/page blended results를 제공한다.",
            "aliases": [
                "mixed language retrieval",
                "blended results",
                "한국어 영어 혼합 질의",
            ],
            "updated_at": "2026-04-08T12:00:00Z",
        },
        {
            "id": "wiki-benchmark-overview",
            "path": "compiled/wiki/benchmarks/overview.md",
            "title": "Benchmark corpus overview",
            "summary": "Overview of the retrieval benchmark corpus.",
            "body": "The benchmark corpus contains 90 queries split across Korean, English, and mixed-language prompts with richer edge-case coverage. 벤치마크는 Korean English mixed query coverage와 edge-case judged set을 가진다.",
            "aliases": ["benchmark overview", "corpus metadata"],
            "updated_at": "2026-04-08T12:00:00Z",
        },
    )


@lru_cache(maxsize=1)
def runtime_index():
    search = load_search_api()
    return search.RetrievalService.from_records_and_pages(
        records=list(normalized_records()),
        pages=list(compiled_pages()),
    ).index
