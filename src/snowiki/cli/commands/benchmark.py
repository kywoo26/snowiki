from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path

import click

from snowiki.bench.models import BenchmarkReport
from snowiki.cli.output import emit_error

_BENCH = import_module("snowiki.bench")
benchmark_exit_code = _BENCH.benchmark_exit_code
generate_report = _BENCH.generate_report
list_presets = _BENCH.list_presets
seed_canonical_benchmark_root = _BENCH.seed_canonical_benchmark_root
render_report_text = _BENCH.render_report_text


PRESET_NAMES = tuple(preset.name for preset in list_presets())


def _has_seeded_corpus(root: Path) -> bool:
    normalized_root = root / "normalized"
    return normalized_root.exists() and any(normalized_root.rglob("*.json"))


def _ensure_seeded_root(root: Path) -> None:
    if _has_seeded_corpus(root):
        return
    _ = seed_canonical_benchmark_root(root)


@contextmanager
def _benchmark_root_context(root: Path | None):
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
def command(preset: str, output: Path, root: Path | None) -> None:
    report: dict[str, object] | None = None
    try:
        with _benchmark_root_context(root) as benchmark_root:
            _ensure_seeded_root(benchmark_root)
            report = generate_report(
                benchmark_root,
                preset_name=preset,
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
            if k in {"preset", "corpus", "baselines"}
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
