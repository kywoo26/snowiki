#!/usr/bin/env python3
"""Report advisory governance drift for repo-owned instruction surfaces."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import click

INHERITANCE_MARKER = (
    "Root `AGENTS.md` is inherited; this file defines local deltas only."
)
ROOT_AGENT_FILE = Path("AGENTS.md")
CHILD_AGENT_FILES = (
    Path("benchmarks/AGENTS.md"),
    Path("vault-template/AGENTS.md"),
    Path("skill/AGENTS.md"),
)
REQUIRED_AGENT_FILES = (
    ROOT_AGENT_FILE,
    *CHILD_AGENT_FILES,
)
REQUIRED_CANONICAL_SURFACES = (
    ROOT_AGENT_FILE,
    Path("benchmarks/README.md"),
    Path("skill/SKILL.md"),
    Path("vault-template/CLAUDE.md"),
)


@dataclass(frozen=True, slots=True)
class Finding:
    """A single advisory governance finding."""

    code: str
    path: str
    message: str


def _read_text(path: Path) -> str:
    """Return file contents using UTF-8."""

    return path.read_text(encoding="utf-8")


def _extract_root_command_lines(root_agents_text: str) -> tuple[str, ...]:
    """Return executable command lines from the root AGENTS command block."""

    fence = "```"
    marker = "```bash"
    if marker not in root_agents_text:
        return ()

    command_block = root_agents_text.split(marker, maxsplit=1)[1].split(
        fence,
        maxsplit=1,
    )[0]
    lines: list[str] = []
    for raw_line in command_block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return tuple(lines)


def _relative_path(root: Path, path: Path) -> str:
    """Return a stable relative path string."""

    return path.relative_to(root).as_posix()


def _check_required_files(root: Path) -> list[Finding]:
    """Check that required governed surfaces exist."""

    findings: list[Finding] = []

    for relative_path in REQUIRED_AGENT_FILES:
        path = root / relative_path
        if not path.exists():
            findings.append(
                Finding(
                    code="missing-agents",
                    path=relative_path.as_posix(),
                    message="required AGENTS contract is missing",
                )
            )

    for relative_path in REQUIRED_CANONICAL_SURFACES:
        path = root / relative_path
        if not path.exists():
            findings.append(
                Finding(
                    code="missing-canonical-surface",
                    path=relative_path.as_posix(),
                    message="required canonical source-of-truth surface is missing",
                )
            )

    return findings


def _check_child_agents(root: Path, root_commands: Sequence[str]) -> list[Finding]:
    """Check child AGENTS inheritance markers and root-command duplication."""

    findings: list[Finding] = []

    for relative_path in CHILD_AGENT_FILES:
        path = root / relative_path
        if not path.exists():
            continue

        content = _read_text(path)
        if INHERITANCE_MARKER not in content:
            findings.append(
                Finding(
                    code="missing-inheritance-marker",
                    path=_relative_path(root, path),
                    message="child AGENTS must declare inheritance from root AGENTS.md",
                )
            )

        for command in root_commands:
            if command in content:
                findings.append(
                    Finding(
                        code="duplicated-root-command",
                        path=_relative_path(root, path),
                        message=(
                            f"child AGENTS duplicates a root command line: {command}"
                        ),
                    )
                )

    return findings


def collect_findings(root: Path) -> list[Finding]:
    """Collect advisory governance drift findings for the repository."""

    findings = _check_required_files(root)
    root_agents_path = root / ROOT_AGENT_FILE
    if not root_agents_path.exists():
        return findings

    root_commands = _extract_root_command_lines(_read_text(root_agents_path))
    if not root_commands:
        findings.append(
            Finding(
                code="missing-root-command-block",
                path=ROOT_AGENT_FILE.as_posix(),
                message="root AGENTS.md should expose a fenced bash command block",
            )
        )

    findings.extend(_check_child_agents(root, root_commands))
    return findings


def render_report(findings: Sequence[Finding]) -> str:
    """Render a human-readable advisory report."""

    lines = ["Governance advisory report"]
    if not findings:
        lines.append("status: clean")
        lines.append("No governance drift findings.")
        return "\n".join(lines)

    lines.append(f"status: advisory ({len(findings)} finding(s))")
    for finding in findings:
        lines.append(f"- [{finding.code}] {finding.path}: {finding.message}")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Report governance drift across canonical repo surfaces.",
    )
    _ = parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root to inspect (defaults to current working directory)",
    )
    mode = parser.add_mutually_exclusive_group()
    _ = mode.add_argument(
        "--report",
        action="store_true",
        help="emit an advisory report and always exit zero",
    )
    _ = mode.add_argument(
        "--strict",
        action="store_true",
        help="emit the report and exit non-zero when findings exist",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the governance checker CLI."""

    args = parse_args(argv)
    root = cast(Path, args.root).resolve()
    strict = cast(bool, args.strict)
    findings = collect_findings(root)
    click.echo(render_report(findings))

    if strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
