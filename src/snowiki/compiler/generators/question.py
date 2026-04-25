from __future__ import annotations

from ..paths import (  # pyright: ignore[reportMissingImports]
    session_path_for_id,
    summary_path_for_record,
)
from ..projection import projected_summary, projected_taxonomy_items, projected_title
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
    slugify,
    upsert_page,
)

SUPPORTED_PAGE_TYPES = {PageType.QUESTION, PageType.PROJECT, PageType.DECISION}


def generate_question_pages(records: list[NormalizedRecord]) -> list[CompiledPage]:
    pages: dict[str, CompiledPage] = {}
    overview_path = compiled_page_path(PageType.OVERVIEW, "overview")

    for record in records:
        date = iso_to_date(record.recorded_at)
        summary_path = summary_path_for_record(record)
        session_id = record_session_id(record)
        all_items = projected_taxonomy_items(record)
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
                summary=item.summary
                or f"Compiled {item.page_type.value} page for {item.title}.",
            )

            related = [overview_path, summary_path, *related_item_paths]
            related.extend(_supporting_compiled_paths(record))
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

            answer_markdown = _answer_markdown(record)
            if answer_markdown:
                append_section(page, "Answer", answer_markdown)

            append_section(
                page,
                f"Evidence from {projected_title(record)}",
                "\n".join(
                    [
                        projected_summary(record),
                        "",
                        f"Related summary: [[{summary_path[:-3]}]]",
                    ]
                ),
            )

    return sorted(pages.values(), key=lambda page: page.path)


def _answer_markdown(record: NormalizedRecord) -> str:
    value = record.payload.get("answer_markdown")
    return value.strip() if isinstance(value, str) else ""


def _supporting_compiled_paths(record: NormalizedRecord) -> list[str]:
    value = record.payload.get("supporting_paths")
    if not isinstance(value, list):
        return []
    return sorted(
        {
            item.strip()
            for item in value
            if isinstance(item, str)
            and item.strip()
            and item.strip().startswith("compiled/")
        }
    )
