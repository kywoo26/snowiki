from __future__ import annotations

import hashlib

from snowiki.fileback.render import (
    build_manual_question_note_body,
    build_manual_question_raw_path,
    build_raw_ref_for_note,
)


def test_render_manual_question_note_body_uses_review_schema() -> None:
    body = build_manual_question_note_body(
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
                "normalized": ["normalized/markdown/documents/source.json"],
                "raw": ["raw/markdown/ab/c123"],
            },
            "supporting_record_ids": ["source"],
            "supporting_raw_refs": [],
        },
    )

    assert body.startswith("---\n")
    assert 'type: "manual-question"' in body
    assert "# What did we ship?" in body
    assert "## Answer" in body
    assert "We shipped projection fileback." in body
    assert "- compiled/summaries/source.md" in body
    assert "- normalized/markdown/documents/source.json" in body
    assert "- raw/markdown/ab/c123" in body


def test_manual_question_raw_path_and_ref_are_deterministic() -> None:
    path = build_manual_question_raw_path(
        slug="what-did-we-ship",
        proposal_id="fileback-proposal-0123456789abcdef",
        recorded_at="2026-04-25T09:00:00Z",
    )
    content = "# What did we ship?"
    raw_ref = build_raw_ref_for_note(
        relative_path=path,
        content=content,
        mtime="2026-04-25T09:00:00Z",
    )

    assert path == "raw/manual/questions/2026/04/25/what-did-we-ship--0123456789abcdef.md"
    assert raw_ref == {
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "path": path,
        "size": len(content.encode("utf-8")),
        "mtime": "2026-04-25T09:00:00Z",
    }
