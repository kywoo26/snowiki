from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import click

from snowiki.cli.output import emit_error
from snowiki.config import get_snowiki_root

_BENCH = import_module("snowiki.bench")
generate_report = _BENCH.generate_report
list_presets = _BENCH.list_presets
render_report_text = _BENCH.render_report_text


PRESET_NAMES = tuple(preset.name for preset in list_presets())


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
    "--semantic-slots/--no-semantic-slots",
    default=False,
    show_default=True,
    help="Enable the V2.1 semantic slots benchmark stub for the V2 baseline.",
)
@click.option(
    "--root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Snowiki storage root (defaults to ~/.snowiki)",
)
def command(preset: str, output: Path, semantic_slots: bool, root: Path | None) -> None:
    report: dict[str, object] | None = None
    try:
        report = generate_report(
            root if root else get_snowiki_root(),
            preset_name=preset,
            semantic_slots_enabled=semantic_slots,
        )
    except Exception as exc:
        emit_error(str(exc), output="human", code="benchmark_failed")
    if report is None:
        raise RuntimeError("benchmark did not produce a report")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    click.echo(render_report_text(report))
    click.echo(f"JSON report written to {output}")
