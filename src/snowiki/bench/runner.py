from __future__ import annotations

import csv
import json
import random
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeGuard, cast

from snowiki.config import resolve_repo_asset_path

from .datasets import (
    load_dataset_manifest,
    missing_materialized_asset_message,
    resolve_dataset_assets,
)
from .metrics import DEFAULT_METRIC_REGISTRY
from .normalization import normalize_query_results
from .specs import (
    BenchmarkQuery,
    BenchmarkRunResult,
    CellResult,
    DatasetManifest,
    EvaluationMatrix,
    MetricResult,
    QueryResult,
)
from .targets import DEFAULT_TARGET_REGISTRY, get_target

type MatrixSelection = Mapping[str, Sequence[str]] | None

EXIT_CODE_SUCCESS = 0
EXIT_CODE_PARTIAL_FAILURE = 1
EXIT_CODE_INVALID_INPUT = 2
QUERY_SAMPLING_SEED = 1729
QUALITY_SLICE_METRIC_IDS = frozenset(
    metric_id
    for metric_id in DEFAULT_METRIC_REGISTRY.list_metrics()
    if not metric_id.startswith("latency_")
)


def run_cell(
    matrix: EvaluationMatrix,
    dataset_id: str,
    level_id: str,
    target_id: str,
    metric_ids: Sequence[str] | None = None,
    *,
    include_diagnostics: bool = False,
) -> CellResult:
    """Run one matrix cell and compute all registered metrics."""

    if dataset_id not in matrix.datasets:
        return _failure_result(
            dataset_id=dataset_id,
            level_id=level_id,
            target_id=target_id,
            message=f"Unknown dataset in matrix: {dataset_id}",
        )
    if level_id not in matrix.levels:
        return _failure_result(
            dataset_id=dataset_id,
            level_id=level_id,
            target_id=target_id,
            message=f"Unknown level in matrix: {level_id}",
        )
    level = matrix.levels[level_id]
    try:
        manifest = load_dataset_manifest(_dataset_manifest_path(dataset_id))
    except (FileNotFoundError, ValueError) as exc:
        return _failure_result(
            dataset_id=dataset_id,
            level_id=level_id,
            target_id=target_id,
            message=f"Failed to load dataset manifest for {dataset_id}: {exc}",
        )
    if level_id not in manifest.supported_levels:
        return _failure_result(
            dataset_id=dataset_id,
            level_id=level_id,
            target_id=target_id,
            message=f"Dataset {dataset_id} does not support benchmark level {level_id}",
        )
    try:
        target = get_target(target_id)
    except KeyError as exc:
        return _failure_result(
            dataset_id=dataset_id,
            level_id=level_id,
            target_id=target_id,
            message=str(exc),
        )
    try:
        all_queries = _load_materialized_queries(manifest, level_id=level_id)
        all_qrels = _load_qrels(manifest, level_id=level_id)
        selected_queries, qrels, eligible_query_count = _select_queries_for_level(
            queries=all_queries,
            qrels=all_qrels,
            query_cap=level.query_cap,
        )
        selected_query_ids = {query.query_id for query in selected_queries}
        execution = (
            target.run(
                manifest=manifest,
                level=level,
                queries=selected_queries,
                include_diagnostics=True,
            )
            if include_diagnostics
            else target.run(
                manifest=manifest,
                level=level,
                queries=selected_queries,
            )
        )
        cache_metadata = _coerce_cache_metadata(execution.get("cache"))
        query_results = tuple(
            result
            for result in _coerce_query_results(execution.get("results", ()))
            if result.query_id in selected_query_ids
        )
        returned_query_ids = {result.query_id for result in query_results}
        if returned_query_ids != selected_query_ids:
            missing_query_ids = sorted(selected_query_ids - returned_query_ids)
            raise ValueError(
                "Benchmark target omitted results for selected queries: "
                + ", ".join(missing_query_ids)
            )
        selected_metric_ids = (
            tuple(metric_ids)
            if metric_ids is not None
            else DEFAULT_METRIC_REGISTRY.list_metrics()
        )
        metrics = tuple(
            DEFAULT_METRIC_REGISTRY.compute(metric_id, query_results, qrels)
            for metric_id in selected_metric_ids
        )
    except Exception as exc:
        return _failure_result(
            dataset_id=dataset_id,
            level_id=level_id,
            target_id=target_id,
            message=f"Cell execution failed: {exc}",
        )
    details: dict[str, object] = {
        "eligible_query_count": eligible_query_count,
        "effective_query_count": len(selected_queries),
        "per_query": _build_per_query_evidence(
            selected_queries,
            query_results,
            qrels,
            metrics,
            include_diagnostics=include_diagnostics,
        ),
        "slices": _build_slice_evidence(selected_queries, metrics),
        "sampling_seed": QUERY_SAMPLING_SEED,
    }
    if level.corpus_cap is not None:
        details["run_classification"] = "smoke"
        details["public_baseline_comparable"] = False
    if cache_metadata is not None:
        details["cache"] = cache_metadata
    return CellResult(
        dataset_id=dataset_id,
        level_id=level_id,
        target_id=target_id,
        metrics=metrics,
        status="success",
        details=details,
    )


def run_matrix(
    matrix: EvaluationMatrix,
    selection: MatrixSelection = None,
    *,
    include_diagnostics: bool = False,
) -> BenchmarkRunResult:
    """Run the selected matrix cells through the lean runner skeleton."""

    result, _ = run_matrix_with_exit_code(
        matrix=matrix,
        selection=selection,
        include_diagnostics=include_diagnostics,
    )
    return result


def run_matrix_with_exit_code(
    matrix: EvaluationMatrix,
    selection: MatrixSelection = None,
    *,
    fail_fast: bool = False,
    include_diagnostics: bool = False,
) -> tuple[BenchmarkRunResult, int]:
    """Run the selected matrix cells and return the result plus exit code."""

    validation_error, normalized_selection = _validate_selection(matrix, selection)
    if validation_error is not None:
        return (
            BenchmarkRunResult(
                matrix_id=matrix.matrix_id,
                failures=(validation_error,),
                details={"selection": normalized_selection},
            ),
            EXIT_CODE_INVALID_INPUT,
        )

    cells: list[CellResult] = []
    failures: list[str] = []
    for dataset_id in normalized_selection["dataset_ids"]:
        for level_id in normalized_selection["level_ids"]:
            for target_id in normalized_selection["target_ids"]:
                cell = run_cell(
                    matrix=matrix,
                    dataset_id=dataset_id,
                    level_id=level_id,
                    target_id=target_id,
                    metric_ids=normalized_selection["metric_ids"],
                    include_diagnostics=include_diagnostics,
                )
                cells.append(cell)
                if cell.error_message is None:
                    continue
                failures.append(cell.error_message)
                if fail_fast:
                    return (
                        BenchmarkRunResult(
                            matrix_id=matrix.matrix_id,
                            cells=tuple(cells),
                            failures=tuple(failures),
                            details={"selection": normalized_selection},
                        ),
                        EXIT_CODE_PARTIAL_FAILURE,
                    )

    exit_code = EXIT_CODE_SUCCESS if not failures else EXIT_CODE_PARTIAL_FAILURE
    return (
        BenchmarkRunResult(
            matrix_id=matrix.matrix_id,
            cells=tuple(cells),
            failures=tuple(failures),
            details={"selection": normalized_selection},
        ),
        exit_code,
    )


def _failure_result(
    *,
    dataset_id: str,
    level_id: str,
    target_id: str,
    message: str,
) -> CellResult:
    return CellResult(
        dataset_id=dataset_id,
        level_id=level_id,
        target_id=target_id,
        status="failed",
        error_message=message,
    )


def _validate_selection(
    matrix: EvaluationMatrix,
    selection: MatrixSelection,
) -> tuple[str | None, dict[str, list[str]]]:
    normalized_selection = {
        "dataset_ids": list(selection.get("dataset_ids", matrix.datasets))
        if selection
        else list(matrix.datasets),
        "level_ids": list(selection.get("level_ids", tuple(matrix.levels)))
        if selection
        else list(matrix.levels),
        "target_ids": list(selection.get("target_ids", ())) if selection else [],
        "metric_ids": list(selection.get("metric_ids", ())) if selection else [],
    }
    if not matrix.datasets:
        return "Benchmark matrix must define at least one dataset.", normalized_selection
    if not matrix.levels:
        return "Benchmark matrix must define at least one level.", normalized_selection
    if not normalized_selection["target_ids"]:
        return "No benchmark targets selected.", normalized_selection

    invalid_dataset_ids = [
        dataset_id
        for dataset_id in normalized_selection["dataset_ids"]
        if dataset_id not in matrix.datasets
    ]
    if invalid_dataset_ids:
        return (
            f"Unknown dataset selection: {', '.join(sorted(set(invalid_dataset_ids)))}",
            normalized_selection,
        )

    invalid_level_ids = [
        level_id
        for level_id in normalized_selection["level_ids"]
        if level_id not in matrix.levels
    ]
    if invalid_level_ids:
        return (
            f"Unknown level selection: {', '.join(sorted(set(invalid_level_ids)))}",
            normalized_selection,
        )

    known_target_ids = {
        spec.target_id for spec in DEFAULT_TARGET_REGISTRY.list_targets()
    }
    invalid_target_ids = [
        target_id
        for target_id in normalized_selection["target_ids"]
        if target_id not in known_target_ids
    ]
    if invalid_target_ids:
        return (
            f"Unknown target selection: {', '.join(sorted(set(invalid_target_ids)))}",
            normalized_selection,
        )

    if not normalized_selection["metric_ids"]:
        normalized_selection["metric_ids"] = list(DEFAULT_METRIC_REGISTRY.list_metrics())

    known_metric_ids = set(DEFAULT_METRIC_REGISTRY.list_metrics())
    invalid_metric_ids = [
        metric_id
        for metric_id in normalized_selection["metric_ids"]
        if metric_id not in known_metric_ids
    ]
    if invalid_metric_ids:
        return (
            f"Unknown metric selection: {', '.join(sorted(set(invalid_metric_ids)))}",
            normalized_selection,
        )

    return None, normalized_selection


def _dataset_manifest_path(dataset_id: str) -> Path:
    return resolve_repo_asset_path(
        Path("benchmarks/contracts/datasets") / f"{dataset_id}.yaml"
    )


def _load_materialized_queries(
    manifest: DatasetManifest,
    *,
    level_id: str | None = None,
) -> tuple[BenchmarkQuery, ...]:
    queries_path = resolve_dataset_assets(manifest, level_id=level_id)["queries"]
    if not queries_path.is_file():
        raise FileNotFoundError(
            missing_materialized_asset_message(
                manifest,
                asset_name="queries",
                path=queries_path,
                level_id=level_id,
            )
        )
    if queries_path.suffix == ".json":
        return _load_json_queries(queries_path)
    from datasets import load_dataset

    dataset = load_dataset("parquet", data_files=str(queries_path), split="train")
    query_id_keys = manifest.field_mappings.get("query_id_keys", ())
    query_text_keys = manifest.field_mappings.get("query_text_keys", ())
    queries: list[BenchmarkQuery] = []
    for row in dataset:
        if not isinstance(row, Mapping):
            raise ValueError(f"Expected query row mappings in {queries_path}")
        query_id = _first_value(row, query_id_keys, fallback_keys=("qid",))
        query_text = _first_value(row, query_text_keys, fallback_keys=("query",))
        if query_id is None or query_text is None:
            raise ValueError(f"Missing query field mapping in {queries_path}")
        queries.append(
            BenchmarkQuery(query_id=str(query_id), query_text=str(query_text))
        )
    return tuple(queries)


def _load_json_queries(queries_path: Path) -> tuple[BenchmarkQuery, ...]:
    payload = json.loads(queries_path.read_text(encoding="utf-8"))
    rows: object
    if isinstance(payload, Mapping) and "queries" in payload:
        rows = payload["queries"]
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError(f"Expected benchmark query rows in {queries_path}")
    queries: list[BenchmarkQuery] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError(f"Expected query row mappings in {queries_path}")
        query_id = row.get("id") or row.get("qid")
        query_text = row.get("text") or row.get("query")
        if query_id is None or query_text is None:
            raise ValueError(f"Missing query id/text in {queries_path}")
        group = row.get("group")
        kind = row.get("kind")
        queries.append(
            BenchmarkQuery(
                query_id=str(query_id),
                query_text=str(query_text),
                group=str(group) if group not in (None, "") else None,
                kind=str(kind) if kind not in (None, "") else None,
                tags=_coerce_query_tags(row.get("tags"), queries_path),
            )
        )
    return tuple(queries)


def _select_queries_for_level(
    *,
    queries: Sequence[BenchmarkQuery],
    qrels: Mapping[str, set[str]],
    query_cap: int,
) -> tuple[tuple[BenchmarkQuery, ...], dict[str, set[str]], int]:
    query_by_id: dict[str, BenchmarkQuery] = {}
    for query in queries:
        query_by_id.setdefault(query.query_id, query)
    eligible_query_ids = sorted(set(query_by_id) & set(qrels))
    shuffled_query_ids = list(eligible_query_ids)
    random.Random(QUERY_SAMPLING_SEED).shuffle(shuffled_query_ids)
    selected_query_ids = tuple(shuffled_query_ids[: min(query_cap, len(shuffled_query_ids))])
    return (
        tuple(query_by_id[query_id] for query_id in selected_query_ids),
        {query_id: set(qrels[query_id]) for query_id in selected_query_ids},
        len(eligible_query_ids),
    )


def _coerce_query_results(raw_results: object) -> tuple[QueryResult, ...]:
    return normalize_query_results(raw_results)


def _coerce_cache_metadata(raw_cache: object) -> dict[str, object] | None:
    if raw_cache is None:
        return None
    if not isinstance(raw_cache, Mapping):
        raise TypeError("Benchmark target cache metadata must be a mapping.")
    metadata: dict[str, object] = {}
    for key, value in raw_cache.items():
        if not isinstance(key, str):
            raise TypeError("Benchmark target cache metadata keys must be strings.")
        metadata[key] = value
    return metadata


def _load_qrels(
    manifest: DatasetManifest,
    *,
    level_id: str | None = None,
) -> dict[str, set[str]]:
    judgments_path = resolve_dataset_assets(manifest, level_id=level_id)["judgments"]
    if not judgments_path.is_file():
        raise FileNotFoundError(
            missing_materialized_asset_message(
                manifest,
                asset_name="judgments",
                path=judgments_path,
                level_id=level_id,
            )
        )
    if judgments_path.suffix == ".json":
        return _load_json_qrels(judgments_path, manifest.field_mappings)
    return _load_delimited_qrels(judgments_path, manifest.field_mappings)


def _coerce_qrels(raw_qrels: object) -> dict[str, set[str]]:
    if not isinstance(raw_qrels, Mapping):
        raise TypeError(
            "Benchmark qrels must be a mapping of query IDs to relevant doc IDs."
        )
    normalized: dict[str, set[str]] = {}
    for query_id, relevant_doc_ids in raw_qrels.items():
        if not isinstance(query_id, str):
            raise TypeError("Benchmark qrels query IDs must be strings.")
        if not _is_doc_id_collection(relevant_doc_ids) or isinstance(
            relevant_doc_ids,
            str | bytes,
        ):
            raise TypeError("Benchmark qrels values must be collections of doc IDs.")
        normalized[query_id] = {str(doc_id) for doc_id in relevant_doc_ids}
    return normalized


def _load_json_qrels(
    judgments_path: Path,
    field_mappings: Mapping[str, tuple[str, ...]],
) -> dict[str, set[str]]:
    payload = json.loads(judgments_path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping) and "judgments" in payload:
        return _coerce_qrels(cast(Mapping[str, object], payload["judgments"]))
    if isinstance(payload, dict):
        return _coerce_qrels(payload)
    if not isinstance(payload, list):
        raise ValueError(f"Expected qrels JSON list or mapping in {judgments_path}")
    return _rows_to_qrels(payload, field_mappings, judgments_path)


def _load_delimited_qrels(
    judgments_path: Path,
    field_mappings: Mapping[str, tuple[str, ...]],
) -> dict[str, set[str]]:
    delimiter = "\t" if judgments_path.suffix == ".tsv" else ","
    with judgments_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    return _rows_to_qrels(rows, field_mappings, judgments_path)


def _rows_to_qrels(
    rows: Sequence[Mapping[str, object]],
    field_mappings: Mapping[str, tuple[str, ...]],
    source_path: Path,
) -> dict[str, set[str]]:
    query_id_keys = field_mappings.get("judgment_query_id_keys", ())
    doc_id_keys = field_mappings.get("judgment_doc_id_keys", ())
    relevance_keys = field_mappings.get("judgment_relevance_keys", ())
    qrels: dict[str, set[str]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError(f"Expected qrels row mappings in {source_path}")
        query_id = _first_value(row, query_id_keys, fallback_keys=("qid",))
        doc_id = _first_value(row, doc_id_keys, fallback_keys=("docid",))
        relevance = _first_value(
            row,
            relevance_keys,
            fallback_keys=("relevance",),
        )
        if query_id is None or doc_id is None:
            raise ValueError(f"Missing qrels field mapping in {source_path}")
        if relevance is not None and _coerce_float(relevance) <= 0:
            continue
        qrels.setdefault(str(query_id), set()).add(str(doc_id))
    return qrels


def _first_value(
    row: Mapping[str, object],
    keys: Sequence[str],
    *,
    fallback_keys: Sequence[str] = (),
) -> object | None:
    for key in (*keys, *fallback_keys):
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _build_per_query_evidence(
    queries: Sequence[BenchmarkQuery],
    query_results: Sequence[QueryResult],
    qrels: Mapping[str, set[str]],
    metrics: Sequence[MetricResult],
    *,
    include_diagnostics: bool = False,
) -> dict[str, dict[str, object]]:
    metric_lookup: dict[str, Mapping[str, object]] = {}
    for metric in metrics:
        per_query = metric.details.get("per_query")
        if isinstance(per_query, Mapping):
            metric_lookup[metric.metric_id] = cast(Mapping[str, object], per_query)
    query_ids = {result.query_id for result in query_results} | set(qrels)
    evidence: dict[str, dict[str, object]] = {}
    query_by_id = {query.query_id: query for query in queries}
    query_results_by_id = {result.query_id: result for result in query_results}
    for query_id in sorted(query_ids):
        query = query_by_id.get(query_id)
        query_result = query_results_by_id.get(query_id)
        evidence[query_id] = {
            "query": {
                "group": query.group if query and query.group else None,
                "kind": query.kind if query and query.kind else None,
                "tags": list(query.tags) if query else [],
            },
            "ranked_doc_ids": list(query_result.ranked_doc_ids) if query_result else [],
            "relevant_doc_ids": sorted(qrels.get(query_id, set())),
            "latency_ms": query_result.latency_ms if query_result else None,
            "metrics": {
                metric_id: per_query_scores.get(query_id)
                for metric_id, per_query_scores in metric_lookup.items()
            },
        }
        if include_diagnostics and query_result and query_result.diagnostics:
            diagnostics = query_result.diagnostics
            token_explain_trace = diagnostics.get("token_explain_trace")
            if isinstance(token_explain_trace, Mapping):
                evidence[query_id]["token_explain_trace"] = token_explain_trace
                evidence[query_id]["diagnostics"] = {
                    key: value
                    for key, value in diagnostics.items()
                    if key != "token_explain_trace"
                }
            else:
                evidence[query_id]["diagnostics"] = diagnostics
    return evidence


def _build_slice_evidence(
    selected_queries: Sequence[BenchmarkQuery],
    metrics: Sequence[MetricResult],
) -> dict[str, dict[str, object]]:
    metric_lookup: dict[str, Mapping[str, object]] = {}
    for metric in metrics:
        per_query = metric.details.get("per_query")
        if isinstance(per_query, Mapping):
            metric_lookup[metric.metric_id] = cast(Mapping[str, object], per_query)
    slice_query_ids: dict[str, set[str]] = {"all": set()}
    for query in selected_queries:
        slice_query_ids["all"].add(query.query_id)
        if query.group:
            slice_query_ids.setdefault(f"group:{query.group}", set()).add(query.query_id)
        if query.kind:
            slice_query_ids.setdefault(f"kind:{query.kind}", set()).add(query.query_id)
        for tag in query.tags:
            slice_query_ids.setdefault(f"tag:{tag}", set()).add(query.query_id)

    evidence: dict[str, dict[str, object]] = {}
    for slice_id, query_ids in sorted(slice_query_ids.items()):
        metric_values: dict[str, float | None] = {}
        evaluated_counts: dict[str, int] = {}
        for metric_id, per_query_scores in metric_lookup.items():
            if metric_id not in QUALITY_SLICE_METRIC_IDS:
                continue
            values = tuple(
                float(value)
                for query_id in query_ids
                if isinstance((value := per_query_scores.get(query_id)), int | float)
            )
            metric_values[metric_id] = _mean_float(values)
            evaluated_counts[metric_id] = len(values)
        evidence[slice_id] = {
            "query_count": len(query_ids),
            "metrics": metric_values,
            "evaluated_queries": evaluated_counts,
        }
    return evidence


def _coerce_query_tags(raw_tags: object, source_path: Path) -> tuple[str, ...]:
    if raw_tags in (None, ""):
        return ()
    if not isinstance(raw_tags, Sequence) or isinstance(raw_tags, str | bytes):
        raise ValueError(f"Expected query tags list in {source_path}")
    return tuple(str(tag) for tag in raw_tags if str(tag))


def _mean_float(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _coerce_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise TypeError("Benchmark relevance values must be numeric.")
    return float(value)


def _is_doc_id_collection(
    value: object,
) -> TypeGuard[Sequence[object] | set[object] | frozenset[object]]:
    return isinstance(value, Sequence | set | frozenset)
