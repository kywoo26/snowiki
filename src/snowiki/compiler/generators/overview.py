from __future__ import annotations

from collections import Counter

from snowiki.schema.compiled import CompiledPage, PageType
from snowiki.schema.normalized import NormalizedRecord

from ..taxonomy import (
    append_section,
    merge_raw_refs,
    merge_string_list,
)


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
                "- Navigation artifacts: [[compiled/index]], [[compiled/log]]",
                "- Source freshness: run `snowiki status --output json` for current counts",
                *[
                    f"- {page_type}: {counter[page_type]}"
                    for page_type in sorted(counter)
                ],
            ]
        ),
    )

    return overview
