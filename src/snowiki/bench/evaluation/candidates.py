from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from snowiki.search import BM25SearchIndex

from ..contract.presets import candidate_name_for_benchmark_baseline
from ..reporting.models import (
    BaselineResult,
    CandidateMatrixEntry,
    CandidateMatrixReport,
    CandidateOperationalEvidence,
    InstallErgonomicsEvidence,
    PlatformSupportEvidence,
)
from ..runtime.operational import (
    measure_bm25_candidate_build,
    measure_regex_candidate_build,
)

type CandidateRole = Literal["control", "candidate"]
type AdmissionStatus = Literal["admitted", "not_admitted"]


class TokenizerCandidate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    candidate_name: str
    evidence_baseline: str | None
    role: CandidateRole
    admission_status: AdmissionStatus
    control: bool
    operational_evidence: CandidateOperationalEvidence


_SUPPORTED_PLATFORM_SET = PlatformSupportEvidence(
    macos="supported",
    linux_x86_64="supported",
    linux_aarch64="supported",
    windows="supported",
    fallback_behavior="none",
)

_KIWI_PLATFORM_SET = PlatformSupportEvidence(
    macos="supported",
    linux_x86_64="supported",
    linux_aarch64="supported",
    windows="unknown",
    fallback_behavior="unknown",
)

_MECAB_PLATFORM_SET = PlatformSupportEvidence(
    macos="unknown",
    linux_x86_64="supported",
    linux_aarch64="unknown",
    windows="unknown",
    fallback_behavior="unknown",
)


CANDIDATE_MATRIX: tuple[TokenizerCandidate, ...] = (
    TokenizerCandidate(
        candidate_name="regex_v1",
        evidence_baseline="lexical",
        role="control",
        admission_status="admitted",
        control=True,
        operational_evidence=CandidateOperationalEvidence(
            memory_peak_rss_mb=None,
            memory_evidence_status="not_measured",
            disk_size_mb=None,
            disk_size_evidence_status="not_measured",
            platform_support=_SUPPORTED_PLATFORM_SET,
            install_ergonomics=InstallErgonomicsEvidence(
                prebuilt_available=True,
                build_from_source_required=False,
                hidden_bootstrap_steps=False,
                operational_complexity="low",
            ),
            zero_cost_admission=True,
            admission_reason="current_runtime_default",
        ),
    ),
    TokenizerCandidate(
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
        role="candidate",
        admission_status="admitted",
        control=False,
        operational_evidence=CandidateOperationalEvidence(
            memory_peak_rss_mb=None,
            memory_evidence_status="not_measured",
            disk_size_mb=None,
            disk_size_evidence_status="not_measured",
            platform_support=_KIWI_PLATFORM_SET,
            install_ergonomics=InstallErgonomicsEvidence(
                prebuilt_available=True,
                build_from_source_required=False,
                hidden_bootstrap_steps=False,
                operational_complexity="medium",
            ),
            zero_cost_admission=True,
            admission_reason="admitted_kiwi_candidate",
        ),
    ),
    TokenizerCandidate(
        candidate_name="kiwi_nouns_v1",
        evidence_baseline="bm25s_kiwi_nouns",
        role="candidate",
        admission_status="admitted",
        control=False,
        operational_evidence=CandidateOperationalEvidence(
            memory_peak_rss_mb=None,
            memory_evidence_status="not_measured",
            disk_size_mb=None,
            disk_size_evidence_status="not_measured",
            platform_support=_KIWI_PLATFORM_SET,
            install_ergonomics=InstallErgonomicsEvidence(
                prebuilt_available=True,
                build_from_source_required=False,
                hidden_bootstrap_steps=False,
                operational_complexity="medium",
            ),
            zero_cost_admission=True,
            admission_reason="admitted_kiwi_candidate",
        ),
    ),
    TokenizerCandidate(
        candidate_name="mecab_morphology_v1",
        evidence_baseline="bm25s_mecab_full",
        role="candidate",
        admission_status="admitted",
        control=False,
        operational_evidence=CandidateOperationalEvidence(
            memory_peak_rss_mb=None,
            memory_evidence_status="not_measured",
            disk_size_mb=None,
            disk_size_evidence_status="not_measured",
            platform_support=_MECAB_PLATFORM_SET,
            install_ergonomics=InstallErgonomicsEvidence(
                prebuilt_available=True,
                build_from_source_required=False,
                hidden_bootstrap_steps=False,
                operational_complexity="medium",
            ),
            zero_cost_admission=True,
            admission_reason="admitted_mecab_candidate",
        ),
    ),
    TokenizerCandidate(
        candidate_name="hf_wordpiece_v1",
        evidence_baseline="bm25s_hf_wordpiece",
        role="candidate",
        admission_status="admitted",
        control=False,
        operational_evidence=CandidateOperationalEvidence(
            memory_peak_rss_mb=None,
            memory_evidence_status="not_measured",
            disk_size_mb=None,
            disk_size_evidence_status="not_measured",
            platform_support=_SUPPORTED_PLATFORM_SET,
            install_ergonomics=InstallErgonomicsEvidence(
                prebuilt_available=True,
                build_from_source_required=False,
                hidden_bootstrap_steps=False,
                operational_complexity="medium",
            ),
            zero_cost_admission=True,
            admission_reason="admitted_subword_candidate",
        ),
    ),
)


def get_candidate(name: str) -> TokenizerCandidate:
    for candidate in CANDIDATE_MATRIX:
        if candidate.candidate_name == name:
            return candidate
    raise KeyError(f"Unknown candidate: {name}")


def admitted_candidates() -> tuple[TokenizerCandidate, ...]:
    return tuple(c for c in CANDIDATE_MATRIX if c.admission_status == "admitted")


def _with_measured_operational_evidence(
    candidate_name: str,
    *,
    memory_peak_rss_mb: float | None,
    disk_size_mb: float,
) -> CandidateOperationalEvidence:
    candidate = get_candidate(candidate_name)
    base = candidate.operational_evidence
    return base.model_copy(
        update={
            "memory_peak_rss_mb": memory_peak_rss_mb,
            "memory_evidence_status": (
                "measured" if memory_peak_rss_mb is not None else "not_measured"
            ),
            "disk_size_mb": disk_size_mb,
            "disk_size_evidence_status": "measured",
        }
    )


def measure_operational_evidence(
    *,
    records: list[dict[str, object]],
    bm25_indexes: Mapping[str, object],
) -> dict[str, CandidateOperationalEvidence]:
    evidence: dict[str, CandidateOperationalEvidence] = {}
    regex_peak_rss_mb, regex_disk_size_mb = measure_regex_candidate_build(
        records=records
    )
    evidence["regex_v1"] = _with_measured_operational_evidence(
        "regex_v1",
        memory_peak_rss_mb=regex_peak_rss_mb,
        disk_size_mb=regex_disk_size_mb,
    )

    for tokenizer_name, bm25_index in bm25_indexes.items():
        if not isinstance(bm25_index, BM25SearchIndex):
            continue
        peak_rss_mb, disk_size_mb = measure_bm25_candidate_build(
            documents=bm25_index.documents,
            tokenizer_name=tokenizer_name,
        )
        evidence[tokenizer_name] = _with_measured_operational_evidence(
            tokenizer_name,
            memory_peak_rss_mb=peak_rss_mb,
            disk_size_mb=disk_size_mb,
        )
    return evidence


def assemble_candidate_matrix(
    baseline_results: Mapping[str, BaselineResult],
    *,
    operational_evidence: Mapping[str, CandidateOperationalEvidence] | None = None,
) -> CandidateMatrixReport:
    candidates: list[CandidateMatrixEntry] = []
    evidence_map = operational_evidence or {}

    for evidence_baseline, baseline_result in baseline_results.items():
        candidate = get_candidate(
            candidate_name_for_benchmark_baseline(evidence_baseline)
        )
        candidates.append(
            CandidateMatrixEntry(
                candidate_name=candidate.candidate_name,
                evidence_baseline=evidence_baseline,
                role=candidate.role,
                admission_status=candidate.admission_status,
                control=candidate.control,
                operational_evidence=evidence_map.get(
                    candidate.candidate_name, candidate.operational_evidence
                ),
                baseline=baseline_result,
            )
        )

    return CandidateMatrixReport(candidates=candidates)


__all__ = [
    "CANDIDATE_MATRIX",
    "TokenizerCandidate",
    "admitted_candidates",
    "assemble_candidate_matrix",
    "get_candidate",
    "measure_operational_evidence",
]
