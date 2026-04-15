#!/usr/bin/env python3
"""Execute the Step 1 lexical promotion gate."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import click

from snowiki.config import get_repo_root


@dataclass(frozen=True, slots=True)
class Step1ProofTarget:
    """A single Step 1 proof target."""

    path: Path
    label: str


STEP1_PROOF_TARGETS: tuple[Step1ProofTarget, ...] = (
    Step1ProofTarget(
        path=Path("tests/search/test_runtime_lexical_separation.py"),
        label="benchmark/runtime separation",
    ),
    Step1ProofTarget(
        path=Path("tests/governance/test_retrieval_surface_parity.py"),
        label="direct-search and recall parity",
    ),
    Step1ProofTarget(
        path=Path("tests/daemon/test_warm_index.py"),
        label="freshness invariants",
    ),
    Step1ProofTarget(
        path=Path("tests/cli/test_rebuild.py"),
        label="rebuild invariants",
    ),
    Step1ProofTarget(
        path=Path("tests/rebuild/test_integrity.py"),
        label="freshness/rebuild integrity",
    ),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Run the narrow Step 1 lexical promotion gate.",
    )
    _ = parser.add_argument(
        "--root",
        type=Path,
        default=get_repo_root(),
        help="repository root to inspect (defaults to the repository root)",
    )
    _ = parser.add_argument(
        "--strict",
        action="store_true",
        help="fail closed when any Step 1 proof target is missing or fails",
    )
    return parser.parse_args(argv)


def _missing_targets(root: Path) -> tuple[Step1ProofTarget, ...]:
    """Return the Step 1 proof targets that are missing from the repo."""

    missing: list[Step1ProofTarget] = []
    for target in STEP1_PROOF_TARGETS:
        if not (root / target.path).exists():
            missing.append(target)
    return tuple(missing)


def _run_step1_proofs(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the Step 1 proof suite under pytest."""

    command = [
        "uv",
        "run",
        "pytest",
        *[target.path.as_posix() for target in STEP1_PROOF_TARGETS],
    ]
    return subprocess.run(command, cwd=root, check=False, text=True)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Step 1 lexical promotion gate."""

    args = parse_args(argv)
    root = cast(Path, args.root).resolve()
    strict = cast(bool, args.strict)

    click.echo("Step 1 lexical promotion gate")
    click.echo(f"mode: {'strict' if strict else 'non-strict'}")

    missing = _missing_targets(root)
    if missing:
        click.echo("missing Step 1 proof target(s):")
        for target in missing:
            click.echo(f"- {target.path.as_posix()} ({target.label})")
        return 2

    click.echo("running Step 1 proof targets:")
    for target in STEP1_PROOF_TARGETS:
        click.echo(f"- {target.path.as_posix()} ({target.label})")

    result = _run_step1_proofs(root)
    if result.returncode != 0:
        click.echo(f"Step 1 promotion gate failed (exit_code={result.returncode})")
        return result.returncode

    click.echo("Step 1 promotion gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
