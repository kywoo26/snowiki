#!/usr/bin/env python3
"""Snowiki recall — daemon-preferred authoritative recall wrapper."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .read_router import build_recall_route, route_read
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROUTER_SPEC = importlib.util.spec_from_file_location(
        "wiki_skill_recall_router", SCRIPT_DIR / "read_router.py"
    )
    if ROUTER_SPEC is None or ROUTER_SPEC.loader is None:
        raise RuntimeError("failed to load read_router.py")
    ROUTER_MODULE = importlib.util.module_from_spec(ROUTER_SPEC)
    sys.modules[ROUTER_SPEC.name] = ROUTER_MODULE
    ROUTER_SPEC.loader.exec_module(ROUTER_MODULE)
    build_recall_route = ROUTER_MODULE.build_recall_route
    route_read = ROUTER_MODULE.route_read


def detect_root() -> Path:
    """Detect the active Snowiki root for skill-side reads."""
    configured = os.environ.get("VAULT_DIR") or os.environ.get("SNOWIKI_ROOT")
    return Path(configured).expanduser() if configured else Path.cwd()


def run_recall(
    target: str,
    *,
    root: Path | None = None,
    snowiki_executable: str = "snowiki",
    host: str = "127.0.0.1",
    port: int = 8765,
    timeout: float = 1.0,
) -> dict[str, Any]:
    """Run daemon-preferred authoritative recall without changing strategies."""
    return route_read(
        build_recall_route(target),
        root=root if root is not None else detect_root(),
        snowiki_executable=snowiki_executable,
        host=host,
        port=port,
        timeout=timeout,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the recall wrapper argument parser."""
    parser = argparse.ArgumentParser(prog="wiki-recall")
    _ = parser.add_argument("target", help="Recall target such as a date or topic")
    _ = parser.add_argument(
        "--root", type=Path, default=None, help="Snowiki storage root"
    )
    _ = parser.add_argument("--host", default="127.0.0.1", help="Daemon host")
    _ = parser.add_argument("--port", type=int, default=8765, help="Daemon port")
    _ = parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Daemon request timeout in seconds",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute the skill-side recall wrapper."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    payload = run_recall(
        args.target,
        root=args.root,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
    )
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
