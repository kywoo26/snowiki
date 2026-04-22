from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .baselines import run_baseline_comparison
    from .candidates import (
        CANDIDATE_MATRIX,
        TokenizerCandidate,
        admitted_candidates,
        get_candidate,
    )
    from .index import CorpusBundle
    from .qrels import BenchmarkQuery, QrelEntry, load_qrels
    from .scoring import (
        evaluate_quality,
        evaluate_quality_thresholds,
        evaluate_sliced_quality,
    )

__all__ = [
    "BenchmarkQuery",
    "CANDIDATE_MATRIX",
    "CorpusBundle",
    "QrelEntry",
    "TokenizerCandidate",
    "admitted_candidates",
    "evaluate_quality",
    "evaluate_quality_thresholds",
    "evaluate_sliced_quality",
    "get_candidate",
    "load_qrels",
    "run_baseline_comparison",
]


def __getattr__(name: str) -> object:
    if name == "run_baseline_comparison":
        from .baselines import run_baseline_comparison

        return run_baseline_comparison

    if name in {"CANDIDATE_MATRIX", "TokenizerCandidate", "admitted_candidates", "get_candidate"}:
        from .candidates import (
            CANDIDATE_MATRIX,
            TokenizerCandidate,
            admitted_candidates,
            get_candidate,
        )

        return {
            "CANDIDATE_MATRIX": CANDIDATE_MATRIX,
            "TokenizerCandidate": TokenizerCandidate,
            "admitted_candidates": admitted_candidates,
            "get_candidate": get_candidate,
        }[name]

    if name == "CorpusBundle":
        from .index import CorpusBundle

        return CorpusBundle

    if name in {"BenchmarkQuery", "QrelEntry", "load_qrels"}:
        from .qrels import BenchmarkQuery, QrelEntry, load_qrels

        return {
            "BenchmarkQuery": BenchmarkQuery,
            "QrelEntry": QrelEntry,
            "load_qrels": load_qrels,
        }[name]

    if name in {
        "evaluate_quality",
        "evaluate_quality_thresholds",
        "evaluate_sliced_quality",
    }:
        from .scoring import (
            evaluate_quality,
            evaluate_quality_thresholds,
            evaluate_sliced_quality,
        )

        return {
            "evaluate_quality": evaluate_quality,
            "evaluate_quality_thresholds": evaluate_quality_thresholds,
            "evaluate_sliced_quality": evaluate_sliced_quality,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
