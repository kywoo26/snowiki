from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from .models import (
    CandidateOperationalEvidence,
    InstallErgonomicsEvidence,
    PlatformSupportEvidence,
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

_LINDERA_ZERO_COST_ADMISSION = False


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
    TokenizerCandidate(
        candidate_name="lindera_ko_v1",
        evidence_baseline=None,
        role="candidate",
        admission_status="admitted" if _LINDERA_ZERO_COST_ADMISSION else "not_admitted",
        control=False,
        operational_evidence=CandidateOperationalEvidence(
            memory_peak_rss_mb=None,
            memory_evidence_status="not_measured",
            disk_size_mb=None,
            disk_size_evidence_status="not_measured",
            platform_support=PlatformSupportEvidence(
                macos="unknown",
                linux_x86_64="unknown",
                linux_aarch64="unknown",
                windows="unknown",
                fallback_behavior="unknown",
            ),
            install_ergonomics=InstallErgonomicsEvidence(
                prebuilt_available=None,
                build_from_source_required=None,
                hidden_bootstrap_steps=None,
                operational_complexity="unknown",
            ),
            zero_cost_admission=_LINDERA_ZERO_COST_ADMISSION,
            admission_reason="zero_cost_local_install_unavailable",
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
