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

SUPPORTED_BENCHMARK_QUERY_IDS = frozenset(
    {
        "ko-001",
        "ko-002",
        "ko-004",
        "ko-012",
        "ko-017",
        "en-001",
        "en-002",
        "en-003",
        "en-004",
        "en-006",
        "en-007",
        "en-011",
        "en-012",
        "en-017",
        "en-020",
        "mix-001",
        "mix-002",
        "mix-004",
        "mix-006",
        "mix-007",
        "mix-012",
        "mix-017",
        "mix-018",
    }
)


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
def blended_index_data(search_api_module, normalized_records_data, compiled_pages_data):
    search = search_api_module
    lexical_index = search.build_lexical_index(normalized_records_data)
    wiki_index = search.build_wiki_index(compiled_pages_data)
    return search.build_blended_index(lexical_index.documents, wiki_index.documents)


@lru_cache(maxsize=1)
def benchmark_queries() -> list[dict[str, object]]:
    return benchmark_queries_from_path(_repo_root() / "benchmarks" / "queries.json")


@lru_cache(maxsize=1)
def benchmark_queries_from_path(path: Path) -> list[dict[str, object]]:
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
        if query_id not in SUPPORTED_BENCHMARK_QUERY_IDS:
            continue
        normalized_rows.append({**row, "query": row.get("query", row.get("text", ""))})
    return normalized_rows


@lru_cache(maxsize=1)
def benchmark_judgments() -> dict[str, list[str]]:
    return benchmark_judgments_from_path(_repo_root() / "benchmarks" / "judgments.json")


@lru_cache(maxsize=1)
def benchmark_judgments_from_path(path: Path) -> dict[str, list[str]]:
    rows = _read_json(path)
    if isinstance(rows, dict):
        rows_map = {str(key): value for key, value in rows.items()}
        judgments_data = rows_map.get("judgments")
        judgments = cast(dict[str, list[str]], judgments_data)
        assert isinstance(judgments, dict)
        normalized: dict[str, list[str]] = {}
        for query_id, paths in judgments.items():
            if str(query_id) not in SUPPORTED_BENCHMARK_QUERY_IDS:
                continue
            assert isinstance(paths, list)
            normalized[str(query_id)] = [
                BENCHMARK_DOC_PATHS.get(str(path), str(path)) for path in paths
            ]
        return normalized

    rows = _require_list_of_dicts(rows)
    judgments: dict[str, list[str]] = {}
    for row in rows:
        if str(row["query_id"]) not in SUPPORTED_BENCHMARK_QUERY_IDS:
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
            "text": "Basic Claude JSONL session fixture. 기본 세션 fixture 위치. Canonical sample for a basic Claude session export.",
            "aliases": ["basic Claude fixture", "클로드 기본 세션", "fixture_lookup"],
        },
        {
            "id": "fixtures/claude/with_tools.jsonl",
            "path": "fixtures/claude/with_tools.jsonl",
            "title": "Claude tool call fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture for tool calls and tool results.",
            "text": "Claude fixture with tool calls and tool results. 도구 호출과 tool result를 검증하는 JSONL 예시. with_tools fixture purpose is exercising tool call flows.",
            "aliases": ["with_tools", "tool call", "도구 호출", "tool results"],
        },
        {
            "id": "fixtures/claude/with_attachments.jsonl",
            "path": "fixtures/claude/with_attachments.jsonl",
            "title": "Claude attachments fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture with attachments.",
            "text": "Claude fixture with attachments and attachment handling. 첨부파일이 있는 fixture. with_attachments sample purpose is exercising attachment handling.",
            "aliases": ["attachment", "attachments", "with_attachments", "첨부파일"],
        },
        {
            "id": "fixtures/claude/with_sidechains.jsonl",
            "path": "fixtures/claude/with_sidechains.jsonl",
            "title": "Claude sidechain fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture with sidechain branches.",
            "text": "JSONL sample with sidechain branches. 사이드체인 분기 테스트 샘플.",
            "aliases": ["sidechain", "branches", "사이드체인"],
        },
        {
            "id": "fixtures/claude/resumed.jsonl",
            "path": "fixtures/claude/resumed.jsonl",
            "title": "Resumed Claude session fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture for resumed sessions.",
            "text": "Fixture that models a resumed Claude session. 재개된 세션 fixture.",
            "aliases": ["resumed", "재개된 세션"],
        },
        {
            "id": "fixtures/claude/large_output.jsonl",
            "path": "fixtures/claude/large_output.jsonl",
            "title": "Large stdout fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture with large command output.",
            "text": "Fixture containing large stdout and large command output. 큰 stdout 출력을 가진 fixture.",
            "aliases": ["large output", "stdout", "큰 stdout"],
        },
        {
            "id": "fixtures/claude/corrupted/malformed_json.jsonl",
            "path": "fixtures/claude/corrupted/malformed_json.jsonl",
            "title": "Malformed Claude JSON fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Corrupted Claude fixture.",
            "text": "Corrupted Claude JSONL fixture file. 손상된 Claude jsonl 파일 목록에 포함. malformed json sample.",
            "aliases": ["corrupted Claude", "malformed json"],
        },
        {
            "id": "fixtures/claude/corrupted/missing_fields.jsonl",
            "path": "fixtures/claude/corrupted/missing_fields.jsonl",
            "title": "Missing fields Claude fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Corrupted Claude fixture.",
            "text": "Corrupted Claude JSONL fixture with missing fields. 손상된 Claude jsonl 파일 목록에 포함.",
            "aliases": ["corrupted Claude", "missing fields"],
        },
        {
            "id": "fixtures/claude/corrupted/wrong_types.jsonl",
            "path": "fixtures/claude/corrupted/wrong_types.jsonl",
            "title": "Wrong types Claude fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Corrupted Claude fixture.",
            "text": "Corrupted Claude JSONL fixture with wrong types. 손상된 Claude jsonl 파일 목록에 포함.",
            "aliases": ["corrupted Claude", "wrong types"],
        },
        {
            "id": "fixtures/opencode/basic.db",
            "path": "fixtures/opencode/basic.db",
            "title": "OpenCode basic database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Baseline OpenCode database.",
            "text": "OpenCode basic database fixture for fixture inventory contract work. fixture inventory contract itself is referenced here.",
            "aliases": ["basic opencode", "fixture inventory contract", "omo basic"],
        },
        {
            "id": "fixtures/opencode/with_todos.db",
            "path": "fixtures/opencode/with_todos.db",
            "title": "OpenCode todos database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Database with todos.",
            "text": "OpenCode database fixture that includes todos and todo rows. todo가 들어있는 OpenCode 데이터베이스.",
            "aliases": ["todos", "todo rows", "todo가 들어있는"],
        },
        {
            "id": "fixtures/opencode/with_diffs.db",
            "path": "fixtures/opencode/with_diffs.db",
            "title": "OpenCode diffs database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Database with diffs.",
            "text": "OpenCode sqlite sample and database fixture that includes diffs and diff rows. diff 정보가 있는 OpenCode fixture.",
            "aliases": ["diff", "diff rows", "diff 정보", "sqlite sample"],
        },
        {
            "id": "fixtures/opencode/with_reasoning.db",
            "path": "fixtures/opencode/with_reasoning.db",
            "title": "OpenCode reasoning database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Database with reasoning blocks.",
            "text": "OpenCode sqlite sample with reasoning blocks. reasoning 블록이 저장된 sqlite 샘플.",
            "aliases": ["reasoning", "reasoning block", "reasoning 블록"],
        },
        {
            "id": "fixtures/opencode/with_compaction.db",
            "path": "fixtures/opencode/with_compaction.db",
            "title": "OpenCode compaction database fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Database with compaction events.",
            "text": "OpenCode db fixture with compaction events. compaction 이벤트를 담은 db.",
            "aliases": ["compaction", "compaction event"],
        },
        {
            "id": "fixtures/opencode/corrupted/truncated.db",
            "path": "fixtures/opencode/corrupted/truncated.db",
            "title": "Truncated SQLite fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Corrupted SQLite sample.",
            "text": "Corrupted sqlite sample. 손상된 sqlite 샘플 목록에 포함.",
            "aliases": ["corrupted sqlite", "truncated db"],
        },
        {
            "id": "fixtures/opencode/corrupted/not_sqlite.db",
            "path": "fixtures/opencode/corrupted/not_sqlite.db",
            "title": "Not SQLite fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Corrupted SQLite sample.",
            "text": "Corrupted sqlite sample. 손상된 sqlite 샘플 목록에 포함.",
            "aliases": ["corrupted sqlite", "not sqlite"],
        },
        {
            "id": "fixtures/opencode/corrupted/empty.db",
            "path": "fixtures/opencode/corrupted/empty.db",
            "title": "Empty SQLite fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Corrupted SQLite sample.",
            "text": "Corrupted sqlite sample. 손상된 sqlite 샘플 목록에 포함.",
            "aliases": ["corrupted sqlite", "empty db"],
        },
        {
            "id": "fixtures/claude/secret_bearing.jsonl",
            "path": "fixtures/claude/secret_bearing.jsonl",
            "title": "Secret-bearing Claude fixture",
            "record_type": "fixture",
            "recorded_at": recorded_at,
            "summary": "Fixture for privacy gate validation.",
            "text": "Claude fixture intentionally containing synthetic API keys and passwords for privacy testing. privacy gate reasoning and 민감정보 차단 behavior are covered here.",
            "aliases": [
                "privacy gate",
                "synthetic secrets",
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
            "text": "queries.json stores all benchmark queries. Total benchmark query count is 60. Korean benchmark queries count is 20. English and mixed-language queries are included. 한국어 질의 benchmark는 20개이고 전체는 60개이며 영문과 혼합 질의도 포함된다.",
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
            "text": "judgments.json stores the gold judgments and gold labels for retrieval benchmark queries. gold label 파일 이름.",
            "aliases": ["gold judgments", "gold label", "judgments.json"],
        },
        {
            "id": "tests/contracts/test_fixture_inventory.py",
            "path": "tests/contracts/test_fixture_inventory.py",
            "title": "Fixture inventory contract test",
            "record_type": "test",
            "recorded_at": recorded_at,
            "summary": "Contract test for the fixture inventory.",
            "text": "Fixture inventory contract test path. fixture inventory 계약 테스트 파일은 여기 있다.",
            "aliases": [
                "fixture inventory contract test",
                "fixture inventory",
                "계약 테스트",
            ],
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
            "body": "The benchmark corpus contains 60 queries split across Korean, English, and mixed-language prompts. 벤치마크는 Korean English mixed query coverage를 가진다.",
            "aliases": ["benchmark overview", "corpus metadata"],
            "updated_at": "2026-04-08T12:00:00Z",
        },
    )


@lru_cache(maxsize=1)
def blended_index():
    search = load_search_api()
    lexical_index = search.build_lexical_index(normalized_records())
    wiki_index = search.build_wiki_index(compiled_pages())
    return search.build_blended_index(lexical_index.documents, wiki_index.documents)
