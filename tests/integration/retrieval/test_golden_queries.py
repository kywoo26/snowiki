from __future__ import annotations

import json

from snowiki.config import resolve_repo_asset_path


def test_snowiki_owned_golden_query_fixture_covers_required_slices() -> None:
    fixture_path = resolve_repo_asset_path("fixtures/retrieval/golden_queries.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    queries = payload["queries"]
    slices = {query["slice"] for query in queries}

    assert payload["version"] == 1
    assert slices == {
        "Korean query -> Korean document",
        "Korean query -> English or code-heavy document",
        "English query -> Korean document",
        "mixed Korean/English query",
        "exact path or filename query",
        "code/API/symbol query",
        "CLI/tool command query",
        "session/history query",
        "topical exploratory query",
        "source/provenance validation query",
    }
    assert len({query["id"] for query in queries}) == len(queries)
    assert all(query["query"] for query in queries)
    assert all(query["expected_paths"] for query in queries)
