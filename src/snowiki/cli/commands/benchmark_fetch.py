from __future__ import annotations

from pathlib import Path
from typing import cast

import click

from snowiki.bench.datasets import load_matrix
from snowiki.benchmark_fetch import (
    DEFAULT_MATRIX_PATH,
    materialize_selected_datasets,
)
from snowiki.config import resolve_repo_asset_path


def _render_result(result: dict[str, object]) -> str:
    dataset_id = result["dataset_id"]
    action = result["action"]
    reason = result["reason"]
    if result.get("dry_run"):
        planned_paths = cast(dict[str, Path], result.get("planned_paths", {}))
        return (
            f"dataset={dataset_id} level={result['level_id']} plan={action} reason={reason} "
            f"corpus_path={planned_paths.get('corpus')} "
            f"queries_path={planned_paths.get('queries')} "
            f"judgments_path={planned_paths.get('judgments')}"
        )
    if action == "skip":
        return f"dataset={dataset_id} level={result['level_id']} action=skip reason={reason}"
    row_counts = cast(dict[str, int], result.get("row_counts", {}))
    return (
        f"dataset={dataset_id} level={result['level_id']} action=materialized reason={reason} "
        f"corpus={row_counts.get('corpus', 0)} queries={row_counts.get('queries', 0)} "
        f"judgments={row_counts.get('judgments', 0)}"
    )


@click.command("benchmark-fetch")
@click.option(
    "--matrix",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_MATRIX_PATH,
    show_default=True,
    help="Evaluation matrix contract that defines the allowed datasets.",
)
@click.option(
    "--dataset",
    "dataset_ids",
    multiple=True,
    help="Dataset ID to materialize. Repeat to select multiple datasets.",
)
@click.option(
    "--level",
    "level_ids",
    multiple=True,
    help="Level ID to materialize. Repeat to select multiple levels.",
)
@click.option(
    "--force/--no-force",
    default=False,
    show_default=True,
    help="Re-materialize even when the sidecar matches the current source locators.",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    show_default=True,
    help="Print planned actions without downloading or writing files.",
)
def command(
    matrix: Path,
    dataset_ids: tuple[str, ...],
    level_ids: tuple[str, ...],
    force: bool,
    dry_run: bool,
) -> None:
    """Fetch and materialize pinned benchmark datasets from Hugging Face."""

    resolved_matrix = resolve_repo_asset_path(matrix)
    try:
        selected_matrix = load_matrix(resolved_matrix)
    except FileNotFoundError as exc:
        raise click.BadParameter(
            f"Path '{resolved_matrix}' does not exist.",
            param_hint="--matrix",
        ) from exc
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--matrix") from exc
    selected_ids = list(dataset_ids) if dataset_ids else list(selected_matrix.datasets)
    selected_level_ids = list(level_ids) if level_ids else list(selected_matrix.levels)

    invalid_dataset_ids = [
        dataset_id
        for dataset_id in selected_ids
        if dataset_id not in selected_matrix.datasets
    ]
    if invalid_dataset_ids:
        click.echo(
            f"Unknown dataset selection: {', '.join(sorted(set(invalid_dataset_ids)))}",
            err=True,
        )
        raise click.exceptions.Exit(2)

    invalid_level_ids = [
        level_id
        for level_id in selected_level_ids
        if level_id not in selected_matrix.levels
    ]
    if invalid_level_ids:
        click.echo(
            f"Unknown level selection: {', '.join(sorted(set(invalid_level_ids)))}",
            err=True,
        )
        raise click.exceptions.Exit(2)
    selected_levels = [selected_matrix.levels[level_id] for level_id in selected_level_ids]

    try:
        results = materialize_selected_datasets(
            selected_ids,
            levels=selected_levels,
            force=force,
            dry_run=dry_run,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    for result in results:
        click.echo(_render_result(result))
