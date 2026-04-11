from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.bench import corpus


def test_seed_canonical_benchmark_root_uses_full_canonical_fixture_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingested: list[tuple[Path, str, Path]] = []
    rebuilt: list[Path] = []

    def fake_ingest(path: Path, *, source: str, root: Path) -> dict[str, object]:
        ingested.append((path, source, root))
        return {"path": path.as_posix(), "source": source, "root": root.as_posix()}

    def fake_rebuild(root: Path) -> dict[str, object]:
        rebuilt.append(root)
        return {"root": root.as_posix()}

    monkeypatch.setattr(corpus, "run_ingest", fake_ingest)
    monkeypatch.setattr(corpus, "run_rebuild", fake_rebuild)

    seeded = corpus.seed_canonical_benchmark_root(tmp_path)

    assert [item["fixture_id"] for item in seeded] == list(
        corpus.CANONICAL_BENCHMARK_FIXTURE_PATHS
    )
    assert len(ingested) == len(corpus.CANONICAL_BENCHMARK_FIXTURE_PATHS)
    assert all(root == tmp_path for _, _, root in ingested)
    assert {source for _, source, _ in ingested} == {"claude", "opencode"}
    assert rebuilt == [tmp_path]
