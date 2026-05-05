from __future__ import annotations

from datetime import UTC, datetime

import pytest

from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.scoring import RuntimeScoringPolicy


def _document(
    document_id: str,
    *,
    path: str | None = None,
    kind: str = "page",
    recorded_at: datetime | None = None,
) -> SearchDocument:
    return SearchDocument(
        id=document_id,
        path=path or f"docs/{document_id}.md",
        kind=kind,
        title=document_id,
        content="contract test fixture",
        recorded_at=recorded_at,
    )


class _Tokenizer:
    def tokenize(self, text: str) -> tuple[str, ...]:
        return tuple(text.lower().split())

    def normalize(self, text: str) -> str:
        return " ".join(self.tokenize(text))


def test_score_candidate_derives_sorted_matched_terms_from_token_evidence() -> None:
    policy = RuntimeScoringPolicy()
    hit = policy.score_candidate(
        document=_document("runtime-policy"),
        raw_score=1.25,
        query_tokens=("runtime", "policy", "missing"),
        document_tokens=("policy", "runtime", "snowiki"),
        tokenizer=_Tokenizer(),
        query="runtime policy",
    )

    assert hit == SearchHit(
        document=_document("runtime-policy"),
        score=1.25,
        matched_terms=("policy", "runtime"),
    )


def test_score_candidate_rejects_zero_score_candidates_without_match_evidence() -> None:
    policy = RuntimeScoringPolicy()
    hit = policy.score_candidate(
        document=_document("unmatched"),
        raw_score=0.0,
        query_tokens=("runtime",),
        document_tokens=("snowiki",),
        tokenizer=_Tokenizer(),
        query="runtime",
    )

    assert hit is None


def test_score_candidate_rejects_zero_score_candidates_with_boosts_only() -> None:
    policy = RuntimeScoringPolicy()
    hit = policy.score_candidate(
        document=_document("runtime-note", path="sessions/runtime-note.json", kind="session"),
        raw_score=0.0,
        query_tokens=("runtime", "missing"),
        document_tokens=("snowiki",),
        tokenizer=_Tokenizer(),
        query="runtime missing",
        exact_path_bias=True,
        kind_weights={"session": 1.15},
    )

    assert hit is None


def test_score_candidate_applies_path_boosts_kind_weight_and_recency_tie_break() -> None:
    recorded_at = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
    document = _document(
        "session-runtime-policy",
        path="sessions/runtime policy.md",
        kind="session",
        recorded_at=recorded_at,
    )

    policy = RuntimeScoringPolicy()
    hit = policy.score_candidate(
        document=document,
        raw_score=1.0,
        query_tokens=("runtime", "policy"),
        document_tokens=("runtime",),
        tokenizer=_Tokenizer(),
        query="runtime policy",
        exact_path_bias=True,
        kind_weights={"session": 1.15, "page": 0.85},
    )

    assert hit is not None
    expected_without_recency = (1.0 + 2.0 + 2.5) * 1.15
    expected = expected_without_recency + recorded_at.timestamp() / 10_000_000_000.0
    assert hit.score == pytest.approx(expected)
    assert hit.matched_terms == ("runtime",)


def test_score_candidate_uses_default_kind_weight_when_kind_is_not_named() -> None:
    policy = RuntimeScoringPolicy()
    hit = policy.score_candidate(
        document=_document("kiwi-note", kind="note"),
        raw_score=2.0,
        query_tokens=("kiwi",),
        document_tokens=("kiwi",),
        tokenizer=_Tokenizer(),
        query="kiwi intent",
        kind_weights={"session": 1.15, "page": 0.85},
    )

    assert hit is not None
    assert hit.score == pytest.approx(2.0)


def test_score_candidate_keeps_path_phrase_boost_independent_from_exact_path_bias() -> None:
    policy = RuntimeScoringPolicy()
    hit = policy.score_candidate(
        document=_document("runtime-policy", path="docs/runtime policy.md"),
        raw_score=0.0,
        query_tokens=("unmatched",),
        document_tokens=(),
        tokenizer=_Tokenizer(),
        query="runtime policy",
        exact_path_bias=False,
    )

    assert hit is not None
    assert hit.score == pytest.approx(2.5)
    assert hit.matched_terms == ()


def test_sort_key_is_deterministic_for_score_path_and_document_id_ties() -> None:
    policy = RuntimeScoringPolicy()
    hits = [
        SearchHit(document=_document("b", path="docs/shared.md"), score=3.0, matched_terms=("x",)),
        SearchHit(document=_document("a", path="docs/shared.md"), score=3.0, matched_terms=("x",)),
        SearchHit(document=_document("z", path="docs/alpha.md"), score=3.0, matched_terms=("x",)),
        SearchHit(document=_document("top", path="docs/top.md"), score=4.0, matched_terms=("x",)),
    ]

    ranked = sorted(hits, key=policy.sort_key)

    assert [hit.document.id for hit in ranked] == ["top", "z", "a", "b"]


def test_sort_key_breaks_tied_scores_by_recency_before_path_and_id() -> None:
    policy = RuntimeScoringPolicy()
    older = SearchHit(
        document=_document(
            "older",
            path="docs/shared.md",
            recorded_at=datetime(2026, 4, 1, tzinfo=UTC),
        ),
        score=2.0,
        matched_terms=("x",),
    )
    newer = SearchHit(
        document=_document(
            "newer",
            path="docs/zzz.md",
            recorded_at=datetime(2026, 4, 2, tzinfo=UTC),
        ),
        score=2.0,
        matched_terms=("x",),
    )

    ranked = sorted([older, newer], key=policy.sort_key)

    assert [hit.document.id for hit in ranked] == ["newer", "older"]


def test_rank_candidates_orders_ties_by_recency_path_then_id() -> None:
    policy = RuntimeScoringPolicy(recency_divisor=1_000_000_000_000_000_000.0)
    candidates = [
        SearchHit(
            document=_document(
                "path-b",
                path="docs/b.md",
                recorded_at=datetime(2026, 4, 1, tzinfo=UTC),
            ),
            score=1.0,
            matched_terms=(),
        ),
        SearchHit(
            document=_document(
                "path-a",
                path="docs/a.md",
                recorded_at=datetime(2026, 4, 1, tzinfo=UTC),
            ),
            score=1.0,
            matched_terms=(),
        ),
        SearchHit(
            document=_document(
                "newer",
                path="docs/z.md",
                recorded_at=datetime(2026, 4, 2, tzinfo=UTC),
            ),
            score=1.0,
            matched_terms=(),
        ),
        SearchHit(
            document=_document(
                "path-a-2",
                path="docs/a.md",
                recorded_at=datetime(2026, 4, 1, tzinfo=UTC),
            ),
            score=1.0,
            matched_terms=(),
        ),
    ]

    ranked = policy.rank_candidates(
        candidates,
        query="contract",
        tokenizer=_Tokenizer(),
        document_tokens=lambda _document_id: ("contract",),
    )

    assert [hit.document.id for hit in ranked] == [
        "newer",
        "path-a",
        "path-a-2",
        "path-b",
    ]
