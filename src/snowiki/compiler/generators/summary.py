from __future__ import annotations

from typing import cast

from ..paths import (
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
        if record.source_type == "markdown" and record.record_type == "document":
            summary = record.payload.get("summary")
            summary_text = summary if isinstance(summary, str) else ""
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
        if record.source_type == "markdown" and record.record_type == "document":
            promoted = record.payload.get("promoted_frontmatter")
            if isinstance(promoted, dict):
                promoted_fields = cast(dict[str, object], promoted)
                tags = promoted_fields.get("tags")
                if isinstance(tags, list):
                    tag_values = cast(list[object], tags)
                    merge_string_list(
                        page.tags, [tag for tag in tag_values if isinstance(tag, str)]
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

        if record.source_type == "markdown" and record.record_type == "document":
            source_identity: list[str] = []
            for key in ("source_root", "relative_path", "content_hash"):
                value = record.payload.get(key)
                if isinstance(value, str) and value:
                    source_identity.append(f"- {key}: `{value}`")
            append_section(page, "Source Identity", "\n".join(source_identity))

            text = record.payload.get("text")
            if isinstance(text, str) and text.strip():
                append_section(page, "Document", text)

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
