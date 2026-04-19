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
    load_beir_nfcorpus_sample,
    load_beir_scifact_sample,
    load_hidden_holdout_suite,
    load_miracl_ko_sample,
    load_mr_tydi_ko_sample,
    load_snowiki_shaped_suite,
)
from snowiki.bench.corpus import BenchmarkCorpusManifest, load_corpus_from_manifest
from snowiki.bench.models import BenchmarkReport
from snowiki.cli.output import emit_error

_BENCH = import_module("snowiki.bench")
benchmark_exit_code = _BENCH.benchmark_exit_code
generate_report = _BENCH.generate_report
list_presets = _BENCH.list_presets
seed_canonical_benchmark_root = _BENCH.seed_canonical_benchmark_root
render_report_text = _BENCH.render_report_text


PRESET_NAMES = tuple(preset.name for preset in list_presets())
DATASET_NAMES = (
    "regression",
    "miracl_ko",
    "mr_tydi_ko",
    "beir_scifact",
    "beir_nfcorpus",
    "snowiki_shaped",
    "hidden_holdout",
    "beir_small",
)


def _has_seeded_corpus(root: Path) -> bool:
    normalized_root = root / "normalized"
    return normalized_root.exists() and any(normalized_root.rglob("*.json"))


def _load_dataset_manifest(dataset: str) -> BenchmarkCorpusManifest | None:
    if dataset == "miracl_ko":
        return load_miracl_ko_sample()
    if dataset == "mr_tydi_ko":
        return load_mr_tydi_ko_sample()
    if dataset == "beir_scifact":
        return load_beir_scifact_sample()
    if dataset == "beir_nfcorpus":
        return load_beir_nfcorpus_sample()
    if dataset == "snowiki_shaped":
        return load_snowiki_shaped_suite()
    if dataset == "hidden_holdout":
        return load_hidden_holdout_suite()
    if dataset == "beir_small":
        raise ValueError(
            "dataset 'beir_small' is reserved but does not have a loader yet"
        )
    return None


def _ensure_seeded_root(root: Path, *, dataset: str) -> BenchmarkCorpusManifest | None:
    manifest = _load_dataset_manifest(dataset)
    if dataset == "regression":
        if _has_seeded_corpus(root):
            return None
        _ = seed_canonical_benchmark_root(root)
        return None

    if _has_seeded_corpus(root):
        raise ValueError(
            f"dataset '{dataset}' requires an empty isolated benchmark root to avoid cross-tier mixing"
        )
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
    help="Benchmark dataset tier to evaluate without changing the default regression path.",
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
    latency_sample: str | None,
) -> None:
    report: dict[str, object] | None = None
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
        with _benchmark_root_context(root) as benchmark_root:
            manifest = _ensure_seeded_root(benchmark_root, dataset=dataset)
            report = generate_report(
                benchmark_root,
                preset_name=preset,
                manifest=manifest,
                dataset_name=dataset,
                isolated_root=root is None,
                latency_sample=sampling_mode,
            )
    except Exception as exc:
        emit_error(str(exc), output="human", code="benchmark_failed")
    if report is None:
        raise RuntimeError("benchmark did not produce a report")

    if "retrieval" in report and isinstance(report["retrieval"], dict):
        retrieval_data = report["retrieval"]
        model_input = {
            k: v
            for k, v in retrieval_data.items()
            if k in {"preset", "corpus", "baselines", "candidate_matrix"}
        }
        try:
            canonical_retrieval = BenchmarkReport.model_validate(
                model_input
            ).to_legacy_dict()
            report["retrieval"] = {**retrieval_data, **canonical_retrieval}
        except Exception:
            pass

    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    click.echo(render_report_text(report))
    click.echo(f"JSON report written to {output}")
    exit_code = benchmark_exit_code(report)
    if exit_code:
        raise click.exceptions.Exit(exit_code)
