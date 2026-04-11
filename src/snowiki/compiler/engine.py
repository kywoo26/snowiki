from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from pathlib import Path

from snowiki.storage.provenance import ProvenanceTracker
from snowiki.storage.zones import StoragePaths, atomic_write_bytes, relative_to_root

from .generators.concept import generate_concept_pages
from .generators.overview import generate_overview_page
from .generators.question import generate_question_pages
from .generators.session import generate_session_pages
from .generators.summary import generate_summary_pages
from .provenance_links import (
    raw_source_paths,
    render_provenance_section,
)
from .taxonomy import CompiledPage, NormalizedRecord, sorted_unique
from .wikilinks import apply_backlinks, render_related_section

type FrontmatterScalar = None | bool | int | float | str
type FrontmatterValue = FrontmatterScalar | list[str]


class CompilerEngine:
    """Compile normalized records into wiki pages on disk."""

    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()
        self.provenance = ProvenanceTracker(self.paths.root)

    @property
    def root(self) -> Path:
        """Return the workspace root directory."""
        return self.paths.root

    @property
    def compiled_root(self) -> Path:
        """Return the compiled wiki output directory."""
        return self.paths.compiled

    def load_normalized_records(self) -> list[NormalizedRecord]:
        """Load normalized records and their raw provenance references."""
        records: list[NormalizedRecord] = []
        for path in sorted(
            self.paths.normalized.rglob("*.json"),
            key=lambda candidate: candidate.as_posix(),
        ):
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw_refs = self.provenance.query_raw_sources(payload)
            normalized_raw_refs = [
                {str(key): value for key, value in raw_ref.items()}
                for raw_ref in raw_refs
            ]
            records.append(
                NormalizedRecord(
                    id=str(payload.get("id", path.stem)),
                    path=relative_to_root(self.root, path),
                    source_type=str(payload.get("source_type", "unknown")),
                    record_type=str(payload.get("record_type", "record")),
                    recorded_at=str(payload.get("recorded_at", "1970-01-01T00:00:00Z")),
                    payload=payload,
                    raw_refs=normalized_raw_refs,
                )
            )
        return records

    def build_pages(
        self, records: Sequence[NormalizedRecord] | None = None
    ) -> list[CompiledPage]:
        """Build compiled wiki pages from normalized records."""
        resolved_records = (
            list(records) if records is not None else self.load_normalized_records()
        )
        pages: list[CompiledPage] = []
        pages.extend(generate_summary_pages(resolved_records))
        pages.extend(generate_concept_pages(resolved_records))
        pages.extend(generate_question_pages(resolved_records))
        pages.extend(generate_session_pages(resolved_records))
        pages.append(generate_overview_page(resolved_records, pages))
        return apply_backlinks(pages)

    def rebuild(self) -> list[str]:
        """Rebuild compiled wiki pages on disk and return written paths."""
        pages = self.build_pages()
        self._reset_compiled_zone()

        written_paths: list[str] = []
        for page in pages:
            target = self.root / page.path
            rendered = self._render_page(page)
            atomic_write_bytes(target, rendered.encode("utf-8"))
            written_paths.append(relative_to_root(self.root, target))
        return sorted(written_paths)

    def _reset_compiled_zone(self) -> None:
        self.compiled_root.mkdir(parents=True, exist_ok=True)
        for child in self.compiled_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def _render_page(self, page: CompiledPage) -> str:
        frontmatter = self._render_frontmatter(page)
        lines = [frontmatter, "", f"# {page.title}"]
        if page.summary:
            lines.extend(["", page.summary])

        for section in page.sections:
            lines.extend(["", f"## {section.title}", "", section.body])

        lines.extend(
            [
                "",
                render_related_section(page.related),
                "",
                render_provenance_section(page.raw_refs),
                "",
            ]
        )
        return "\n".join(lines)

    def _render_frontmatter(self, page: CompiledPage) -> str:
        sources = sorted_unique([*page.sources, *raw_source_paths(page.raw_refs)])
        related = sorted_unique(page.related)
        tags = sorted_unique(page.tags)
        record_ids = sorted_unique(page.record_ids)

        fields: list[tuple[str, FrontmatterValue]] = [
            ("title", page.title),
            ("type", page.page_type.value),
            ("created", page.created),
            ("updated", page.updated),
            ("summary", page.summary),
            ("sources", sources),
            ("related", related),
            ("tags", tags),
            ("record_ids", record_ids),
        ]
        fields.extend(sorted(page.extra_frontmatter.items()))

        lines = ["---"]
        for key, value in fields:
            lines.extend(self._render_yaml_field(key, value))
        lines.append("---")
        return "\n".join(lines)

    def _render_yaml_field(self, key: str, value: FrontmatterValue) -> list[str]:
        if isinstance(value, list):
            if not value:
                return [f"{key}: []"]
            lines = [f"{key}:"]
            for item in value:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
            return lines

        if isinstance(value, bool):
            return [f"{key}: {'true' if value else 'false'}"]

        if value is None:
            return [f"{key}: null"]

        if isinstance(value, (int, float)):
            return [f"{key}: {value}"]

        return [f"{key}: {json.dumps(str(value), ensure_ascii=False)}"]
