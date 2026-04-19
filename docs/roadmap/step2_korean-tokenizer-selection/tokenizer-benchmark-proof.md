# Tokenizer Benchmark Proof Memo

## Run Metadata

- **Commit SHA**: `7911895673d8487083cb9a43842853cbaaf69524`
- **Benchmark Presets**: `retrieval` (blocking), `core` (informational), `full` (informational)
- **Local Transient Report Paths**: `reports/step2-proof/retrieval.json`, `reports/step2-proof/core.json`, `reports/step2-proof/full.json`
- **GitHub Artifact Name**: `benchmark-retrieval-report` (blocking preset)
- **Canonical Candidate Identities**:
  - `regex_v1` (Control)
  - `kiwi_morphology_v1`
  - `kiwi_nouns_v1`

> **Note on Transient Reports**: Raw JSON artifacts under `reports/` are transient and not committed to the repository. This memo is the durable roadmap-facing record of the current local benchmark evidence after the first mixed-tokenizer redesign attempt.

## Blocking Evidence

The `retrieval` preset remains the blocking gate for Step 2.

### Mixed-Slice Delta Table

| Candidate | Recall@k | MRR | nDCG@k | Delta (vs regex_v1) | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `regex_v1` | 0.740741 | 0.722222 | 0.689731 | 0.00 | CONTROL |
| `kiwi_morphology_v1` | 0.712963 | 0.733333 | 0.685411 | Recall `-0.027778`, MRR `+0.011111`, nDCG `-0.004320` | reject |
| `kiwi_nouns_v1` | 0.712963 | 0.733333 | 0.685411 | Recall `-0.027778`, MRR `+0.011111`, nDCG `-0.004320` | reject |

### Ko/En Guardrail Table

| Candidate | Slice | Recall@k | Delta (vs regex_v1) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `kiwi_morphology_v1` | `ko` | 0.712963 | 0.000000 | PASS |
| `kiwi_morphology_v1` | `en` | 0.685185 | -0.111111 | FAIL |
| `kiwi_nouns_v1` | `ko` | 0.712963 | 0.000000 | PASS |
| `kiwi_nouns_v1` | `en` | 0.685185 | -0.111111 | FAIL |

## Informational Evidence

The `core` and `full` presets provide additional context but do not block the gate.

### Core Preset Regression Summary

The redesigned mixed tokenizer path causes both Kiwi candidates to fail the `core` preset overall MRR threshold (`0.643519 < 0.70`). This means the redesign does not merely miss promotion narrowly; it degrades a known-item-focused informational guardrail as well.

### Full Preset Regression Anatomy

The `full` preset continues to fail for both Kiwi candidates, and the redesigned path broadens the failure shape:

- `kiwi_morphology_v1` now fails overall recall (`0.675 < 0.72`) and overall nDCG (`0.641309 < 0.67`)
- `kiwi_nouns_v1` now fails overall recall (`0.675 < 0.72`), overall MRR (`0.697778 < 0.70`), overall nDCG (`0.635158 < 0.67`), and temporal recall (`0.416667 < 0.47`)

### Latency Ratio Table

| Candidate | P50 (ms) | P95 (ms) | Ratio (vs regex_v1) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `regex_v1` | 0.771994 | 1.052875 | 1.00x | CONTROL |
| `kiwi_morphology_v1` | 0.196453 | 0.415828 | 0.39x | PASS |
| `kiwi_nouns_v1` | 0.159842 | 0.340549 | 0.32x | PASS |

## Operational Evidence

- **Platform Coverage**: macOS / Linux x86_64 / Linux aarch64 supported; Windows unknown.
- **Install Ergonomics**: Prebuilt wheels available; build-from-source not required.
- **Measured Build Evidence**:
  - `regex_v1`: memory `945.390625 MB`, disk `0.052922 MB`
  - `kiwi_morphology_v1`: memory `1364.519531 MB`, disk `0.054637 MB`
  - `kiwi_nouns_v1`: memory `1323.605469 MB`, disk `0.054499 MB`
- **Operational Status**: PASS (memory and disk usage are now measured)

## GitHub Reproduction

- **Workflow Run URL**: [PENDING]
- **Parity Status**: [PENDING]
- **Reproduction Rationale**: Local evidence is refreshed on the redesigned tokenizer path. GitHub/manual parity is still required before any future gate relaxation, but current local evidence is already sufficient to keep Step 2 blocked.

> **Gate Rule**: Step 4 cannot be unblocked without both local blocking evidence and GitHub reproduction parity.

## Step 4 Gate Decision

- **Local Closeout Outcome**: benchmark-only/no runtime promotion
- **Promoted Tokenizer**: [NONE]
- **Step 4 Unblocked**: [NO]
- **Rationale**: The redesigned mixed tokenizer path does not justify promotion. Operational evidence is now measured, but both Kiwi candidates regress the mixed slice relative to `regex_v1` and fail the `en` non-regression guardrail by `-0.111111`. `kiwi_morphology_v1` and `kiwi_nouns_v1` both fail the blocking `retrieval` preset overall quality gate, and `kiwi_nouns_v1` also fails more severely on `full`. Step 2 therefore remains `benchmark-only/no runtime promotion`, and Step 4 remains blocked.

---
*This document is the durable Step 2 local proof refresh record for the benchmark evidence captured above.*
