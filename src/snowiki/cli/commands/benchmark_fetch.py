from __future__ import annotations

from pathlib import Path
from typing import cast

import click

from snowiki.bench.datasets import (
    RefreshMode,
    fetch_benchmark_dataset,
    normalize_dataset_id,
)
from snowiki.bench.runtime.catalog import official_suite_dataset_ids
from snowiki.cli.output import emit_error

OFFICIAL_FETCH_DATASET_IDS = official_suite_dataset_ids()


@click.command("benchmark-fetch")
@click.option(
    "--dataset",
    type=click.Choice(OFFICIAL_FETCH_DATASET_IDS, case_sensitive=False),
    required=True,
    help="Official benchmark dataset to fetch into the benchmark-owned cache.",
)
@click.option(
    "--data-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Override the benchmark data root used for the HF cache and local locks.",
)
@click.option(
    "--refresh",
    type=click.Choice(("if-missing", "force"), case_sensitive=False),
    default="if-missing",
    show_default=True,
    help="Reuse an existing local lock when possible or force a fresh snapshot fetch.",
)
@click.option(
    "--offline/--no-offline",
    default=False,
    show_default=True,
    help="Require the dataset snapshot to already exist in the local benchmark cache.",
)
def command(dataset: str, data_root: Path | None, refresh: str, offline: bool) -> None:
    normalized_dataset = normalize_dataset_id(dataset)
    try:
        result = fetch_benchmark_dataset(
            normalized_dataset,
            data_root=data_root,
            refresh=cast(RefreshMode, refresh),
            local_files_only=offline,
        )
    except Exception as exc:
        emit_error(str(exc), output="human", code="benchmark_fetch_failed")

    click.echo(f"dataset id: {result.dataset_id}")
    click.echo(f"benchmark data root: {result.benchmark_data_root}")
    click.echo(f"lock path: {result.lock_path}")
    click.echo(f"source count: {len(result.sources)}")
    for source in result.sources:
        click.echo(
            f"- {source.label}: {source.repo_id} @ {source.requested_revision}"
        )
        click.echo(f"  snapshot path: {source.snapshot_path}")
        click.echo(f"  allow patterns: {', '.join(source.allow_patterns)}")
