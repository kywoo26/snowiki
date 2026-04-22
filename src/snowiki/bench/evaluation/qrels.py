from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from snowiki.config import resolve_repo_asset_path

from ..contract import BENCHMARK_CORPUS


@dataclass(frozen=True)
class BenchmarkQuery:
    query_id: str
    text: str
    group: str
    kind: str
    tags: tuple[str, ...] = ()
    no_answer: bool = False


@dataclass(frozen=True)
class QrelEntry:
    query_id: str
    doc_id: str
    relevance: int = 1


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _mapping_rows(payload: object, key: str) -> object:
    if isinstance(payload, dict):
        payload_map = cast(dict[str, object], payload)
        return payload_map.get(key, payload)
    return payload


def _require_mapping_rows(rows: object, *, label: str) -> list[Mapping[str, object]]:
    if not isinstance(rows, list):
        raise ValueError(label)
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError(label)
    return [cast(Mapping[str, object], row) for row in rows]


def _string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(label)
    return [str(item) for item in value]


def _resolve_benchmark_asset_path(
    root: Path,
    configured_path: str | Path | None,
    *,
    default_relative_path: str,
) -> tuple[Path, str]:
    raw_path = configured_path or default_relative_path
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate, candidate.as_posix()

    root_candidate = root / candidate
    if root_candidate.exists():
        return root_candidate, root_candidate.as_posix()

    return resolve_repo_asset_path(candidate.as_posix()), candidate.as_posix()


def queries_from_payload(
    payload: object, *, path_label: str
) -> tuple[BenchmarkQuery, ...]:
    rows = _require_mapping_rows(
        _mapping_rows(payload, "queries"),
        label=f"{path_label} must contain a 'queries' list",
    )
    return tuple(
        BenchmarkQuery(
            query_id=str(row["id"]),
            text=str(row["text"]),
            group=str(row.get("group", "default")),
            kind=str(row.get("kind", "known-item")),
            tags=tuple(
                _string_list(
                    row.get("tags", []),
                    label=f"{path_label} tags must be a list",
                )
            ),
            no_answer=bool(row.get("no_answer", False)),
        )
        for row in rows
    )


def load_queries(
    root: Path, queries_path: str | Path | None = None
) -> tuple[BenchmarkQuery, ...]:
    resolved_path, path_label = _resolve_benchmark_asset_path(
        root,
        queries_path,
        default_relative_path=BENCHMARK_CORPUS["queries"],
    )
    payload = _load_json(resolved_path)
    return queries_from_payload(payload, path_label=path_label)


def _parse_qrel_entry(query_id: str, value: object, *, label: str) -> QrelEntry:
    if isinstance(value, QrelEntry):
        return value
    if isinstance(value, str):
        return QrelEntry(query_id=query_id, doc_id=value)
    if not isinstance(value, Mapping):
        raise ValueError(label)

    row = cast(Mapping[str, object], value)
    row_query_id = row.get("query_id", query_id)
    if str(row_query_id) != query_id:
        raise ValueError(label)

    doc_id = row.get("doc_id")
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise ValueError(label)

    relevance_raw = row.get("relevance", 1)
    if isinstance(relevance_raw, bool):
        relevance = int(relevance_raw)
    elif isinstance(relevance_raw, int):
        relevance = relevance_raw
    elif isinstance(relevance_raw, str):
        try:
            relevance = int(relevance_raw)
        except ValueError as exc:
            raise ValueError(label) from exc
    else:
        raise ValueError(label)

    return QrelEntry(query_id=query_id, doc_id=doc_id, relevance=relevance)


def _parse_qrel_entries(query_id: str, values: object, *, label: str) -> list[QrelEntry]:
    if not isinstance(values, list):
        raise ValueError(label)
    return [_parse_qrel_entry(query_id, value, label=label) for value in values]


def load_qrels(path: Path) -> dict[str, list[QrelEntry]]:
    payload = _load_json(path)
    rows = _mapping_rows(payload, "judgments")
    label = f"{path.as_posix()} must contain a 'judgments' mapping or list rows"
    if isinstance(rows, Mapping):
        return {
            str(key): _parse_qrel_entries(str(key), value, label=label)
            for key, value in rows.items()
        }

    if isinstance(rows, list):
        mapping_rows = _require_mapping_rows(rows, label=label)
        qrels: dict[str, list[QrelEntry]] = {}
        for row in mapping_rows:
            query_id = str(row["query_id"])
            if "doc_id" in row:
                qrels.setdefault(query_id, []).append(
                    _parse_qrel_entry(query_id, row, label=label)
                )
                continue

            if "qrels" in row:
                qrels.setdefault(query_id, []).extend(
                    _parse_qrel_entries(query_id, row["qrels"], label=label)
                )
                continue

            qrels.setdefault(query_id, []).extend(
                QrelEntry(query_id=query_id, doc_id=doc_id)
                for doc_id in _string_list(
                    row.get("relevant_paths", []),
                    label=label,
                )
            )
        return qrels

    raise ValueError(label)


def load_judgments(
    root: Path, judgments_path: str | Path | None = None
) -> dict[str, list[QrelEntry]]:
    resolved_path, path_label = _resolve_benchmark_asset_path(
        root,
        judgments_path,
        default_relative_path=BENCHMARK_CORPUS["judgments"],
    )
    try:
        return load_qrels(resolved_path)
    except ValueError as exc:
        raise ValueError(
            f"{path_label} must contain a 'judgments' mapping or list rows"
        ) from exc


def normalize_qrels(
    judgments: Mapping[str, object], *, label: str = "judgments"
) -> dict[str, list[QrelEntry]]:
    return {
        str(query_id): _parse_qrel_entries(
            str(query_id),
            entries,
            label=f"{label} must map query ids to qrel lists",
        )
        for query_id, entries in judgments.items()
    }


def relevant_doc_ids(
    judgments: Mapping[str, list[QrelEntry]]
) -> dict[str, list[str]]:
    return {
        query_id: [qrel.doc_id for qrel in qrels if qrel.relevance > 0]
        for query_id, qrels in judgments.items()
    }


__all__ = [
    "BenchmarkQuery",
    "QrelEntry",
    "load_judgments",
    "load_qrels",
    "load_queries",
    "normalize_qrels",
    "queries_from_payload",
    "relevant_doc_ids",
]
