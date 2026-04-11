from __future__ import annotations

from ..paths import (  # pyright: ignore[reportMissingImports]
    session_path_for_id,
    summary_path_for_record,
)
from ..taxonomy import (
    CompiledPage,
    NormalizedRecord,
    PageType,
    append_section,
    compiled_page_path,
    iso_to_date,
    merge_raw_refs,
    merge_string_list,
    record_session_id,
    record_summary,
    record_title,
    slugify,
    taxonomy_items_for_record,
    upsert_page,
)

SUPPORTED_PAGE_TYPES = {PageType.CONCEPT, PageType.ENTITY, PageType.TOPIC}


def generate_concept_pages(records: list[NormalizedRecord]) -> list[CompiledPage]:
    pages: dict[str, CompiledPage] = {}
    overview_path = compiled_page_path(PageType.OVERVIEW, "overview")

    for record in records:
        date = iso_to_date(record.recorded_at)
        summary_path = summary_path_for_record(record)
        session_id = record_session_id(record)
        all_items = taxonomy_items_for_record(record)
        related_item_paths = [
            compiled_page_path(item.page_type, slugify(item.title))
            for item in all_items
        ]

        for item in all_items:
            if item.page_type not in SUPPORTED_PAGE_TYPES:
                continue

            page = upsert_page(
                pages,
                page_type=item.page_type,
                slug=slugify(item.title),
                title=item.title,
                created=date,
                updated=date,
                summary=item.summary or f"Compiled concept page for {item.title}.",
            )

            related = [overview_path, summary_path, *related_item_paths]
            if session_id is not None:
                related.append(session_path_for_id(session_id))

            merge_string_list(page.related, related)
            merge_string_list(
                page.tags, [*item.tags, item.page_type.value, record.source_type]
            )
            merge_string_list(page.record_ids, [record.id])
            merge_string_list(
                page.sources, [ref.get("path", "") for ref in record.raw_refs]
            )
            merge_raw_refs(page.raw_refs, record.raw_refs)
            for key, value in item.metadata.items():
                page.extra_frontmatter.setdefault(key, value)

            append_section(
                page,
                f"Source: {record_title(record)}",
                "\n".join(
                    [
                        record_summary(record),
                        "",
                        f"Related summary: [[{summary_path[:-3]}]]",
                    ]
                ),
            )

    return sorted(pages.values(), key=lambda page: page.path)
