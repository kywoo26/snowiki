from __future__ import annotations

from collections import Counter

from ..taxonomy import (
    CompiledPage,
    NormalizedRecord,
    PageType,
    append_section,
    merge_raw_refs,
    merge_string_list,
)
from ..wikilinks import wikilink


def generate_overview_page(
    records: list[NormalizedRecord],
    pages: list[CompiledPage],
) -> CompiledPage:
    dates = [record.recorded_at for record in records]
    created = min(dates)[:10] if dates else "1970-01-01"
    updated = max(dates)[:10] if dates else created
    overview = CompiledPage(
        page_type=PageType.OVERVIEW,
        slug="overview",
        title="Overview",
        created=created,
        updated=updated,
        summary="Auto-generated synthesis of compiled pages from normalized storage.",
    )

    counter = Counter(
        page.page_type.value
        for page in pages
        if page.page_type is not PageType.OVERVIEW
    )
    merge_string_list(overview.tags, ["overview", "compiled"])
    merge_string_list(
        overview.related,
        [page.path for page in pages if page.page_type is not PageType.OVERVIEW],
    )
    for page in pages:
        merge_string_list(overview.sources, page.sources)
        merge_raw_refs(overview.raw_refs, page.raw_refs)
        merge_string_list(overview.record_ids, page.record_ids)

    append_section(
        overview,
        "Compilation Summary",
        "\n".join(
            [
                f"- Normalized records: {len(records)}",
                *[
                    f"- {page_type}: {counter[page_type]}"
                    for page_type in sorted(counter)
                ],
            ]
        ),
    )

    grouped: dict[str, list[str]] = {}
    for page in sorted(
        (page for page in pages if page.page_type is not PageType.OVERVIEW),
        key=lambda page: (page.page_type.value, page.title.lower()),
    ):
        grouped.setdefault(page.page_type.value, []).append(f"- {wikilink(page.path)}")

    for page_type in sorted(grouped):
        append_section(overview, page_type.title(), "\n".join(grouped[page_type]))

    return overview
