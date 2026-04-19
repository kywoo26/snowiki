from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

from snowiki.search import BM25SearchDocument, BM25SearchIndex, build_lexical_index

if TYPE_CHECKING:
    from collections.abc import Iterable


def measure_peak_rss_mb() -> float | None:
    """Return the current process peak RSS in MB when supported."""

    try:
        import resource
    except ImportError:
        return None

    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(float(usage) / (1024 * 1024), 6)
    return round(float(usage) / 1024, 6)


def directory_size_mb(path: Path) -> float:
    """Return recursive on-disk size in MB for a directory tree."""

    total_bytes = 0
    for root, _, files in os.walk(path):
        root_path = Path(root)
        for name in files:
            try:
                total_bytes += (root_path / name).stat().st_size
            except FileNotFoundError:
                continue
    return round(total_bytes / (1024 * 1024), 6)


def measure_regex_candidate_build(
    *, records: Iterable[dict[str, object]]
) -> tuple[float | None, float]:
    """Measure runtime lexical control build memory and a serialized disk proxy."""

    lexical = build_lexical_index(records)
    peak_rss_mb = measure_peak_rss_mb()
    with TemporaryDirectory(prefix="snowiki-bench-regex-") as tmpdir:
        out = Path(tmpdir) / "lexical-index.json"
        payload: dict[str, Any] = {
            "documents": [
                {
                    "id": document.id,
                    "path": document.path,
                    "kind": document.kind,
                    "title": document.title,
                }
                for document in lexical.documents
            ],
            "postings": dict(lexical.index._postings),
            "field_tokens": lexical.index._field_tokens,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
        disk_size_mb = directory_size_mb(Path(tmpdir))
    return peak_rss_mb, disk_size_mb


def measure_bm25_candidate_build(
    *, documents: Iterable[BM25SearchDocument], tokenizer_name: str
) -> tuple[float | None, float]:
    """Measure BM25 candidate build memory and serialized disk footprint."""

    index = BM25SearchIndex(documents, tokenizer_name=tokenizer_name)
    peak_rss_mb = measure_peak_rss_mb()
    with TemporaryDirectory(prefix=f"snowiki-bench-{tokenizer_name}-") as tmpdir:
        index_path = Path(tmpdir) / "bm25-index"
        index.save(index_path.as_posix())
        disk_size_mb = directory_size_mb(Path(tmpdir))
    return peak_rss_mb, disk_size_mb
