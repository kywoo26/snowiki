# Tokenizer Benchmark Proof Memo

## Run Metadata

- **Commit SHA**: `1757d8edee77198fd2555bda315dc8adf2bc2678`
- **Benchmark Presets**: `retrieval` (blocking), `core` (informational), `full` (informational)
- **Local Transient Report Paths**: `reports/step2-proof/retrieval.json`, `reports/step2-proof/core.json`, `reports/step2-proof/full.json`
- **GitHub Artifact Name**: `benchmark-retrieval-report` (blocking preset)
- **Canonical Candidate Identities**:
  - `regex_v1` (Control)
  - `kiwi_morphology_v1`
  - `kiwi_nouns_v1`

> **Note on Transient Reports**: Raw JSON artifacts under `reports/` are transient and not committed to the repository. This memo serves as the durable roadmap-facing record of the benchmark results.

## Blocking Evidence

The `retrieval` preset serves as the blocking gate for Step 2.

### Mixed-Slice Delta Table

| Candidate | Recall@k | MRR | nDCG@k | Delta (vs regex_v1) | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `regex_v1` | 0.740741 | 0.722222 | 0.689731 | 0.00 | CONTROL |
| `kiwi_morphology_v1` | 0.768519 | 0.779630 | 0.725761 | +0.027778 | benchmark-only/no runtime promotion |
| `kiwi_nouns_v1` | 0.768519 | 0.779630 | 0.725761 | +0.027778 | benchmark-only/no runtime promotion |

### Ko/En Guardrail Table

| Candidate | Slice | Recall@k | Delta (vs regex_v1) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `kiwi_morphology_v1` | `ko` | 0.712963 | 0.000000 | PASS |
| `kiwi_morphology_v1` | `en` | 0.768519 | -0.027777 | FAIL |
| `kiwi_nouns_v1` | `ko` | 0.657407 | -0.055556 | FAIL |
| `kiwi_nouns_v1` | `en` | 0.768519 | -0.027777 | FAIL |

## Informational Evidence

The `core` and `full` presets provide additional context but do not block the gate.

### Full Preset Regression Anatomy

The `full` preset failed due to `kiwi_nouns_v1` overall recall (0.716667 < 0.72 threshold). This failure is localized to a specific regression case:

- **Query ID**: `ko-018`
- **Query Text**: "대용량 로그 출력이나 긴 tool_result 응답을 가진 세션을 찾아줘."
- **Gold Fixture**: `claude_large_output` (`fixtures/claude/large_output.jsonl`)
- **Regression Contrast**:
  - `kiwi_morphology_v1`: **HIT** (Correctly retrieved the large output fixture)
  - `kiwi_nouns_v1`: **MISS** (Failed to retrieve the fixture)
- **Root Cause**: The `kiwi_nouns_v1` candidate, which focuses on noun extraction, failed to capture the relevant tokens in the large tool output log, whereas the full morphology-based `kiwi_morphology_v1` succeeded.

### Latency Ratio Table

| Candidate | P50 (ms) | P95 (ms) | Ratio (vs regex_v1) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `regex_v1` | 0.771994 | 1.052875 | 1.00x | CONTROL |
| `kiwi_morphology_v1` | 0.196453 | 0.415828 | 0.39x | PASS |
| `kiwi_nouns_v1` | 0.159842 | 0.340549 | 0.32x | PASS |

## Operational Evidence

- **Platform Coverage**: macOS / Linux x86_64 / Linux aarch64 supported; Windows unknown.
- **Install Ergonomics**: Prebuilt wheels available; build-from-source not required.
- **Operational Status**: FAIL (Memory and Disk usage not measured)

## GitHub Reproduction

- **Workflow Run URL**: `https://github.com/kywoo26/snowiki/actions/runs/24583376836`
- **Parity Status**: MATCH
- **Reproduction Nuance**: The initial dispatch attempt against the local branch ref (`feat/pr-governance-templates`) failed with HTTP 422 because the branch had not yet been pushed to the remote. Parity was successfully verified by falling back to a manual dispatch against the reachable `main` remote ref.

> **Gate Rule**: Step 4 cannot be unblocked without both local blocking evidence and GitHub reproduction parity.

## Step 4 Gate Decision

- **Local Closeout Outcome**: benchmark-only/no runtime promotion
- **Promoted Tokenizer**: [NONE]
- **Step 4 Unblocked**: [NO]
- **Rationale**: No candidate reached the promotion threshold. Both Kiwi candidates failed the mixed-slice delta threshold (+0.03 required, +0.0278 achieved) and the non-regression guardrails for `en` (and `ko` for `kiwi_nouns_v1`). Additionally, operational evidence (memory/disk) remains unmeasured, which blocks promotion by policy. Step 2 local closeout outcome is benchmark-only/no runtime promotion.

---
*This document is the durable Step 2 closeout record for the benchmark evidence captured above.*
