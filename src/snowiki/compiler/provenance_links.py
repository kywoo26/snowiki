from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from snowiki.storage.provenance import dedupe_raw_refs as dedupe_provenance_raw_refs


def dedupe_raw_refs(raw_refs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return dedupe_provenance_raw_refs(raw_refs, sort=True)


def raw_source_paths(raw_refs: Iterable[Mapping[str, Any]]) -> list[str]:
    return sorted(
        {
            str(entry.get("path", "")).strip()
            for entry in dedupe_raw_refs(raw_refs)
            if str(entry.get("path", "")).strip()
        }
    )


def render_provenance_section(raw_refs: Iterable[Mapping[str, Any]]) -> str:
    entries = dedupe_raw_refs(raw_refs)
    if not entries:
        return "## Provenance\n\n- _No raw sources recorded._"

    lines = ["## Provenance", ""]
    for entry in entries:
        path = str(entry.get("path", "unknown"))
        sha256 = str(entry.get("sha256", ""))
        mtime = str(entry.get("mtime", ""))
        size = entry.get("size", "")
        parts = [
            part
            for part in (
                f"sha256: {sha256}" if sha256 else "",
                f"size: {size}" if size != "" else "",
                f"mtime: {mtime}" if mtime else "",
            )
            if part
        ]
        if parts:
            lines.append(f"- `{path}` ({', '.join(parts)})")
        else:
            lines.append(f"- `{path}`")
    return "\n".join(lines)
