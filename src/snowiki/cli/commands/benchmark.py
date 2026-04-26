from __future__ import annotations

import json
from pathlib import Path

import click

from snowiki.bench import load_matrix, render_json
from snowiki.bench.report import render_summary
from snowiki.bench.runner import run_matrix_with_exit_code

DEFAULT_MATRIX_PATH = Path("benchmarks/contracts/official_matrix.yaml")


@click.command("benchmark", short_help="Run benchmark matrix contracts.")
@click.option(
    "--matrix",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=DEFAULT_MATRIX_PATH,
    show_default=True,
    help="Evaluation matrix contract to run.",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Path to write the benchmark JSON result.",
)
@click.option(
    "--dataset",
    "dataset_ids",
    multiple=True,
    help="Dataset ID to run. Repeat to select multiple datasets.",
)
@click.option(
    "--level",
    "level_ids",
    multiple=True,
    help="Level ID to run. Repeat to select multiple levels.",
)
@click.option(
    "--target",
    "target_ids",
    multiple=True,
    help="Target ID to run. Repeat to select multiple targets.",
)
@click.option(
    "--metric",
    "metric_ids",
    multiple=True,
    help="Metric ID to compute. Repeat to select multiple metrics.",
)
@click.option(
    "--fail-fast/--no-fail-fast",
    default=False,
    show_default=True,
    help="Stop after the first failed matrix cell.",
)
def command(
    matrix: Path,
    report_path: Path,
    dataset_ids: tuple[str, ...],
    level_ids: tuple[str, ...],
    target_ids: tuple[str, ...],
    metric_ids: tuple[str, ...],
    fail_fast: bool,
) -> None:
    """Run the lean benchmark skeleton against a matrix contract."""

    selection = {
        key: value
        for key, value in {
            "dataset_ids": dataset_ids,
            "level_ids": level_ids,
            "target_ids": target_ids,
            "metric_ids": metric_ids,
        }.items()
        if value
    }
    result, exit_code = run_matrix_with_exit_code(
        load_matrix(matrix),
        selection=selection,
        fail_fast=fail_fast,
    )
    if exit_code == 2:
        for failure in result.failures:
            click.echo(failure)
        raise click.exceptions.Exit(exit_code)
    payload = render_json(result)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _ = report_path.write_text(f"{rendered}\n", encoding="utf-8")
    click.echo(render_summary(result))
    for failure in result.failures:
        click.echo(failure)
    raise click.exceptions.Exit(exit_code)
