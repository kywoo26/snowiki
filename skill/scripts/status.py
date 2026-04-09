#!/usr/bin/env python3
"""Snowiki status — wiki overview at a glance.

Usage:
    python3 status.py [--vault VAULT_DIR] [--json]
"""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path


def detect_vault():
    v = os.environ.get("VAULT_DIR")
    if v:
        return Path(v).expanduser()
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / ".obsidian").is_dir():
            return p
    return cwd


def parse_frontmatter_type(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "unknown"
    if not text.startswith("---"):
        return "unknown"
    end = text.find("---", 3)
    if end == -1:
        return "unknown"
    for line in text[3:end].strip().split("\n"):
        if line.strip().startswith("type:"):
            return line.partition(":")[2].strip().strip('"').strip("'")
    return "unknown"


def get_last_log_entry(vault: Path) -> str:
    log = vault / "wiki" / "log.md"
    if not log.exists():
        return "No log entries"
    try:
        lines = log.read_text(encoding="utf-8").strip().split("\n")
        for line in reversed(lines):
            if line.startswith("## ["):
                return line[3:].strip()
        return "No entries found"
    except (OSError, UnicodeDecodeError):
        return "Error reading log"


def get_qmd_status() -> str:
    try:
        result = subprocess.run(
            ["qmd", "status"], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if "Documents" in line or "Total:" in line or "Vectors:" in line:
                return line.strip()
        # Extract total docs and vectors
        lines = result.stdout.split("\n")
        total = vectors = "?"
        for line in lines:
            if "Total:" in line:
                total = line.split(":")[1].strip().split()[0]
            if "Vectors:" in line:
                vectors = line.split(":")[1].strip().split()[0]
        return f"{total} docs indexed, {vectors} embedded"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "qmd not available"


def main():
    parser = argparse.ArgumentParser(description="Snowiki status")
    parser.add_argument("--vault", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault) if args.vault else detect_vault()
    wiki_dir = vault / "wiki"
    sources_dir = vault / "sources"

    # Count wiki pages by type
    page_types = Counter()
    if wiki_dir.is_dir():
        for p in wiki_dir.rglob("*.md"):
            if p.name in ("index.md", "log.md"):
                continue
            page_types[parse_frontmatter_type(p)] += 1

    # Count sources by type
    source_types = Counter()
    if sources_dir.is_dir():
        for subdir in ["articles", "sessions", "notes"]:
            d = sources_dir / subdir
            if d.is_dir():
                source_types[subdir] = len(list(d.rglob("*.md")))

    total_pages = sum(page_types.values())
    total_sources = sum(source_types.values())
    last_log = get_last_log_entry(vault)
    qmd = get_qmd_status()

    if args.json:
        json.dump(
            {
                "pages": dict(page_types),
                "total_pages": total_pages,
                "sources": dict(source_types),
                "total_sources": total_sources,
                "last_log": last_log,
                "qmd": qmd,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        print()
        return

    print("📊 Snowiki Status\n")
    type_str = ", ".join(f"{k}: {v}" for k, v in sorted(page_types.items()))
    print(f"Pages:     {total_pages} ({type_str})")
    src_str = ", ".join(f"{k}: {v}" for k, v in sorted(source_types.items()))
    print(f"Sources:   {total_sources} ({src_str})")
    print(f"Last:      {last_log}")
    print(f"qmd:       {qmd}")


if __name__ == "__main__":
    main()
