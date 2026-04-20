from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _load_retrieval_helpers():
    return importlib.import_module("tests.helpers.retrieval_data")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def snowiki_dir(repo_root: Path) -> Path:
    return repo_root / "src" / "snowiki"


@pytest.fixture(scope="session")
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "fixtures"


@pytest.fixture(scope="session")
def benchmarks_dir(repo_root: Path) -> Path:
    return repo_root / "benchmarks"


@pytest.fixture(scope="session")
def claude_fixtures_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "claude"


@pytest.fixture(scope="session")
def claude_fixture_dir(claude_fixtures_dir: Path) -> Path:
    return claude_fixtures_dir


@pytest.fixture
def claude_basic_fixture(claude_fixtures_dir: Path) -> Path:
    return claude_fixtures_dir / "basic.jsonl"


@pytest.fixture
def claude_multi_source_fixture(claude_fixtures_dir: Path) -> Path:
    return claude_fixtures_dir / "multi_source.jsonl"


@pytest.fixture(scope="session")
def opencode_fixtures_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "opencode"


@pytest.fixture(scope="session")
def opencode_fixture_dir(opencode_fixtures_dir: Path) -> Path:
    return opencode_fixtures_dir


@pytest.fixture(scope="session")
def corrupted_claude_fixtures_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "corrupted" / "claude"


@pytest.fixture(scope="session")
def corrupted_opencode_fixtures_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "corrupted" / "opencode"


@pytest.fixture(scope="session")
def benchmark_queries_path(benchmarks_dir: Path) -> Path:
    return benchmarks_dir / "queries.json"


@pytest.fixture(scope="session")
def benchmark_judgments_path(benchmarks_dir: Path) -> Path:
    return benchmarks_dir / "judgments.json"


@pytest.fixture(scope="session")
def search_api_module():
    retrieval_helpers = _load_retrieval_helpers()
    return retrieval_helpers.load_search_api()


@pytest.fixture(scope="session")
def normalized_records_data() -> tuple[dict[str, object], ...]:
    retrieval_helpers = _load_retrieval_helpers()
    return retrieval_helpers.normalized_records()


@pytest.fixture(scope="session")
def compiled_pages_data() -> tuple[dict[str, object], ...]:
    retrieval_helpers = _load_retrieval_helpers()
    return retrieval_helpers.compiled_pages()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    del config
    for item in items:
        path = Path(str(item.path)).as_posix()
        if "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
        if "/tests/bench/" in path or "/tests/integration/bench/" in path:
            item.add_marker(pytest.mark.bench)
        if "/tests/perf/" in path:
            item.add_marker(pytest.mark.perf)


@pytest.fixture
def opencode_basic_fixture(opencode_fixtures_dir: Path) -> Path:
    return opencode_fixtures_dir / "basic.jsonl"


@pytest.fixture
def opencode_basic_db_fixture(opencode_fixtures_dir: Path) -> Path:
    return opencode_fixtures_dir / "basic.db"
