from __future__ import annotations

from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.rerank import blend_hits_by_kind


def _hit(document_id: str, *, kind: str, score: float = 1.0) -> SearchHit:
    return SearchHit(
        document=SearchDocument(
            id=document_id,
            path=f"{kind}/{document_id}.md",
            kind=kind,
            title=document_id,
            content=document_id,
        ),
        score=score,
        matched_terms=(document_id,),
    )


def test_blend_hits_by_kind_round_robins_sorted_kinds() -> None:
    hits = [
        _hit("session-1", kind="session"),
        _hit("session-2", kind="session"),
        _hit("page-1", kind="page"),
        _hit("page-2", kind="page"),
        _hit("note-1", kind="note"),
    ]

    blended = blend_hits_by_kind(hits, limit=5)

    assert [hit.document.id for hit in blended] == [
        "note-1",
        "page-1",
        "session-1",
        "page-2",
        "session-2",
    ]


def test_blend_hits_by_kind_preserves_single_kind_order() -> None:
    hits = [
        _hit("page-1", kind="page", score=3.0),
        _hit("page-2", kind="page", score=2.0),
        _hit("page-3", kind="page", score=1.0),
    ]

    blended = blend_hits_by_kind(hits, limit=2)

    assert [hit.document.id for hit in blended] == ["page-1", "page-2"]


def test_blend_hits_by_kind_handles_empty_hits() -> None:
    assert blend_hits_by_kind([], limit=10) == []
