from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .baselines import run_baseline_comparison
from .presets import get_preset
from .semantic_slots import SemanticSlotsConfig


def generate_report(
    root: Path,
    *,
    preset_name: str,
    semantic_slots_enabled: bool = False,
) -> dict[str, Any]:
    preset = get_preset(preset_name)
    comparison = run_baseline_comparison(
        root,
        preset,
        semantic_slots=SemanticSlotsConfig(enabled=semantic_slots_enabled),
    )
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "report_version": "1.0",
        **comparison,
    }


def render_report_text(report: dict[str, Any]) -> str:
    preset = report["preset"]
    corpus = report["corpus"]
    lines = [
        f"Benchmark preset: {preset['name']}",
        f"Description: {preset['description']}",
        f"Queries evaluated: {corpus['queries_evaluated']}",
        f"Corpus: {corpus['records_indexed']} records, {corpus['pages_indexed']} pages",
        f"Semantic slots: {'enabled' if report['semantic_slots']['enabled'] else 'disabled'} ({report['semantic_slots']['version']} {report['semantic_slots']['mode']})",
        "Baselines:",
    ]
    for name, payload in report["baselines"].items():
        quality = payload["quality"]
        latency = payload["latency"]
        tokens = report["token_reduction"][name]
        lines.append(
            "- "
            f"{name}: Recall@{quality['top_k']}={quality['recall_at_k']}, "
            f"MRR={quality['mrr']}, "
            f"nDCG@{quality['top_k']}={quality['ndcg_at_k']}, "
            f"P50={latency['p50_ms']}ms, P95={latency['p95_ms']}ms, "
            f"avg_tokens={tokens['avg_tokens']}, reduction_vs_raw={tokens['reduction_ratio']}"
        )
    return "\n".join(lines)
