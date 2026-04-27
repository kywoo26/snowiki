from __future__ import annotations

import csv
import io
import random
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from datasets import Dataset, load_dataset
from huggingface_hub import HfFileSystem

from snowiki.bench.datasets import (
    load_dataset_manifest,
    load_matrix,
    resolve_dataset_assets,
)
from snowiki.bench.specs import DatasetSourceLocator, LevelConfig
from snowiki.config import resolve_repo_asset_path
from snowiki.storage.zones import atomic_write_bytes, atomic_write_json, isoformat_utc

DEFAULT_MATRIX_PATH = Path("benchmarks/contracts/official_matrix.yaml")
HF_CACHE_DIR = Path("benchmarks/hf")
MATERIALIZATION_SIDECAR_NAME = "materialization.json"
QUERY_SAMPLING_SEED = 1729
CORPUS_SAMPLING_SEED = 2718

type DatasetRows = Sequence[Mapping[str, object]] | Iterable[Mapping[str, object]]


def materialize_selected_datasets(
    dataset_ids: Sequence[str] | None = None,
    levels: Sequence[LevelConfig] | None = None,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> list[dict[str, object]]:
    """Materialize one or more benchmark datasets from pinned HF manifests."""

    selected_dataset_ids = tuple(dataset_ids) if dataset_ids else _default_dataset_ids()
    selected_levels = tuple(levels) if levels else _default_levels()
    return [
        materialize_dataset(dataset_id, level=level, force=force, dry_run=dry_run)
        for dataset_id in selected_dataset_ids
        for level in selected_levels
    ]


def materialize_dataset(
    dataset_id: str,
    *,
    level: LevelConfig,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    """Fetch, normalize, and materialize one benchmark dataset."""

    manifest = load_dataset_manifest(_dataset_manifest_path(dataset_id))
    if level.level_id not in manifest.supported_levels:
        raise ValueError(
            f"Dataset {dataset_id} does not support benchmark level {level.level_id}"
        )
    output_paths = resolve_dataset_assets(manifest, level_id=level.level_id)
    sidecar_path = output_paths["corpus"].parent / MATERIALIZATION_SIDECAR_NAME
    if not manifest.source:
        raise ValueError(
            f"Dataset {manifest.dataset_id} uses committed local benchmark assets "
            "and does not support benchmark-fetch materialization."
        )
    source_locators = _serialize_source_locators(manifest.source)
    field_mappings = _serialize_field_mappings(manifest.field_mappings)
    materialization_config = _serialize_materialization_config(level)
    resolved_revisions = _resolve_revisions(manifest.source)
    action, reason = _determine_action(
        sidecar_path=sidecar_path,
        output_paths=output_paths,
        source_locators=source_locators,
        field_mappings=field_mappings,
        materialization_config=materialization_config,
        force=force,
    )
    result: dict[str, object] = {
        "dataset_id": manifest.dataset_id,
        "level_id": level.level_id,
        "action": action,
        "reason": reason,
        "dry_run": dry_run,
        "output_dir": output_paths["corpus"].parent,
        "sidecar_path": sidecar_path,
    }
    if dry_run:
        result["planned_paths"] = dict(output_paths)
    if dry_run or action == "skip":
        return result

    started_at = isoformat_utc(None)
    queries_rows = _normalize_rows(
        rows=_load_asset_rows(manifest.source["queries"]),
        id_keys=manifest.field_mappings["query_id_keys"],
        text_keys=manifest.field_mappings["query_text_keys"],
        id_column="qid",
        text_column="query",
        asset_name="queries",
    )
    judgment_rows = _normalize_judgment_rows(
        rows=_load_asset_rows(manifest.source["judgments"]),
        query_id_keys=manifest.field_mappings["judgment_query_id_keys"],
        doc_id_keys=manifest.field_mappings["judgment_doc_id_keys"],
        relevance_keys=manifest.field_mappings["judgment_relevance_keys"],
    )
    selected_queries, selected_judgments = _select_level_queries_and_judgments(
        queries_rows=queries_rows,
        judgment_rows=judgment_rows,
        query_cap=level.query_cap,
    )
    corpus_rows = _normalize_corpus_rows_for_level(
        rows=_load_asset_rows(manifest.source["corpus"], streaming=True),
        id_keys=manifest.field_mappings["corpus_id_keys"],
        text_keys=manifest.field_mappings["corpus_text_keys"],
        judged_doc_ids=_selected_judged_doc_ids(selected_judgments),
        corpus_cap=level.corpus_cap,
    )

    _write_parquet(output_paths["corpus"], corpus_rows, ["docid", "text"])
    _write_parquet(output_paths["queries"], selected_queries, ["qid", "query"])
    _write_judgments_tsv(output_paths["judgments"], selected_judgments)

    completed_at = isoformat_utc(None)
    sidecar_payload = {
        "dataset_id": manifest.dataset_id,
        "source_locators": source_locators,
        "field_mappings": field_mappings,
        "materialization_config": materialization_config,
        "resolved_revisions": resolved_revisions,
        "row_counts": {
            "corpus": len(corpus_rows),
            "queries": len(selected_queries),
            "judgments": len(selected_judgments),
        },
        "timestamps": {
            "started_at": started_at,
            "completed_at": completed_at,
        },
    }
    _ = atomic_write_json(sidecar_path, sidecar_payload)
    result["row_counts"] = sidecar_payload["row_counts"]
    result["materialization"] = sidecar_payload
    return result


def _default_dataset_ids() -> tuple[str, ...]:
    return load_matrix(resolve_repo_asset_path(DEFAULT_MATRIX_PATH)).datasets


def _default_levels() -> tuple[LevelConfig, ...]:
    return tuple(load_matrix(resolve_repo_asset_path(DEFAULT_MATRIX_PATH)).levels.values())


def _dataset_manifest_path(dataset_id: str) -> Path:
    return resolve_repo_asset_path(
        Path("benchmarks/contracts/datasets") / f"{dataset_id}.yaml"
    )


def _load_asset_rows(locator: DatasetSourceLocator, *, streaming: bool = False) -> DatasetRows:
    cache_dir = resolve_repo_asset_path(HF_CACHE_DIR).as_posix()
    if locator.data_files:
        if locator.loader is None:
            raise ValueError(f"Expected loader for file-based source {locator.repo_id!r}")
        return cast(
            DatasetRows,
            load_dataset(
                locator.loader,
                data_files=_resolve_data_files(locator.data_files, revision=locator.revision),
                split="train",
                cache_dir=cache_dir,
                streaming=streaming,
                **cast(dict[str, Any], locator.load_kwargs),
            ),
        )
    if locator.trust_remote_code:
        return cast(
            DatasetRows,
            load_dataset(
                locator.repo_id,
                locator.config,
                split=locator.split,
                revision=locator.revision,
                cache_dir=cache_dir,
                trust_remote_code=True,
                streaming=streaming,
            ),
        )
    return cast(
        DatasetRows,
        load_dataset(
            locator.repo_id,
            locator.config,
            split=locator.split,
            revision=locator.revision,
            cache_dir=cache_dir,
            streaming=streaming,
        ),
    )


def _resolve_data_files(data_files: Sequence[str], *, revision: str) -> list[str]:
    resolved_files: list[str] = []
    fs = HfFileSystem()
    for data_file in data_files:
        pinned_data_file = _pin_hf_data_file_revision(data_file, revision=revision)
        if _looks_like_hf_glob(pinned_data_file):
            repo_paths = sorted(fs.glob(pinned_data_file))
            resolved_files.extend(f"hf://{repo_path}" for repo_path in repo_paths)
        else:
            resolved_files.append(pinned_data_file)
    return resolved_files


def _looks_like_hf_glob(data_file: str) -> bool:
    path = data_file.removeprefix("hf://")
    return path.startswith("datasets/") and any(ch in path for ch in "*?[")


def _pin_hf_data_file_revision(data_file: str, *, revision: str) -> str:
    prefix = "hf://" if data_file.startswith("hf://") else ""
    path = data_file.removeprefix("hf://")
    if not path.startswith("datasets/"):
        return data_file
    parts = path.split("/", 3)
    if len(parts) < 4:
        raise ValueError(f"Expected dataset file path with repository and file: {data_file}")
    repo_segment = parts[2]
    if "@" in repo_segment:
        repo_name, existing_revision = repo_segment.split("@", 1)
        if existing_revision != revision:
            raise ValueError(
                f"Data file revision {existing_revision!r} does not match pinned revision {revision!r}"
            )
        repo_segment = f"{repo_name}@{revision}"
    else:
        repo_segment = f"{repo_segment}@{revision}"
    return f"{prefix}{parts[0]}/{parts[1]}/{repo_segment}/{parts[3]}"


def _determine_action(
    *,
    sidecar_path: Path,
    output_paths: Mapping[str, Path],
    source_locators: Mapping[str, Mapping[str, object]],
    field_mappings: Mapping[str, Sequence[str]],
    materialization_config: Mapping[str, object],
    force: bool,
) -> tuple[str, str]:
    if force:
        return "materialize", "force_requested"
    if not sidecar_path.is_file():
        return "materialize", "missing_sidecar"
    if any(not path.is_file() for path in output_paths.values()):
        return "materialize", "missing_outputs"
    cached_payload = _read_materialization_sidecar(sidecar_path)
    if cached_payload.get("source_locators") != source_locators:
        return "materialize", "source_locators_changed"
    if cached_payload.get("field_mappings") != field_mappings:
        return "materialize", "field_mappings_changed"
    if cached_payload.get("materialization_config") != materialization_config:
        return "materialize", "materialization_config_changed"
    return "skip", "cache_hit"


def _read_materialization_sidecar(path: Path) -> dict[str, object]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected materialization sidecar mapping at {path}")
    return cast(dict[str, object], payload)


def _serialize_source_locators(
    locators: Mapping[str, DatasetSourceLocator],
) -> dict[str, dict[str, object]]:
    return {
        asset_name: {
            "repo_id": locator.repo_id,
            "config": locator.config,
            "split": locator.split,
            "revision": locator.revision,
            **({"loader": locator.loader} if locator.loader is not None else {}),
            **({"data_files": list(locator.data_files)} if locator.data_files else {}),
            **({"load_kwargs": locator.load_kwargs} if locator.load_kwargs else {}),
            **({"trust_remote_code": True} if locator.trust_remote_code else {}),
        }
        for asset_name, locator in locators.items()
    }


def _resolve_revisions(locators: Mapping[str, DatasetSourceLocator]) -> dict[str, str]:
    return {
        asset_name: locator.revision for asset_name, locator in locators.items()
    }


def _serialize_field_mappings(
    field_mappings: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    return {
        field_name: list(keys) for field_name, keys in field_mappings.items()
    }


def _serialize_materialization_config(level: LevelConfig) -> dict[str, object]:
    return {
        "level_id": level.level_id,
        "query_cap": level.query_cap,
        "corpus_cap": level.corpus_cap,
        "query_sampling_seed": QUERY_SAMPLING_SEED,
        "corpus_sampling_seed": CORPUS_SAMPLING_SEED,
    }


def _normalize_rows(
    *,
    rows: DatasetRows,
    id_keys: Sequence[str],
    text_keys: Sequence[str],
    id_column: str,
    text_column: str,
    asset_name: str,
) -> list[dict[str, str]]:
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        raw_id = _require_row_value(row, id_keys, asset_name=asset_name, field_name=id_column)
        raw_text = _require_row_value(
            row,
            text_keys,
            asset_name=asset_name,
            field_name=text_column,
        )
        normalized_rows.append({id_column: str(raw_id), text_column: str(raw_text)})
    return normalized_rows


def _normalize_judgment_rows(
    *,
    rows: DatasetRows,
    query_id_keys: Sequence[str],
    doc_id_keys: Sequence[str],
    relevance_keys: Sequence[str],
) -> list[dict[str, object]]:
    normalized_rows: list[dict[str, object]] = []
    for row in rows:
        qid = _require_row_value(row, query_id_keys, asset_name="judgments", field_name="qid")
        docid = _require_row_value(
            row,
            doc_id_keys,
            asset_name="judgments",
            field_name="docid",
        )
        relevance = _require_row_value(
            row,
            relevance_keys,
            asset_name="judgments",
            field_name="relevance",
        )
        normalized_rows.append(
            {
                "qid": str(qid),
                "docid": str(docid),
                "relevance": relevance,
            }
        )
    return normalized_rows


def _select_level_queries_and_judgments(
    *,
    queries_rows: Sequence[Mapping[str, str]],
    judgment_rows: Sequence[Mapping[str, object]],
    query_cap: int,
) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    query_by_id = {str(row["qid"]): row for row in queries_rows}
    qrel_query_ids = {
        str(row["qid"])
        for row in judgment_rows
        if _is_positive_relevance(row.get("relevance"))
    }
    eligible_query_ids = sorted(set(query_by_id) & qrel_query_ids)
    shuffled_query_ids = list(eligible_query_ids)
    random.Random(QUERY_SAMPLING_SEED).shuffle(shuffled_query_ids)
    selected_query_ids = set(shuffled_query_ids[: min(query_cap, len(shuffled_query_ids))])
    selected_queries = [
        {"qid": str(row["qid"]), "query": str(row["query"])}
        for row in queries_rows
        if str(row["qid"]) in selected_query_ids
    ]
    selected_judgments = [
        dict(row) for row in judgment_rows if str(row["qid"]) in selected_query_ids
    ]
    return selected_queries, selected_judgments


def _selected_judged_doc_ids(
    judgment_rows: Sequence[Mapping[str, object]],
) -> set[str]:
    return {str(row["docid"]) for row in judgment_rows}


def _normalize_corpus_rows_for_level(
    *,
    rows: DatasetRows,
    id_keys: Sequence[str],
    text_keys: Sequence[str],
    judged_doc_ids: set[str],
    corpus_cap: int | None,
) -> list[dict[str, str]]:
    if corpus_cap is None:
        return _normalize_rows(
            rows=rows,
            id_keys=id_keys,
            text_keys=text_keys,
            id_column="docid",
            text_column="text",
            asset_name="corpus",
        )

    fill_size = max(corpus_cap, len(judged_doc_ids)) - len(judged_doc_ids)
    judged_rows: dict[str, dict[str, str]] = {}
    sampled_rows: list[dict[str, str]] = []
    non_judged_seen = 0
    sampler = random.Random(CORPUS_SAMPLING_SEED)
    for row in rows:
        docid = str(_require_row_value(row, id_keys, asset_name="corpus", field_name="docid"))
        text = str(_require_row_value(row, text_keys, asset_name="corpus", field_name="text"))
        corpus_row = {"docid": docid, "text": text}
        if docid in judged_doc_ids:
            judged_rows.setdefault(docid, corpus_row)
            continue
        if fill_size <= 0:
            continue
        non_judged_seen += 1
        if len(sampled_rows) < fill_size:
            sampled_rows.append(corpus_row)
            continue
        replacement_index = sampler.randrange(non_judged_seen)
        if replacement_index < fill_size:
            sampled_rows[replacement_index] = corpus_row
    missing_judged_doc_ids = sorted(judged_doc_ids - set(judged_rows))
    if missing_judged_doc_ids:
        raise ValueError(
            "Materialized corpus is missing judged documents: "
            + ", ".join(missing_judged_doc_ids[:10])
        )
    return [*judged_rows.values(), *sampled_rows]


def _is_positive_relevance(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise TypeError("Benchmark relevance values must be numeric.")
    return float(value) > 0


def _require_row_value(
    row: Mapping[str, object],
    keys: Sequence[str],
    *,
    asset_name: str,
    field_name: str,
) -> object:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    raise ValueError(
        f"Missing {field_name} mapping for {asset_name}; checked keys: {', '.join(keys)}"
    )


def _write_parquet(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    columns: Sequence[str],
) -> None:
    dataset = Dataset.from_dict(
        {column: [row[column] for row in rows] for column in columns}
    )
    _write_dataset_parquet(path, dataset)


def _write_dataset_parquet(path: Path, dataset: Dataset) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.stem}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
        _ = dataset.to_parquet(temp_path.as_posix())
        _ = temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _write_judgments_tsv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["qid", "docid", "relevance"],
        delimiter="\t",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "qid": row["qid"],
                "docid": row["docid"],
                "relevance": row["relevance"],
            }
        )
    _ = atomic_write_bytes(path, buffer.getvalue().encode("utf-8"))
