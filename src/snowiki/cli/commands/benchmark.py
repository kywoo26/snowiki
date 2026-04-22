from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import Literal, cast

import click

from snowiki.bench.anchors import (
    load_beir_nq_cached_manifest,
    load_beir_scifact_cached_manifest,
    load_miracl_en_cached_manifest,
    load_miracl_ko_cached_manifest,
    load_ms_marco_passage_cached_manifest,
    load_trec_dl_2020_passage_cached_manifest,
)
from snowiki.bench.anchors.public_cached import PublicAnchorSampleMode
from snowiki.bench.catalog import official_suite_dataset_ids
from snowiki.bench.corpus import BenchmarkCorpusManifest, load_corpus_from_manifest
from snowiki.bench.models import BenchmarkReport
from snowiki.bench.run_context import LAYER_POLICIES, canonicalize_execution_layer
from snowiki.cli.output import emit_error

_BENCH = import_module("snowiki.bench")
benchmark_exit_code = _BENCH.benchmark_exit_code
generate_report = _BENCH.generate_report
list_presets = _BENCH.list_presets
seed_canonical_benchmark_root = _BENCH.seed_canonical_benchmark_root
render_report_text = _BENCH.render_report_text
write_tokenizer_comparison_artifact = _BENCH.write_tokenizer_comparison_artifact


PRESET_NAMES = tuple(preset.name for preset in list_presets())
OFFICIAL_DATASET_NAMES = official_suite_dataset_ids()
DATASET_NAMES = ("regression", *OFFICIAL_DATASET_NAMES)
LAYER_NAMES = (*tuple(LAYER_POLICIES), "scheduled_official_broad")


def _has_seeded_corpus(root: Path) -> bool:
    normalized_root = root / "normalized"
    return normalized_root.exists() and any(normalized_root.rglob("*.json"))


def _load_dataset_manifest(
    dataset: str, sample_mode: PublicAnchorSampleMode
) -> BenchmarkCorpusManifest | None:
    if dataset == "ms_marco_passage":
        return load_ms_marco_passage_cached_manifest(sample_mode=sample_mode)
    if dataset == "trec_dl_2020_passage":
        return load_trec_dl_2020_passage_cached_manifest(sample_mode=sample_mode)
    if dataset == "miracl_ko":
        return load_miracl_ko_cached_manifest(sample_mode=sample_mode)
    if dataset == "miracl_en":
        return load_miracl_en_cached_manifest(sample_mode=sample_mode)
    if dataset == "beir_nq":
        return load_beir_nq_cached_manifest(sample_mode=sample_mode)
    if dataset == "beir_scifact":
        return load_beir_scifact_cached_manifest(sample_mode=sample_mode)
    return None


def _ensure_seeded_root(
    root: Path, *, dataset: str, sample_mode: PublicAnchorSampleMode
) -> BenchmarkCorpusManifest | None:
    if dataset == "regression":
        if _has_seeded_corpus(root):
            return None
        _ = seed_canonical_benchmark_root(root)
        return None

    if _has_seeded_corpus(root):
        raise ValueError(
            f"dataset '{dataset}' requires an empty isolated benchmark root to avoid cross-dataset mixing"
        )
    manifest = _load_dataset_manifest(dataset, sample_mode)
    if manifest is None:
        raise ValueError(f"dataset '{dataset}' did not resolve to a benchmark manifest")
    _ = load_corpus_from_manifest(manifest, root)
    return manifest


@contextmanager
def _benchmark_root_context(root: Path | None) -> Iterator[Path]:
    if root is not None:
        yield root
        return
    with tempfile.TemporaryDirectory(
        prefix="snowiki-benchmark-root-"
    ) as temporary_root:
        yield Path(temporary_root)


@click.command("benchmark")
@click.option(
    "--preset", type=click.Choice(PRESET_NAMES, case_sensitive=False), required=True
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Path to write the machine-readable benchmark JSON report.",
)
@click.option(
    "--root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Snowiki storage root (defaults to an isolated temporary benchmark root)",
)
@click.option(
    "--dataset",
    type=click.Choice(DATASET_NAMES, case_sensitive=False),
    default="regression",
    show_default=True,
    help="Benchmark dataset to evaluate. Supported values are regression plus the official six-dataset suite.",
)
@click.option(
    "--sample-mode",
    type=click.Choice(("quick", "standard", "full"), case_sensitive=False),
    default="standard",
    show_default=True,
    help=(
        "Official benchmark sample mode (quick=150, standard=500, "
        + "full=min(all,1000)). Ignored for regression."
    ),
)
@click.option(
    "--latency-sample",
    type=click.Choice(("exhaustive", "stratified", "fixed_sample"), case_sensitive=False),
    default=None,
    help="Override the tier-aware latency sampling policy for benchmark query timing.",
)
@click.option(
    "--layer",
    type=click.Choice(LAYER_NAMES, case_sensitive=False),
    default=None,
    help="Execution layer for official benchmark runs.",
)
def command(
    preset: str,
    output: Path,
    root: Path | None,
    dataset: str,
    sample_mode: str,
    latency_sample: str | None,
    layer: str | None,
) -> None:
    report: dict[str, object] | None = None
    tokenizer_artifact_path: Path | None = None
    dataset_sample_mode = cast(PublicAnchorSampleMode, sample_mode)
    sampling_mode = cast(
        Literal["exhaustive", "stratified", "fixed_sample"] | None,
        latency_sample,
    )
    normalized_layer = (
        canonicalize_execution_layer(layer) if isinstance(layer, str) else None
    )
    try:
        with _benchmark_root_context(root) as benchmark_root:
            manifest = _ensure_seeded_root(
                benchmark_root,
                dataset=dataset,
                sample_mode=dataset_sample_mode,
            )
            generated_report = generate_report(
                benchmark_root,
                preset_name=preset,
                manifest=manifest,
                dataset_name=dataset,
                isolated_root=root is None,
                latency_sample=sampling_mode,
                execution_layer=normalized_layer,
            )
            if "retrieval" in generated_report and isinstance(
                generated_report["retrieval"], dict
            ):
                retrieval_data = generated_report["retrieval"]
                model_input = {
                    k: v
                    for k, v in retrieval_data.items()
                    if k in {"preset", "corpus", "baselines", "candidate_matrix"}
                }
                try:
                    canonical_retrieval = BenchmarkReport.model_validate(
                        model_input
                    ).to_legacy_dict()
                    generated_report["retrieval"] = {
                        **retrieval_data,
                        **canonical_retrieval,
                    }
                except Exception:
                    pass
            current_report = generated_report
            report = current_report
            tokenizer_artifact_path = output.parent / ".cache" / "tokenizer_comparison.md"
            _ = write_tokenizer_comparison_artifact(report, tokenizer_artifact_path)
    except Exception as exc:
        emit_error(str(exc), output="human", code="benchmark_failed")
    if report is None:
        raise RuntimeError("benchmark did not produce a report")
    final_report = report
    final_tokenizer_artifact_path = tokenizer_artifact_path

    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(
        json.dumps(final_report, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    click.echo(render_report_text(final_report))
    click.echo(f"JSON report written to {output}")
    click.echo(f"Tokenizer comparison written to {final_tokenizer_artifact_path}")
    exit_code = benchmark_exit_code(final_report)
    if exit_code:
        raise click.exceptions.Exit(exit_code)
