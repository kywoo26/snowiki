"""Human-readable benchmark report rendering helpers."""

from __future__ import annotations

from importlib import import_module
from typing import cast

_VERDICT = import_module("snowiki.bench.verdict")
_retrieval_threshold_entries = _VERDICT._retrieval_threshold_entries
informational_warning_count = _VERDICT.informational_warning_count
performance_threshold_failure_count = _VERDICT.performance_threshold_failure_count
retrieval_threshold_failure_count = _VERDICT.retrieval_threshold_failure_count
structural_failure_count = _VERDICT.structural_failure_count


def _render_thresholds(thresholds: object) -> str:
    if not isinstance(thresholds, list):
        return ""
    rendered: list[str] = []
    for entry in thresholds:
        if not isinstance(entry, dict):
            continue
        threshold = cast(dict[str, object], entry)
        metric = str(threshold.get("metric", "unknown"))
        operator = str(threshold.get("operator", ">="))
        value = threshold.get("value", "n/a")
        rendered.append(f"{metric} {operator} {value}")
    return ", ".join(rendered)


def _format_threshold_entry(baseline: str, entry: dict[str, object]) -> str:
    gate = str(entry.get("gate", "unknown"))
    metric = str(entry.get("metric", "unknown"))
    value = entry.get("value", "n/a")
    delta = entry.get("delta")
    threshold = entry.get("threshold", "n/a")
    verdict = str(entry.get("verdict", "UNKNOWN"))
    tokenizer_name = entry.get("tokenizer_name")
    baseline_label = f"{baseline} ({tokenizer_name})" if tokenizer_name else baseline
    parts = [
        f"- {baseline_label} {gate} {metric}: {verdict}",
        f"value={value}",
        f"delta={delta if delta is not None else 'n/a'}",
        f"threshold={threshold}",
    ]
    return ", ".join(parts)


def _format_table_value(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _baseline_tokenizer_name(baseline: dict[str, object]) -> str | None:
    tokenizer_name = baseline.get("tokenizer_name")
    if isinstance(tokenizer_name, str) and tokenizer_name.strip():
        return tokenizer_name.strip()

    quality = baseline.get("quality")
    if isinstance(quality, dict):
        quality_dict = cast(dict[str, object], quality)
        quality_tokenizer_name = quality_dict.get("tokenizer_name")
        if isinstance(quality_tokenizer_name, str) and quality_tokenizer_name.strip():
            return quality_tokenizer_name.strip()

        thresholds = quality_dict.get("thresholds")
        if isinstance(thresholds, list):
            for entry in thresholds:
                if not isinstance(entry, dict):
                    continue
                threshold_entry = cast(dict[str, object], entry)
                threshold_tokenizer_name = threshold_entry.get("tokenizer_name")
                if (
                    isinstance(threshold_tokenizer_name, str)
                    and threshold_tokenizer_name.strip()
                ):
                    return threshold_tokenizer_name.strip()

    return None


def _render_tokenizer_comparison(baselines: dict[str, object]) -> list[str]:
    rows: list[list[str]] = []
    for baseline_name, baseline_payload in baselines.items():
        if not isinstance(baseline_payload, dict):
            continue
        baseline = cast(dict[str, object], baseline_payload)
        tokenizer_name = _baseline_tokenizer_name(baseline)
        if tokenizer_name is None:
            continue

        quality = baseline.get("quality")
        overall: dict[str, object] = {}
        if isinstance(quality, dict):
            quality_dict = cast(dict[str, object], quality)
            overall_payload = quality_dict.get("overall")
            if isinstance(overall_payload, dict):
                overall = cast(dict[str, object], overall_payload)

        rows.append(
            [
                str(baseline_name),
                tokenizer_name,
                _format_table_value(overall.get("recall_at_k")),
                _format_table_value(overall.get("mrr")),
                _format_table_value(overall.get("ndcg_at_k")),
            ]
        )

    if not rows:
        return []

    headers = ["Baseline", "Tokenizer", "Recall@k", "MRR", "nDCG@k"]
    widths = [
        max(len(row[index]) for row in [headers, *rows])
        for index in range(len(headers))
    ]

    def _render_row(values: list[str]) -> str:
        return "| " + " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(values)
        ) + " |"

    lines = ["Tokenizer comparison:", _render_row(headers)]
    lines.append(
        "| "
        + " | ".join("-" * width for width in widths)
        + " |"
    )
    for row in rows:
        lines.append(_render_row(row))
    return lines


def _format_structural_issue(entry: dict[str, object]) -> str:
    return (
        f"- {entry.get('stage', 'structural')} {entry.get('code', 'unknown')}: "
        f"{entry.get('path', 'unknown')} - {entry.get('message', 'n/a')}"
    )


def _format_performance_threshold_entry(entry: dict[str, object]) -> str:
    gate = str(entry.get("gate", "unknown"))
    metric = str(entry.get("metric", "unknown"))
    value = entry.get("value", "n/a")
    delta = entry.get("delta")
    threshold = entry.get("threshold", "n/a")
    verdict = str(entry.get("verdict", "UNKNOWN"))
    return (
        f"- {gate} {metric}: {verdict}, value={value}, "
        f"delta={delta if delta is not None else 'n/a'}, threshold={threshold}"
    )


def _format_latency_sampling_policy(policy: dict[str, object]) -> str:
    mode = str(policy.get("mode", "exhaustive"))
    sampled_query_count = policy.get("sampled_query_count")
    population_query_count = policy.get("population_query_count")
    parts = [f"mode={mode}"]
    if sampled_query_count is not None and population_query_count is not None:
        parts.append(f"queries={sampled_query_count}/{population_query_count}")
    elif sampled_query_count is not None:
        parts.append(f"queries={sampled_query_count}")
    sample_size = policy.get("sample_size")
    if sample_size is not None:
        parts.append(f"sample_size={sample_size}")
    strata = policy.get("strata")
    if isinstance(strata, list) and strata:
        parts.append(f"strata={strata}")
    return ", ".join(parts)


def _render_candidate_matrix(matrix: dict[str, object]) -> list[str]:
    candidates = cast(list[dict[str, object]], matrix.get("candidates", []))
    if not candidates:
        return []
    lines = ["Candidate Matrix:"]
    for candidate in candidates:
        name = candidate.get("candidate_name", "unknown")
        role = candidate.get("role", "unknown")
        status = candidate.get("admission_status", "unknown")
        baseline = candidate.get("evidence_baseline")
        operational = cast(dict[str, object], candidate.get("operational_evidence", {}))
        baseline_str = f", baseline={baseline}" if baseline else ""
        memory_str = ""
        disk_str = ""
        if operational.get("memory_evidence_status") == "measured":
            memory_str = f", memory_peak_rss_mb={operational.get('memory_peak_rss_mb')}"
        if operational.get("disk_size_evidence_status") == "measured":
            disk_str = f", disk_size_mb={operational.get('disk_size_mb')}"
        lines.append(
            f"- {name}: role={role}, status={status}{baseline_str}{memory_str}{disk_str}"
        )
    return lines


def _render_candidate_decisions(matrix: dict[str, object]) -> list[str]:
    decisions = cast(list[dict[str, object]], matrix.get("decisions", []))
    if not decisions:
        return []
    lines = ["Candidate Decisions:"]
    for decision in decisions:
        name = decision.get("candidate_name", "unknown")
        disposition = str(decision.get("disposition", "unknown")).upper()
        reasons = decision.get("reasons", [])
        reasons_str = f" ({', '.join(cast(list[str], reasons))})" if reasons else ""
        lines.append(f"- {name}: {disposition}{reasons_str}")
    return lines


def render_report_text(report: dict[str, object]) -> str:
    """Render a benchmark report as human-readable text.

    Args:
        report: Benchmark report dictionary.

    Returns:
        A newline-delimited text summary of the report.
    """
    dataset = cast(dict[str, object], report.get("dataset", {}))
    metadata = cast(dict[str, object], report.get("metadata", {}))
    preset = cast(dict[str, object], report["preset"])
    corpus = cast(dict[str, object], report["corpus"])
    protocol = cast(dict[str, object], report["protocol"])
    structural = cast(dict[str, object], report.get("structural", {}))
    retrieval = cast(dict[str, object], report["retrieval"])
    candidate_matrix = cast(dict[str, object], retrieval.get("candidate_matrix", {}))
    performance = cast(dict[str, dict[str, float]], report["performance"])
    performance_threshold_policy = cast(
        list[dict[str, object]], report.get("performance_threshold_policy", [])
    )
    performance_thresholds = cast(
        list[dict[str, object]], report.get("performance_thresholds", [])
    )
    unified_verdict = cast(dict[str, object], report.get("benchmark_verdict", {}))
    structural_failures = structural_failure_count(report)
    structural_warnings = informational_warning_count(report)
    dataset_label = str(dataset.get("name", dataset.get("id", "unknown")))
    dataset_id = dataset.get("id")
    dataset_tier = dataset.get("tier")
    lines = [
        f"Benchmark preset: {preset['name']}",
        (
            f"Benchmark dataset: {dataset_label}"
            + (f" (id={dataset_id})" if dataset_id else "")
            + (f", tier={dataset_tier}" if dataset_tier else "")
        ),
        f"Description: {preset['description']}",
        f"Queries evaluated: {corpus['queries_evaluated']}",
        (
            "Protocol: "
            f"isolated_root={protocol['isolated_root']}, "
            f"warmups={protocol['warmups']}, "
            f"repetitions={protocol['repetitions']}, "
            f"query_mode={protocol['query_mode']}, "
            f"top_k={protocol['top_k']}, top_ks={protocol.get('top_ks', preset.get('top_ks', [protocol['top_k']]))}"
            + (
                f", dataset_mode={protocol.get('dataset_mode')}"
                if protocol.get("dataset_mode")
                else ""
            )
        ),
        (
            "Structural verdict: "
            f"{'FAIL' if structural_failures else 'PASS'} "
            f"({structural_failures} failures, {structural_warnings} warnings)"
        ),
    ]
    sampling_policy = cast(
        dict[str, object], metadata.get("latency_sampling_policy", {})
    )
    if not sampling_policy:
        sampling_policy = cast(dict[str, object], protocol.get("sampling_policy", {}))
    lines.append(
        f"Latency sampling: {_format_latency_sampling_policy(sampling_policy)}"
    )
    report_limits = cast(dict[str, object], metadata.get("report_limits", {}))
    if report_limits.get("applied"):
        lines.append(
            "Report detail limit: "
            f"per-query details capped at {report_limits.get('per_query_detail_limit')} entries "
            f"for baselines {report_limits.get('baselines_truncated', [])}"
        )
    dataset_metadata = cast(dict[str, object], dataset.get("metadata", {}))
    if dataset.get("description"):
        lines.append(f"Dataset description: {dataset['description']}")
    if dataset_metadata.get("source_url"):
        lines.append(f"Dataset source: {dataset_metadata['source_url']}")
    if dataset_metadata.get("license"):
        lines.append(f"Dataset license: {dataset_metadata['license']}")
    sample_mode = dataset_metadata.get("sample_mode")
    if sample_mode:
        lines.append(
            "Dataset sample mode: "
            f"{sample_mode} ({dataset_metadata.get('sample_size', 'n/a')}/"
            f"{dataset_metadata.get('queries_available', 'n/a')} queries)"
        )
    if dataset_metadata.get("language"):
        lines.append(f"Dataset language: {dataset_metadata['language']}")
    dataset_provenance = cast(dict[str, object], dataset.get("provenance", {}))
    provenance_status = cast(dict[str, object], dataset.get("provenance_status", {}))
    if dataset_provenance:
        provenance_parts = [
            f"source_class={dataset_provenance.get('source_class', 'unknown')}",
            f"authoring_method={dataset_provenance.get('authoring_method', 'unknown')}",
            f"family_dedupe_key={dataset_provenance.get('family_dedupe_key', 'n/a')}",
        ]
        lines.append(f"Dataset provenance: {', '.join(provenance_parts)}")
    elif provenance_status:
        lines.append(
            "Dataset provenance: sealed "
            f"(visibility_tier={provenance_status.get('visibility_tier', 'unknown')}, "
            f"authority_tier={provenance_status.get('authority_tier', 'unknown')}, "
            f"dev_report_excludes_assets={provenance_status.get('dev_report_excludes_assets', False)})"
        )
    if "fixtures_indexed" in corpus:
        lines.append(f"Canonical fixtures: {corpus['fixtures_indexed']}")
    if "documents_seeded" in corpus:
        lines.append(f"Manifest documents seeded: {corpus['documents_seeded']}")
    if "records_indexed" in corpus:
        lines.append(f"Records indexed: {corpus['records_indexed']}")
    if "pages_indexed" in corpus:
        lines.append(f"Pages indexed: {corpus['pages_indexed']}")
    failures = structural.get("failures", [])
    if isinstance(failures, list) and failures:
        lines.append("Structural failures:")
        for entry in failures:
            if isinstance(entry, dict):
                lines.append(_format_structural_issue(cast(dict[str, object], entry)))
    warnings = structural.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Informational warnings:")
        for entry in warnings:
            if isinstance(entry, dict):
                lines.append(_format_structural_issue(cast(dict[str, object], entry)))

    if candidate_matrix:
        lines.extend(_render_candidate_matrix(candidate_matrix))
        lines.extend(_render_candidate_decisions(candidate_matrix))

    if performance:
        lines.append("Performance:")
        for name, latency in performance.items():
            lines.append(f"- {name}: P50={latency['p50_ms']}ms, P95={latency['p95_ms']}ms")
    else:
        lines.append("Performance: unavailable")
    if performance_threshold_policy:
        lines.append("Performance threshold policy:")
        lines.append(f"- overall: {_render_thresholds(performance_threshold_policy)}")
    performance_failures = [
        entry for entry in performance_thresholds if entry.get("verdict") == "FAIL"
    ]
    if performance_failures:
        lines.append("Performance threshold failures:")
        for entry in performance_failures:
            lines.append(_format_performance_threshold_entry(entry))
    if performance_thresholds:
        lines.append("Performance thresholds:")
        for entry in performance_thresholds:
            if performance_failures and entry.get("verdict") == "FAIL":
                continue
            lines.append(_format_performance_threshold_entry(entry))
        failure_count = performance_threshold_failure_count(report)
        lines.append(
            f"Performance threshold verdict: {'FAIL' if failure_count else 'PASS'} ({failure_count} failures)"
        )
    threshold_policy = cast(dict[str, object], retrieval.get("threshold_policy", {}))
    overall_policy = threshold_policy.get("overall", [])
    slice_policy = threshold_policy.get("slices", {})
    if overall_policy or slice_policy:
        lines.append("Retrieval threshold policy:")
        if isinstance(overall_policy, list) and overall_policy:
            rendered_overall = _render_thresholds(overall_policy)
            lines.append(f"- overall: {rendered_overall}")
        if isinstance(slice_policy, dict):
            for kind, thresholds in slice_policy.items():
                rendered_slice = _render_thresholds(thresholds)
                if not rendered_slice:
                    continue
                lines.append(f"- slice:{kind}: {rendered_slice}")
    threshold_entries = _retrieval_threshold_entries(report)
    if threshold_entries:
        retrieval_failures = [
            (baseline_name, entry)
            for baseline_name, entry in threshold_entries
            if entry.get("verdict") == "FAIL"
        ]
        if retrieval_failures:
            lines.append("Retrieval threshold failures:")
            for baseline_name, entry in retrieval_failures:
                lines.append(_format_threshold_entry(baseline_name, entry))
        lines.append("Retrieval thresholds:")
        for baseline_name, entry in threshold_entries:
            if retrieval_failures and entry.get("verdict") == "FAIL":
                continue
            lines.append(_format_threshold_entry(baseline_name, entry))
        failure_count = retrieval_threshold_failure_count(report)
        lines.append(
            f"Retrieval threshold verdict: {'FAIL' if failure_count else 'PASS'} ({failure_count} failures)"
        )
    tokenizer_comparison = _render_tokenizer_comparison(
        cast(dict[str, object], retrieval.get("baselines", {}))
    )
    if tokenizer_comparison:
        lines.extend(tokenizer_comparison)
    audit = cast(dict[str, object], report.get("audit", {}))
    if audit:
        samples = cast(dict[str, object], audit.get("samples", {}))
        pooled_review = cast(dict[str, object], audit.get("pooled_review", {}))
        provenance_quota = cast(dict[str, object], audit.get("provenance_quota", {}))
        lines.append("Audit sampling:")
        lines.append(
            "- samples="
            f"{samples.get('count', 0)}, reviewer_assignments={samples.get('reviewer_assignments', 0)}, "
            f"mean_agreement_score={samples.get('mean_agreement_score', 'n/a')}"
        )
        lines.append(
            "- pooled_review="
            f"queries={pooled_review.get('query_count', 0)}, "
            f"disagreements={pooled_review.get('disagreement_count', 0)}, "
            f"blind_human_adjudication={pooled_review.get('blind_human_adjudication', False)}"
        )
        lines.append(
            "- provenance_quota="
            f"assets={provenance_quota.get('asset_count', 0)}, "
            f"hidden_holdout_assets={provenance_quota.get('hidden_holdout_asset_count', 0)}"
        )
    lines.append(
        "Unified benchmark verdict: "
        f"{unified_verdict.get('verdict', 'UNKNOWN')} "
        f"(blocking_stage={unified_verdict.get('blocking_stage')}, "
        f"exit_code={unified_verdict.get('exit_code', 'n/a')})"
    )
    return "\n".join(lines)
