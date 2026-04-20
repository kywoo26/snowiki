from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from statistics import fmean
from typing import Literal, Protocol, cast

from .baselines import run_baseline_comparison
from .corpus import BenchmarkCorpusManifest
from .matrix import CANDIDATE_MATRIX
from .models import (
    BENCHMARK_ASSET_MANIFEST_LIST_ADAPTER,
    BenchmarkAssetManifest,
    BenchmarkReport,
    CandidateMatrixReport,
)
from .phase1_correctness import CheckIssue, ValidationResult, validate_phase1_workspace
from .phase1_latency import run_phase1_latency_evaluation
from .presets import get_preset

_RENDER = import_module("snowiki.bench.render")
_VERDICT = import_module("snowiki.bench.verdict")

_PER_QUERY_DETAIL_LIMIT = 20


def _coerce_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


class _RenderReportText(Protocol):
    def __call__(self, report: dict[str, object]) -> str: ...


class _ReportToInt(Protocol):
    def __call__(self, report: dict[str, object]) -> int: ...


class _ReportToDict(Protocol):
    def __call__(
        self, report: dict[str, object], *, tier: str | None = None
    ) -> dict[str, object]: ...


class _ThresholdEntries(Protocol):
    def __call__(self, report: dict[str, object]) -> list[dict[str, object]]: ...


class _ThresholdPolicy(Protocol):
    def __call__(self) -> list[dict[str, object]]: ...


class _RetrievalThresholdPolicy(Protocol):
    def __call__(self) -> dict[str, object]: ...


def _legacy_retrieval_payload(
    retrieval: BenchmarkReport | dict[str, object],
) -> dict[str, object]:
    if isinstance(retrieval, BenchmarkReport):
        return {
            **retrieval.to_legacy_dict(),
            **_manifest_payload_from_model(retrieval),
        }
    return {**retrieval, **_validated_manifest_payload(retrieval)}


def _manifest_payload_from_model(retrieval: BenchmarkReport) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field_name in ("corpus_assets", "query_assets", "judgment_assets"):
        manifests = cast(list[BenchmarkAssetManifest], getattr(retrieval, field_name))
        visible_manifests = [
            manifest for manifest in manifests if not _is_hidden_holdout_asset(manifest)
        ]
        if visible_manifests:
            payload[field_name] = [
                manifest.to_report_dict() for manifest in visible_manifests
            ]
    return payload


def _is_hidden_holdout_asset(manifest: BenchmarkAssetManifest) -> bool:
    return manifest.provenance.visibility_tier == "hidden_holdout"


def _asset_counts_by_visibility(manifests: list[BenchmarkAssetManifest]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for manifest in manifests:
        tier = manifest.provenance.visibility_tier
        counts[tier] = counts.get(tier, 0) + 1
    return counts


def _asset_counts_by_source_class(manifests: list[BenchmarkAssetManifest]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for manifest in manifests:
        source_class = manifest.provenance.source_class
        counts[source_class] = counts.get(source_class, 0) + 1
    return counts


def _asset_counts_by_authoring_method(
    manifests: list[BenchmarkAssetManifest],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for manifest in manifests:
        authoring_method = manifest.provenance.authoring_method
        counts[authoring_method] = counts.get(authoring_method, 0) + 1
    return counts


def _asset_counts_by_authority_tier(
    manifests: list[BenchmarkAssetManifest],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for manifest in manifests:
        authority_tier = manifest.provenance.authority_tier
        counts[authority_tier] = counts.get(authority_tier, 0) + 1
    return counts


def _redact_hidden_holdout_retrieval_payload(
    retrieval: dict[str, object],
) -> dict[str, object]:
    redacted = dict(retrieval)
    baselines = redacted.get("baselines")
    if isinstance(baselines, dict):
        sealed_baselines: dict[str, object] = {}
        for baseline_name, baseline_payload in baselines.items():
            if not isinstance(baseline_payload, dict):
                sealed_baselines[str(baseline_name)] = baseline_payload
                continue
            sealed_baseline = dict(baseline_payload)
            sealed_baseline["queries"] = {}
            quality = sealed_baseline.get("quality")
            if isinstance(quality, dict):
                sealed_quality = dict(quality)
                overall = sealed_quality.get("overall")
                if isinstance(overall, dict):
                    sealed_overall = dict(overall)
                    sealed_overall["per_query"] = []
                    sealed_quality["overall"] = sealed_overall
                slices = sealed_quality.get("slices")
                if isinstance(slices, dict):
                    sealed_slices = dict(slices)
                    for slice_name in ("group", "kind", "subset"):
                        slice_values = sealed_slices.get(slice_name)
                        if not isinstance(slice_values, dict):
                            continue
                        sealed_slice_values: dict[str, object] = {}
                        for key, slice_payload in slice_values.items():
                            if not isinstance(slice_payload, dict):
                                sealed_slice_values[str(key)] = slice_payload
                                continue
                            sealed_slice_payload = dict(slice_payload)
                            sealed_slice_payload["per_query"] = []
                            sealed_slice_values[str(key)] = sealed_slice_payload
                        sealed_slices[slice_name] = sealed_slice_values
                    sealed_quality["slices"] = sealed_slices
                sealed_baseline["quality"] = sealed_quality
            sealed_baselines[str(baseline_name)] = sealed_baseline
        redacted["baselines"] = sealed_baselines
    redacted["sealed_holdout"] = True
    return redacted


def _dataset_payload_from_manifest(
    manifest: BenchmarkCorpusManifest | None, *, dataset_name: str
) -> dict[str, object]:
    if manifest is None:
        return {
            "id": dataset_name,
            "name": "Phase 1 regression fixtures",
            "tier": "regression",
            "description": "Deterministic local regression fixtures used for candidate-screening benchmark runs.",
        }

    payload: dict[str, object] = {
        "id": manifest.dataset_id or dataset_name,
        "name": manifest.dataset_name or dataset_name,
        "tier": manifest.tier,
    }
    if manifest.dataset_description:
        payload["description"] = manifest.dataset_description
    if manifest.dataset_metadata:
        payload["metadata"] = dict(manifest.dataset_metadata)
    if manifest.corpus_assets:
        provenance = manifest.corpus_assets[0].provenance
        if provenance.visibility_tier == "hidden_holdout":
            payload["provenance_status"] = {
                "visibility_tier": provenance.visibility_tier,
                "authority_tier": provenance.authority_tier,
                "sealed": True,
                "dev_report_excludes_assets": True,
            }
        else:
            payload["provenance"] = provenance.model_dump(mode="json")
    return payload


def _dataset_sample_metadata(dataset_payload: dict[str, object]) -> dict[str, object]:
    raw_metadata = dataset_payload.get("metadata")
    if not isinstance(raw_metadata, dict):
        return {}
    dataset_metadata = cast(dict[str, object], raw_metadata)

    sample_metadata: dict[str, object] = {}
    for field_name in ("sample_mode", "queries_available", "sample_size"):
        if field_name in dataset_metadata:
            sample_metadata[field_name] = dataset_metadata[field_name]
    return sample_metadata


def _attach_manifest_assets(
    retrieval: BenchmarkReport,
    manifest: BenchmarkCorpusManifest | None,
) -> BenchmarkReport:
    if manifest is None:
        return retrieval
    return retrieval.model_copy(
        update={
            "corpus_assets": list(manifest.corpus_assets),
            "query_assets": list(manifest.query_assets),
            "judgment_assets": list(manifest.judgment_assets),
            "pooled_reviews": list(manifest.pooled_reviews),
            "audit_samples": list(manifest.audit_samples),
            "review_policy": dict(manifest.review_policy or {}),
            "audit_policy": dict(manifest.audit_policy or {}),
        }
    )


def _manifest_corpus_summary(
    retrieval: BenchmarkReport,
    manifest: BenchmarkCorpusManifest,
) -> dict[str, object]:
    summary = retrieval.corpus.to_legacy_dict() if retrieval.corpus else {}
    return {
        **summary,
        "documents_seeded": len(manifest.documents),
        "queries_evaluated": summary.get("queries_evaluated", len(manifest.queries or [])),
    }


def _manifest_protocol(
    *,
    isolated_root: bool,
) -> dict[str, object]:
    return {
        "isolated_root": isolated_root,
        "warmups": 0,
        "repetitions": 0,
        "query_mode": "lexical",
        "dataset_mode": "manifest",
    }


def _validated_manifest_payload(retrieval: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field_name in ("corpus_assets", "query_assets", "judgment_assets"):
        manifests = retrieval.get(field_name)
        if manifests is None:
            continue
        validated = BENCHMARK_ASSET_MANIFEST_LIST_ADAPTER.validate_python(manifests)
        visible_manifests = [
            manifest for manifest in validated if not _is_hidden_holdout_asset(manifest)
        ]
        if visible_manifests:
            payload[field_name] = [
                manifest.to_report_dict() for manifest in visible_manifests
            ]
    return payload


def _candidate_matrix_payload(
    retrieval: BenchmarkReport | dict[str, object],
) -> dict[str, object]:
    if isinstance(retrieval, BenchmarkReport):
        if retrieval.candidate_matrix is not None:
            return retrieval.candidate_matrix.to_report_dict()
        return _default_candidate_matrix_report().to_report_dict()

    candidate_matrix = retrieval.get("candidate_matrix")
    if isinstance(candidate_matrix, dict):
        return cast(dict[str, object], candidate_matrix)
    return _default_candidate_matrix_report().to_report_dict()


def _default_candidate_matrix_report() -> CandidateMatrixReport:
    return CandidateMatrixReport.model_validate(
        {
            "candidates": [
                candidate.model_dump(mode="json") for candidate in CANDIDATE_MATRIX
            ]
        }
    )


def _limit_sequence_detail(
    payload: dict[str, object],
    *,
    key: str,
    limit: int,
) -> int:
    value = payload.get(key)
    if isinstance(value, list) and len(value) > limit:
        payload[key] = value[:limit]
        return len(value) - limit
    if isinstance(value, dict) and len(value) > limit:
        payload[key] = dict(list(value.items())[:limit])
        return len(value) - limit
    return 0


def _bound_quality_payload(
    quality: dict[str, object],
    *,
    limit: int,
) -> int:
    removed_entries = 0
    overall = quality.get("overall")
    if isinstance(overall, dict):
        removed_entries += _limit_sequence_detail(
            cast(dict[str, object], overall),
            key="per_query",
            limit=limit,
        )

    slices = quality.get("slices")
    if not isinstance(slices, dict):
        return removed_entries

    for slice_group in slices.values():
        if not isinstance(slice_group, dict):
            continue
        for metrics in slice_group.values():
            if not isinstance(metrics, dict):
                continue
            removed_entries += _limit_sequence_detail(
                cast(dict[str, object], metrics),
                key="per_query",
                limit=limit,
            )
    return removed_entries


def _bound_retrieval_payload(
    retrieval: dict[str, object],
    *,
    query_count: int,
    tier: str,
) -> dict[str, object]:
    if tier == "regression" or query_count <= _PER_QUERY_DETAIL_LIMIT:
        return {
            "applied": False,
            "per_query_detail_limit": None,
            "entries_removed": 0,
            "baselines_truncated": [],
        }

    baselines = retrieval.get("baselines")
    if not isinstance(baselines, dict):
        return {
            "applied": False,
            "per_query_detail_limit": None,
            "entries_removed": 0,
            "baselines_truncated": [],
        }

    entries_removed = 0
    truncated_baselines: list[str] = []
    for baseline_name, baseline_payload in baselines.items():
        if not isinstance(baseline_payload, dict):
            continue
        baseline_dict = cast(dict[str, object], baseline_payload)
        baseline_removed = 0
        baseline_removed += _limit_sequence_detail(
            baseline_dict,
            key="queries",
            limit=_PER_QUERY_DETAIL_LIMIT,
        )
        quality = baseline_dict.get("quality")
        if isinstance(quality, dict):
            baseline_removed += _bound_quality_payload(
                cast(dict[str, object], quality),
                limit=_PER_QUERY_DETAIL_LIMIT,
            )
        if baseline_removed > 0:
            truncated_baselines.append(str(baseline_name))
            entries_removed += baseline_removed

    return {
        "applied": entries_removed > 0,
        "per_query_detail_limit": _PER_QUERY_DETAIL_LIMIT if entries_removed > 0 else None,
        "entries_removed": entries_removed,
        "baselines_truncated": truncated_baselines,
    }


def generate_audit_report(report: BenchmarkReport) -> dict[str, object]:
    manifests = [
        *report.corpus_assets,
        *report.query_assets,
        *report.judgment_assets,
    ]
    if not manifests and not report.audit_samples and not report.pooled_reviews:
        return {}

    agreement_scores = [sample.agreement_score for sample in report.audit_samples]
    contributing_systems = sorted(
        {
            system_name
            for pooled_review in report.pooled_reviews
            for system_name in pooled_review.judgments_from_systems
        }
    )
    disagreement_count = sum(
        1 for pooled_review in report.pooled_reviews if pooled_review.disagreement_flag
    )
    hidden_count = sum(1 for manifest in manifests if _is_hidden_holdout_asset(manifest))

    return {
        "policy": dict(report.audit_policy),
        "samples": {
            "count": len(report.audit_samples),
            "reviewer_assignments": sum(
                sample.reviewer_count for sample in report.audit_samples
            ),
            "mean_agreement_score": (
                round(fmean(agreement_scores), 3) if agreement_scores else None
            ),
        },
        "pooled_review": {
            "query_count": len(report.pooled_reviews),
            "systems": contributing_systems,
            "disagreement_count": disagreement_count,
            "blind_human_adjudication": bool(
                report.review_policy.get("blind_human_adjudication", False)
            ),
            "disagreement_policy": report.review_policy.get("disagreement_policy"),
        },
        "provenance_quota": {
            "asset_count": len(manifests),
            "hidden_holdout_asset_count": hidden_count,
            "by_visibility_tier": _asset_counts_by_visibility(manifests),
            "by_source_class": _asset_counts_by_source_class(manifests),
            "by_authoring_method": _asset_counts_by_authoring_method(manifests),
            "by_authority_tier": _asset_counts_by_authority_tier(manifests),
            "quota_dimensions": list(
                cast(
                    list[str],
                    report.audit_policy.get("provenance_quota_dimensions", []),
                )
            ),
        },
    }


render_report_text = cast(_RenderReportText, _RENDER.render_report_text)
benchmark_verdict = cast(_ReportToDict, _VERDICT.benchmark_verdict)
benchmark_exit_code = cast(_ReportToInt, _VERDICT.benchmark_exit_code)
informational_warning_count = cast(_ReportToInt, _VERDICT.informational_warning_count)
performance_threshold_failure_count = cast(
    _ReportToInt, _VERDICT.performance_threshold_failure_count
)
retrieval_threshold_failure_count = cast(
    _ReportToInt, _VERDICT.retrieval_threshold_failure_count
)
structural_failure_count = cast(_ReportToInt, _VERDICT.structural_failure_count)
_performance_threshold_entries = cast(
    _ThresholdEntries, _VERDICT._performance_threshold_entries
)
_performance_threshold_policy = cast(
    _ThresholdPolicy, _VERDICT._performance_threshold_policy
)
_retrieval_threshold_policy = cast(
    _RetrievalThresholdPolicy, _VERDICT._retrieval_threshold_policy
)


def generate_report(
    root: Path,
    *,
    preset_name: str,
    manifest: BenchmarkCorpusManifest | None = None,
    dataset_name: str = "regression",
    isolated_root: bool = True,
    latency_sample: Literal["exhaustive", "stratified", "fixed_sample"] | None = None,
) -> dict[str, object]:
    preset = get_preset(preset_name)
    structural = _structural_validation_summary(validate_phase1_workspace(root))
    dataset_payload = _dataset_payload_from_manifest(manifest, dataset_name=dataset_name)
    dataset_tier = str(dataset_payload.get("tier", "regression"))
    performance = run_phase1_latency_evaluation(
        root,
        preset=preset,
        manifest=manifest,
        dataset_name=dataset_name,
        latency_sample=latency_sample,
    )
    protocol = cast(dict[str, object], performance["protocol"])
    protocol["isolated_root"] = isolated_root
    performance_payload = cast(dict[str, object], performance["performance"])
    sampling_policy = cast(dict[str, object], protocol.get("sampling_policy", {}))
    if manifest is None:
        retrieval_result = run_baseline_comparison(root, preset)
        corpus_summary = cast(dict[str, object], performance["corpus"])
    else:
        retrieval_result = run_baseline_comparison(
            root,
            preset,
            queries_path=manifest.queries_path,
            judgments_path=manifest.judgments_path,
            queries_data=manifest.queries,
            judgments_data=manifest.judgments,
            use_generic_scoring=True,
        )
        latency_corpus = cast(dict[str, object], performance["corpus"])
        corpus_summary = {
            **_manifest_corpus_summary(retrieval_result, manifest),
            "dataset": dataset_name,
            "tier": dataset_tier,
            "latency_queries_available": latency_corpus.get("queries_available"),
            "latency_queries_evaluated": latency_corpus.get("queries_evaluated"),
        }
    performance_threshold_policy = (
        _performance_threshold_policy()
        if dataset_tier == "regression"
        and str(sampling_policy.get("mode", "exhaustive")) == "exhaustive"
        else []
    )
    retrieval_result = _attach_manifest_assets(retrieval_result, manifest)
    retrieval = _legacy_retrieval_payload(retrieval_result)
    if manifest is not None and manifest.tier == "hidden_holdout":
        retrieval = _redact_hidden_holdout_retrieval_payload(retrieval)
    report_limits = _bound_retrieval_payload(
        retrieval,
        query_count=_coerce_int(corpus_summary.get("queries_evaluated", 0)),
        tier=dataset_tier,
    )
    report_metadata: dict[str, object] = {
        "dataset_id": dataset_payload.get("id", dataset_name),
        "dataset_name": dataset_payload.get("name", dataset_name),
        "dataset_tier": dataset_tier,
        "latency_sampling_policy": sampling_policy,
        "report_limits": report_limits,
    }
    report_metadata.update(_dataset_sample_metadata(dataset_payload))
    report: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "report_version": "1.3",
        "dataset": dataset_payload,
        "metadata": report_metadata,
        "preset": {
            "name": preset.name,
            "description": preset.description,
            "query_kinds": list(preset.query_kinds),
            "top_k": preset.top_k,
            "top_ks": list(preset.top_ks),
        },
        "structural": structural,
        "performance": performance_payload,
        "performance_threshold_policy": performance_threshold_policy,
        "corpus": corpus_summary,
        "protocol": protocol,
        "retrieval": {
            **retrieval,
            "candidate_matrix": _candidate_matrix_payload(retrieval_result),
            "threshold_policy": _retrieval_threshold_policy(),
        },
    }
    if isinstance(retrieval_result, BenchmarkReport):
        has_audit_data = bool(
            retrieval_result.audit_samples or retrieval_result.pooled_reviews
        )
    else:
        has_audit_data = False
    if has_audit_data:
        report["audit"] = generate_audit_report(retrieval_result)
    report["performance_thresholds"] = _performance_threshold_entries(report)
    report["benchmark_verdict"] = benchmark_verdict(report, tier=dataset_tier)
    return report


def _structural_issue_entry(stage: str, issue: CheckIssue) -> dict[str, object]:
    entry: dict[str, object] = {
        "stage": stage,
        "code": issue["code"],
        "severity": issue["severity"],
        "path": issue["path"],
        "message": issue["message"],
    }
    if "target" in issue:
        entry["target"] = issue["target"]
    return entry


def _structural_validation_summary(
    validation: ValidationResult,
) -> dict[str, object]:
    warnings = [
        _structural_issue_entry("lint", issue)
        for issue in validation["lint"]["issues"]
        if issue["severity"] != "error"
    ]
    warnings.extend(
        _structural_issue_entry("integrity", issue)
        for issue in validation["integrity"]["issues"]
        if issue["severity"] != "error"
    )
    failures = [dict(failure) for failure in validation["failures"]]
    return {
        "ok": validation["ok"],
        "error_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
    }


__all__ = [
    "benchmark_exit_code",
    "benchmark_verdict",
    "generate_audit_report",
    "generate_report",
    "informational_warning_count",
    "performance_threshold_failure_count",
    "render_report_text",
    "retrieval_threshold_failure_count",
    "structural_failure_count",
]
