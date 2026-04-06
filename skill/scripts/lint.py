#!/usr/bin/env python3
"""Snowiki lint — wiki health checker.

Usage:
    python3 lint.py [--vault VAULT_DIR] [--json] [--errors-only]

Checks: S001 orphans, S002 unreferenced sources, S003 incomplete frontmatter,
        S004 broken wikilinks, S005 excessive contradictions, S006 stale pages.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

REQUIRED_FIELDS = {"title", "type", "created"}
WIKILINK_RE = re.compile(r'\[\[([^\]]+)\]\]')
MDLINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]+\.md[^)]*)\)')
CONTRADICTION_RE = re.compile(r'⚠️\s*[Cc]ontradiction')


def detect_vault():
    v = os.environ.get("VAULT_DIR")
    if v:
        return Path(v).expanduser()
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / ".obsidian").is_dir():
            return p
    return cwd


def parse_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in text[3:end].strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def collect_wikilinks(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    links = WIKILINK_RE.findall(text)
    # Also collect markdown-style links to .md files
    for _, href in MDLINK_RE.findall(text):
        links.append(href.split("#")[0].strip())
    return links


def count_contradictions(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return len(CONTRADICTION_RE.findall(text))


def run_lint(vault: Path) -> list[dict]:
    findings = []
    wiki_dir = vault / "wiki"
    sources_dir = vault / "sources"

    if not wiki_dir.is_dir():
        findings.append({"code": "S003", "severity": "ERROR",
                         "message": "wiki/ directory not found", "path": str(wiki_dir)})
        return findings

    wiki_pages = [p for p in wiki_dir.rglob("*.md") if p.name not in ("index.md", "log.md")]

    # Collect all inbound links
    all_links = set()
    all_links_by_page = {}
    for page in wiki_pages:
        links = collect_wikilinks(page)
        all_links_by_page[page] = links
        all_links.update(links)

    for special in ["index.md", "log.md"]:
        sp = wiki_dir / special
        if sp.exists():
            all_links.update(collect_wikilinks(sp))

    # S001: Orphan pages
    for page in wiki_pages:
        rel = page.relative_to(vault)
        stem = page.stem
        is_linked = any(
            stem in link or str(rel) in link or str(rel.with_suffix("")) in link
            for link in all_links
        )
        if not is_linked:
            findings.append({"code": "S001", "severity": "WARN",
                             "message": "Orphan page: no inbound links",
                             "path": str(rel)})

    # S002: Unreferenced sources
    if sources_dir.is_dir():
        all_sources_refs = set()
        for page in wiki_pages:
            fm = parse_frontmatter(page)
            src = fm.get("sources", "")
            if src:
                all_sources_refs.update(s.strip() for s in src.split(","))

        for src_file in sources_dir.rglob("*.md"):
            src_rel = str(src_file.relative_to(vault))
            src_stem = src_file.stem
            referenced = any(src_stem in ref or src_rel in ref for ref in all_sources_refs)
            if not referenced:
                findings.append({"code": "S002", "severity": "INFO",
                                 "message": "Source not referenced by any wiki page",
                                 "path": src_rel})

    # S003: Incomplete frontmatter
    for page in wiki_pages:
        fm = parse_frontmatter(page)
        missing = REQUIRED_FIELDS - set(fm.keys())
        if missing:
            findings.append({"code": "S003", "severity": "ERROR",
                             "message": f"Missing frontmatter: {', '.join(sorted(missing))}",
                             "path": str(page.relative_to(vault))})

    # S004: Broken wikilinks
    for page, links in all_links_by_page.items():
        for link in links:
            link_clean = link.split("|")[0].split("#")[0].strip()
            if not link_clean:
                continue
            # Try resolving relative to vault root
            target = vault / link_clean
            # Also try resolving relative to the page's directory
            target_rel = page.parent / link_clean
            if (not target.exists() and not target.with_suffix(".md").exists()
                    and not target_rel.exists() and not target_rel.with_suffix(".md").exists()):
                findings.append({"code": "S004", "severity": "ERROR",
                                 "message": f"Broken link: [[{link}]]",
                                 "path": str(page.relative_to(vault))})

    # S005: Excessive contradictions
    for page in wiki_pages:
        count = count_contradictions(page)
        if count >= 3:
            findings.append({"code": "S005", "severity": "WARN",
                             "message": f"{count} contradiction markers",
                             "path": str(page.relative_to(vault))})

    # S006: Stale pages
    cutoff = datetime.now() - timedelta(days=30)
    for page in wiki_pages:
        fm = parse_frontmatter(page)
        updated = fm.get("updated") or fm.get("created")
        if updated:
            try:
                dt = datetime.fromisoformat(updated)
                if dt < cutoff:
                    findings.append({"code": "S006", "severity": "INFO",
                                     "message": f"Not updated since {updated}",
                                     "path": str(page.relative_to(vault))})
            except ValueError:
                pass

    return findings


def main():
    parser = argparse.ArgumentParser(description="Snowiki lint — wiki health checker")
    parser.add_argument("--vault", default=None, help="Vault directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--errors-only", action="store_true", help="Only show errors")
    args = parser.parse_args()

    vault = Path(args.vault) if args.vault else detect_vault()
    findings = run_lint(vault)

    if args.errors_only:
        findings = [f for f in findings if f["severity"] == "ERROR"]

    if args.json:
        json.dump({"findings": findings, "total": len(findings)}, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warns = sum(1 for f in findings if f["severity"] == "WARN")
    infos = sum(1 for f in findings if f["severity"] == "INFO")

    if not findings:
        print("✅ Snowiki lint: all clear!")
        return

    print("🔍 Snowiki Lint Report\n")
    for f in sorted(findings, key=lambda x: ["ERROR", "WARN", "INFO"].index(x["severity"])):
        sev = {"ERROR": "❌", "WARN": "⚠️", "INFO": "ℹ️"}[f["severity"]]
        print(f"  {f['code']} {sev}  {f['message']}")
        if f.get("path"):
            print(f"       → {f['path']}")
    print(f"\nSummary: {errors} errors, {warns} warnings, {infos} info")
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
