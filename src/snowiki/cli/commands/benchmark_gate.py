from __future__ import annotations

import json
from pathlib import Path

import click
import yaml

from snowiki.benchmark_gates import (
    evaluate_analyzer_promotion_gate,
    load_analyzer_promotion_gate,
    load_benchmark_report,
    render_gate_json,
    render_gate_summary,
)

DEFAULT_GATE_PATH = Path("benchmarks/contracts/analyzer_promotion_gates.yaml")


@click.command("benchmark-gate", short_help="Evaluate benchmark reports against gates.")
@click.option(
    "--gate",
    "gate_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=DEFAULT_GATE_PATH,
    show_default=True,
    help="Analyzer promotion gate contract to evaluate.",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Benchmark JSON report to evaluate.",
)
@click.option(
    "--gate-report",
    "gate_report_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional path to write the gate evaluation JSON result.",
)
def command(gate_path: Path, report_path: Path, gate_report_path: Path | None) -> None:
    """Evaluate a benchmark report against an analyzer promotion gate."""

    try:
        result = evaluate_analyzer_promotion_gate(
            gate=load_analyzer_promotion_gate(gate_path),
            report=load_benchmark_report(report_path),
        )
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload = render_gate_json(result)
    if gate_report_path is not None:
        rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        gate_report_path.parent.mkdir(parents=True, exist_ok=True)
        _ = gate_report_path.write_text(f"{rendered}\n", encoding="utf-8")
    click.echo(render_gate_summary(result))
    for failure in result.failures:
        click.echo(failure)
    raise click.exceptions.Exit(0 if result.status == "pass" else 1)
