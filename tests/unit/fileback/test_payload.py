from __future__ import annotations

from snowiki.fileback.payload import (
    build_fileback_normalized_path,
    build_fileback_record_id,
    build_proposed_write_set,
    normalized_store_payload,
)


def test_build_proposed_write_set_owns_projection_payload_shape() -> None:
    write_set = build_proposed_write_set(
        proposal_id="fileback-proposal-0123456789abcdef",
        created_at="2026-04-25T09:00:00Z",
        draft={
            "question": "What did we ship?",
            "answer_markdown": "We shipped projection fileback.",
            "summary": "Projection fileback shipped.",
        },
        target={
            "title": "What did we ship?",
            "slug": "what-did-we-ship",
            "compiled_path": "compiled/questions/what-did-we-ship.md",
        },
        evidence={
            "requested_paths": ["compiled/summaries/source.md"],
            "resolved_paths": {
                "compiled": ["compiled/summaries/source.md"],
                "normalized": [],
                "raw": [],
            },
            "supporting_record_ids": ["source"],
            "supporting_raw_refs": [],
        },
    )

    normalized = write_set["normalized_record"]
    projection = normalized["projection"]
    assert write_set["raw_note_path"].startswith("raw/manual/questions/2026/04/25/")
    assert normalized["source_type"] == "manual-question"
    assert normalized["record_type"] == "question"
    assert normalized["raw_ref"]["path"] == write_set["raw_note_path"]
    assert projection["title"] == "What did we ship?"
    assert projection["summary"] == "Projection fileback shipped."
    assert projection["tags"] == ["manual-question", "fileback"]
    assert projection["taxonomy"]["questions"] == [
        {
            "title": "What did we ship?",
            "summary": "Projection fileback shipped.",
            "tags": ["manual-question", "fileback"],
        }
    ]


def test_fileback_ids_paths_and_store_payload_are_explicit_contracts() -> None:
    record_id = build_fileback_record_id(
        "what-did-we-ship", "fileback-proposal-0123456789abcdef"
    )

    assert record_id.startswith("question-what-did-we-ship-")
    assert build_fileback_normalized_path(
        record_id,
        recorded_at="2026-04-25T09:00:00Z",
    ) == f"normalized/manual-question/2026/04/25/{record_id}.json"
    assert normalized_store_payload(
        {
            "id": record_id,
            "record_type": "question",
            "recorded_at": "2026-04-25T09:00:00Z",
            "source_type": "manual-question",
            "raw_ref": {"path": "raw/manual/questions/note.md"},
            "provenance": {"raw_refs": []},
            "projection": {"title": "What did we ship?"},
        }
    ) == {"projection": {"title": "What did we ship?"}}
