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
    load_beir_nfcorpus_cached_manifest,
    load_beir_scifact_cached_manifest,
    load_hidden_holdout_suite,
    load_miracl_ko_cached_manifest,
    load_mr_tydi_ko_cached_manifest,
    load_snowiki_shaped_suite,
)
from snowiki.bench.anchors.public_cached import PublicAnchorSampleMode
from snowiki.bench.corpus import BenchmarkCorpusManifest, load_corpus_from_manifest
from snowiki.bench.models import BenchmarkReport
from snowiki.cli.output import emit_error

_BENCH = import_module("snowiki.bench")
benchmark_exit_code = _BENCH.benchmark_exit_code
generate_report = _BENCH.generate_report
list_presets = _BENCH.list_presets
seed_canonical_benchmark_root = _BENCH.seed_canonical_benchmark_root
render_report_text = _BENCH.render_report_text
write_tokenizer_comparison_artifact = _BENCH.write_tokenizer_comparison_artifact


PRESET_NAMES = tuple(preset.name for preset in list_presets())
DATASET_NAMES = (
    "regression",
    "miracl_ko",
    "mr_tydi_ko",
    "beir_scifact",
    "beir_nfcorpus",
    "snowiki_shaped",
    "hidden_holdout",
)


def _has_seeded_corpus(root: Path) -> bool:
    normalized_root = root / "normalized"
    return normalized_root.exists() and any(normalized_root.rglob("*.json"))


def _load_dataset_manifest(
    dataset: str, sample_mode: PublicAnchorSampleMode
) -> BenchmarkCorpusManifest | None:
    if dataset == "miracl_ko":
        return load_miracl_ko_cached_manifest(sample_mode=sample_mode)
    if dataset == "mr_tydi_ko":
        return load_mr_tydi_ko_cached_manifest(sample_mode=sample_mode)
    if dataset == "beir_scifact":
        return load_beir_scifact_cached_manifest(sample_mode=sample_mode)
    if dataset == "beir_nfcorpus":
        return load_beir_nfcorpus_cached_manifest(sample_mode=sample_mode)
    if dataset == "snowiki_shaped":
        return load_snowiki_shaped_suite()
    if dataset == "hidden_holdout":
        return load_hidden_holdout_suite()
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
            f"dataset '{dataset}' requires an empty isolated benchmark root to avoid cross-tier mixing"
        )
    manifest = _load_dataset_manifest(dataset, sample_mode)
    if manifest is None:
        raise ValueError(f"dataset '{dataset}' did not resolve to a benchmark manifest")
    _ = load_corpus_from_manifest(manifest, root)
    return manifest


@contextmanager
def _benchmark_root_context(root: Path | None, *, output: Path) -> Iterator[Path]:
    if root is not None:
        yield root
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    local_root_parent = output.parent / ".snowiki-benchmark-root"
    local_root_parent.mkdir(parents=True, exist_ok=True)
    yield Path(tempfile.mkdtemp(prefix="run-", dir=local_root_parent))


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
    help=(
        "Snowiki storage root (defaults to an isolated local benchmark root under "
        + "the output directory)"
    ),
)
@click.option(
    "--dataset",
    type=click.Choice(DATASET_NAMES, case_sensitive=False),
    default="regression",
    show_default=True,
    help="Benchmark dataset tier to evaluate without changing the default regression path.",
)
@click.option(
    "--sample-mode",
    type=click.Choice(("quick", "standard", "full"), case_sensitive=False),
    default="standard",
    show_default=True,
    help=(
        "Public-anchor dataset sample mode (quick=200, standard=500, "
        + "full=min(all,1000)). Ignored for regression, shaped, and "
        + "hidden-holdout tiers."
    ),
)
@click.option(
    "--latency-sample",
    type=click.Choice(("exhaustive", "stratified", "fixed_sample"), case_sensitive=False),
    default=None,
    help="Override the tier-aware latency sampling policy for benchmark query timing.",
)
def command(
    preset: str,
    output: Path,
    root: Path | None,
    dataset: str,
    sample_mode: str,
    latency_sample: str | None,
) -> None:
    report: dict[str, object] | None = None
    tokenizer_artifact_path: Path | None = None
    dataset_sample_mode = cast(PublicAnchorSampleMode, sample_mode)
    sampling_mode = cast(
        Literal["exhaustive", "stratified", "fixed_sample"] | None,
        latency_sample,
    )
    try:
        if dataset == "hidden_holdout":
            click.echo(
                "Warning: hidden_holdout is a development-only synthetic facsimile for "
                "workflow verification and must not be treated as release evaluation."
            )
        with _benchmark_root_context(root, output=output) as benchmark_root:
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
            report = generated_report
            tokenizer_artifact_path = benchmark_root / ".cache" / "tokenizer_comparison.md"
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
