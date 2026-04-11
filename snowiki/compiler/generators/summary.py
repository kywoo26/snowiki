from __future__ import annotations

from ..paths import (  # pyright: ignore[reportMissingImports]
    session_path_for_id,
    summary_slug_for_record,
)
from ..taxonomy import (
    CompiledPage,
    NormalizedRecord,
    PageType,
    TaxonomyItem,
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
)


def generate_summary_pages(records: list[NormalizedRecord]) -> list[CompiledPage]:
    pages: list[CompiledPage] = []
    overview_path = compiled_page_path(PageType.OVERVIEW, "overview")

    for record in records:
        date = iso_to_date(record.recorded_at)
        summary_text = record_summary(record)
        title = f"Summary: {record_title(record)}"
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
        related.extend(item_path(item) for item in taxonomy_items_for_record(record))

        merge_string_list(page.related, related)
        merge_string_list(
            page.tags, [record.source_type, record.record_type, "summary"]
        )
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

        facts = record.payload.get("facts")
        if isinstance(facts, list) and facts:
            append_section(
                page,
                "Facts",
                "\n".join(f"- {fact}" for fact in facts if isinstance(fact, str)),
            )

        inferences = record.payload.get("inferences")
        if isinstance(inferences, list) and inferences:
            append_section(
                page,
                "Inferences",
                "\n".join(f"- {item}" for item in inferences if isinstance(item, str)),
            )

        pages.append(page)

    return sorted(pages, key=lambda page: page.path)


def item_path(item: TaxonomyItem) -> str:
    page_type = item.page_type
    title = item.title
    return compiled_page_path(page_type, slugify(title))
