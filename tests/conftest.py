from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_retrieval_helpers() -> ModuleType:
    retrieval_conftest = Path(__file__).resolve().parent / "retrieval" / "conftest.py"
    spec = importlib.util.spec_from_file_location(
        "tests.retrieval.conftest", retrieval_conftest
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def snowiki_dir(repo_root: Path) -> Path:
    return repo_root / "snowiki"


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
    retrieval_helpers: ModuleType = _load_retrieval_helpers()
    return retrieval_helpers.load_search_api()


@pytest.fixture(scope="session")
def normalized_records_data() -> tuple[dict[str, object], ...]:
    retrieval_helpers: ModuleType = _load_retrieval_helpers()
    return retrieval_helpers.normalized_records()


@pytest.fixture(scope="session")
def compiled_pages_data() -> tuple[dict[str, object], ...]:
    retrieval_helpers: ModuleType = _load_retrieval_helpers()
    return retrieval_helpers.compiled_pages()


@pytest.fixture
def opencode_basic_fixture(opencode_fixtures_dir: Path) -> Path:
    return opencode_fixtures_dir / "basic.jsonl"


@pytest.fixture
def opencode_basic_db_fixture(opencode_fixtures_dir: Path) -> Path:
    return opencode_fixtures_dir / "basic.db"
