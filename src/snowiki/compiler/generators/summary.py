from __future__ import annotations

from snowiki.schema.compiled import CompiledPage, PageType, compiled_page_path, slugify
from snowiki.schema.normalized import NormalizedRecord

from ..paths import (
    session_path_for_id,
    summary_slug_for_record,
)
from ..projection import (
    projected_sections,
    projected_source_identity,
    projected_summary,
    projected_tags,
    projected_taxonomy_items,
    projected_title,
)
from ..taxonomy import (
    TaxonomyItem,
    append_section,
    iso_to_date,
    merge_raw_refs,
    merge_string_list,
    record_session_id,
)


def generate_summary_pages(records: list[NormalizedRecord]) -> list[CompiledPage]:
    pages: list[CompiledPage] = []
    overview_path = compiled_page_path(PageType.OVERVIEW, "overview")

    for record in records:
        date = iso_to_date(record.recorded_at)
        summary_text = projected_summary(record)
        title = f"Summary: {projected_title(record)}"
        page = CompiledPage(
            page_type=PageType.SUMMARY,
            slug=summary_slug_for_record(record),
            title=title,
            created=date,
            updated=date,
            summary=summary_text,
        )

        related = [overview_path]
        session_id = record_session_id(record)
        if session_id is not None:
            related.append(session_path_for_id(session_id))
        related.extend(item_path(item) for item in projected_taxonomy_items(record))

        merge_string_list(page.related, related)
        merge_string_list(
            page.tags, [record.source_type, record.record_type, "summary"]
        )
        merge_string_list(page.tags, projected_tags(record))
        merge_string_list(page.record_ids, [record.id])
        merge_raw_refs(page.raw_refs, record.raw_refs)
        merge_string_list(
            page.sources, [ref.get("path", "") for ref in record.raw_refs]
        )

        append_section(
            page,
            "Record",
            "\n".join(
                [
                    f"- Normalized path: `{record.path}`",
                    f"- Record type: `{record.record_type}`",
                    f"- Source type: `{record.source_type}`",
                ]
            ),
        )

        source_identity = projected_source_identity(record)
        source_identity_lines: list[str] = []
        for key in ("source_root", "relative_path", "content_hash"):
            value = source_identity.get(key)
            if value:
                source_identity_lines.append(f"- {key}: `{value}`")
        append_section(page, "Source Identity", "\n".join(source_identity_lines))
        for section in projected_sections(record):
            append_section(page, section["title"], section["body"])

        pages.append(page)

    return sorted(pages, key=lambda page: page.path)


def item_path(item: TaxonomyItem) -> str:
    page_type = item.page_type
    title = item.title
    return compiled_page_path(page_type, slugify(title))
