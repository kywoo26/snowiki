from __future__ import annotations

from collections import defaultdict

from snowiki.schema.compiled import CompiledPage, PageType
from snowiki.schema.normalized import NormalizedRecord

from ..projection import projected_title
from ..taxonomy import (
    append_section,
    iso_to_date,
    merge_raw_refs,
    merge_string_list,
)
from ..wikilinks import wikilink


def generate_index_page(
    records: list[NormalizedRecord],
    pages: list[CompiledPage],
) -> CompiledPage:
    """Generate the compiled wiki catalog entrypoint."""
    dates = [record.recorded_at for record in records]
    created = min(dates)[:10] if dates else "1970-01-01"
    updated = max(dates)[:10] if dates else created
    index = CompiledPage(
        page_type=PageType.INDEX,
        slug="index",
        title="Index",
        created=created,
        updated=updated,
        summary="Generated catalog of compiled Snowiki pages.",
    )
    merge_string_list(index.tags, ["compiled", "index", "navigation"])
    merge_string_list(
        index.related,
        [page.path for page in pages if page.page_type is not PageType.INDEX],
    )
    for page in pages:
        merge_raw_refs(index.raw_refs, page.raw_refs)
        merge_string_list(index.record_ids, page.record_ids)

    grouped: dict[str, list[CompiledPage]] = defaultdict(list)
    for page in pages:
        grouped[page.page_type.value].append(page)

    append_section(
        index,
        "Catalog Summary",
        "\n".join(
            [
                f"- Total compiled pages: {len(pages)}",
                "- Source freshness: run `snowiki status --output json` for current counts",
                "- Overview: [[compiled/overview]]",
                "- Log: [[compiled/log]]",
                *[
                    f"- {page_type}: {len(grouped[page_type])}"
                    for page_type in sorted(grouped)
                ],
            ]
        ),
    )

    for page_type in sorted(grouped):
        entries = [
            f"- {wikilink(page.path)} — {page.summary or page.title}"
            for page in sorted(grouped[page_type], key=lambda item: item.title.lower())
        ]
        append_section(index, page_type.title(), "\n".join(entries))
    return index


def generate_log_page(records: list[NormalizedRecord]) -> CompiledPage:
    """Generate a chronological normalized-record operation log."""
    dates = [record.recorded_at for record in records]
    created = min(dates)[:10] if dates else "1970-01-01"
    updated = max(dates)[:10] if dates else created
    log = CompiledPage(
        page_type=PageType.LOG,
        slug="log",
        title="Log",
        created=created,
        updated=updated,
        summary="Generated chronological log of normalized records.",
    )
    merge_string_list(log.tags, ["compiled", "log", "navigation"])
    for record in records:
        merge_raw_refs(log.raw_refs, record.raw_refs)
        merge_string_list(log.record_ids, [record.id])

    if not records:
        append_section(log, "Records", "No records yet.")
        return log
    for record in sorted(records, key=lambda item: (item.recorded_at, item.id)):
        append_section(log, f"[{iso_to_date(record.recorded_at)}] ingest | {record.id}", _record_log_body(record))
    return log


def _record_log_body(record: NormalizedRecord) -> str:
    return (
        f"- record_id: `{record.id}`\n"
        f"- source_type: `{record.source_type}`\n"
        f"- record_type: `{record.record_type}`\n"
        f"- title: {projected_title(record)}"
    )
