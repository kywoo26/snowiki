from __future__ import annotations

from collections import defaultdict

from snowiki.schema.compiled import CompiledPage, PageType, compiled_page_path, slugify
from snowiki.schema.normalized import NormalizedRecord

from ..paths import (  # pyright: ignore[reportMissingImports]
    session_slug_for_id,
    summary_path_for_record,
)
from ..projection import projected_summary, projected_taxonomy_items, projected_title
from ..taxonomy import (
    append_section,
    iso_to_date,
    merge_raw_refs,
    merge_string_list,
    record_session_id,
)


def generate_session_pages(records: list[NormalizedRecord]) -> list[CompiledPage]:
    grouped: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in records:
        session_id = record_session_id(record)
        if session_id is not None:
            grouped[session_id].append(record)

    pages: list[CompiledPage] = []
    overview_path = compiled_page_path(PageType.OVERVIEW, "overview")

    for session_id in sorted(grouped):
        session_records = sorted(
            grouped[session_id], key=lambda record: (record.recorded_at, record.path)
        )
        anchor = session_records[0]
        date = iso_to_date(anchor.recorded_at)
        title = f"Session: {projected_title(anchor)}"
        page = CompiledPage(
            page_type=PageType.SESSION,
            slug=session_slug_for_id(session_id),
            title=title,
            created=date,
            updated=iso_to_date(session_records[-1].recorded_at),
            summary=f"Compiled session page for `{session_id}` with {len(session_records)} normalized records.",
        )

        related = [overview_path]
        merge_string_list(page.record_ids, [session_id])

        timeline_lines: list[str] = []
        for record in session_records:
            merge_string_list(page.record_ids, [record.id])
            merge_string_list(
                page.sources, [ref.get("path", "") for ref in record.raw_refs]
            )
            merge_raw_refs(page.raw_refs, record.raw_refs)
            related.append(summary_path_for_record(record))
            related.extend(
                compiled_page_path(item.page_type, slugify(item.title))
                for item in projected_taxonomy_items(record)
            )
            timeline_lines.append(
                f"- {iso_to_date(record.recorded_at)} · `{record.record_type}` · {projected_title(record)}"
            )

        merge_string_list(page.related, related)
        merge_string_list(page.tags, ["session", anchor.source_type])
        append_section(page, "Timeline", "\n".join(timeline_lines))
        append_section(
            page,
            "Summary",
            "\n".join(projected_summary(record) for record in session_records),
        )
        pages.append(page)

    return sorted(pages, key=lambda page: page.path)
