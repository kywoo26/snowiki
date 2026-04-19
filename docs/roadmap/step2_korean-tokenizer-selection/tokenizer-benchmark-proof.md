# Tokenizer Benchmark Proof Memo

## Run Metadata

- **Current Main SHA after Substep 4 closeout**: `139ce3567f4eaa8dc7d404421832c283d677d843`
- **Substep 4 implementation merge SHA**: `27c54dfd3859d427dc9487e5f0ca2a95407df408`
- **Benchmark Preset for the external-family lane**: `retrieval` (blocking)
- **Local Transient Report Path**: `reports/retrieval.json`
- **Merged Implementation PR**: `#71 feat(search): add hf wordpiece benchmark comparison lane`
- **Canonical Candidate Identities**:
  - `regex_v1` (Control)
  - `kiwi_morphology_v1`
  - `kiwi_nouns_v1`
  - `hf_wordpiece_v1`

> **Note on Transient Reports**: Raw JSON artifacts under `reports/` are transient and not committed to the repository. This memo is the durable roadmap-facing record for the merged HF/subword external-family comparison on top of the strengthened 90-query judged set.

## Blocking Evidence

The `retrieval` preset remains the blocking gate for Step 2.

### Strengthened current-roster result

The strengthened current-roster result does **not** produce a stable winner among the current roster.

No stable winner in the strengthened current roster.

Current rerun result on the 66-query blocking `retrieval` slice:

| Candidate | Recall@k | MRR | nDCG@k | Result |
| :--- | :--- | :--- | :--- | :--- |
| `regex_v1` | 0.712121 | 0.713384 | 0.677320 | reject |
| `kiwi_morphology_v1` | 0.666667 | 0.672222 | 0.628733 | reject |
| `kiwi_nouns_v1` | 0.666667 | 0.664646 | 0.623141 | reject |

### Ko/En/Mixed interpretation

- The stronger judged set confirms that the current roster is not merely “close.”
- `regex_v1` itself now fails the blocking overall recall threshold on the strengthened set.
- Both Kiwi candidates still fail more strongly than the control baseline on the blocking retrieval slice.
- The current roster therefore does not justify a runtime-promotion recommendation.

## Informational Evidence

The `core` and `full` presets provide additional context but do not block the gate.

### Core preset summary

The 42-query `core` preset still favors the control baseline and rejects both Kiwi candidates because their MRR remains below the frozen threshold.

### Full preset summary

The 90-query `full` preset also rejects the entire current roster under the strengthened substrate.

This is useful, not catastrophic: it means the stronger benchmark is doing its job by exposing that the current lexical family set is still not production-credible.

No stable winner in the strengthened current roster.

### Latency / operational evidence

Operational evidence remains measured and acceptable.

Representative retrieval run operational evidence:
- `regex_v1`: memory `945.757812 MB`, disk `0.049595 MB`
- `kiwi_morphology_v1`: memory `1363.722656 MB`, disk `0.05131 MB`
- `kiwi_nouns_v1`: memory `1323.261719 MB`, disk `0.051171 MB`
- **Operational Status**: PASS (memory and disk usage are now measured)

## Current recommendation

### Local closeout for the current roster

- **Local Closeout Outcome**: no stable winner in the strengthened current roster
- **Promoted Tokenizer**: [NONE]
- **Step 4 Unblocked**: [NO]

### Why this is the correct interpretation

The strengthened benchmark no longer supports the idea that the current roster is near promotion.

Instead, it shows that:
- the benchmark substrate is now stricter and more credible
- the current roster is exhausted on that stronger substrate
- another bounded lane is required if Step 2 is to move forward

## Substep 4 external-family result

The bounded external-family comparison lane has now been executed with the admitted-in-principle **HF/subword** representative.

- **Chosen family**: HF / subword via `huggingface/tokenizers`
- **Representative**: `hf_wordpiece_v1`
- **PR**: `#71 feat(search): add hf wordpiece benchmark comparison lane`
- **Artifact type**: implementation artifact
- **Benchmarkability**: PASS — the family integrates cleanly and runs on the blocking `retrieval` preset
- **Quality result**: REJECT — `overall_quality_gate_failed`

Representative blocking retrieval result on the 66-query slice:

| Candidate | Recall@k | MRR | nDCG@k | Result |
| :--- | :--- | :--- | :--- | :--- |
| `hf_wordpiece_v1` | 0.684343 | 0.641414 | 0.626323 | reject |

Interpretation:
- the external-family budget for this round has been spent on one admitted-in-principle family
- the lane succeeded as a bounded implementation/benchmark comparison
- the result still does not produce a stable lexical winner
- this does **not** justify silently opening Mecab in the same round

## Step 4 implication

Step 4 remains blocked.

The sparse branch is still not proven, and the stronger benchmark makes that conclusion more credible rather than less.

## Subsequent Mecab reopening result

The later bounded Mecab reopening attempt did **not** reach implementation or benchmark execution.

- **Representative target**: `python-mecab-ko`
- **Artifact**: `12-mecab-feasibility-blocker.md`
- **Outcome**: `blocked-with-artifact`
- **Blocking reason**: Python 3.14 bounded install failed because `python-mecab-ko` fell into a native build path and errored on `mecab-config not found`

That means:
- HF/subword is the only executed external-family comparison lane in the finished comparison chain
- Mecab did not consume a benchmark run because it failed before bounded implementation could begin
- no further Mecab implementation work remains in this round

## Current Step 2 closeout posture

The current external-family outcomes are now fully known:

- HF/subword: benchmarkable but rejected
- Mecab: blocked-with-artifact at the bounded Python 3.14 feasibility gate

The remaining overall Step 2 closeout question is whether to terminate the broader program as `no stable winner` or explicitly reopen Substep 3 under new evidence. The Mecab reopening program itself is closed.

## Step 4 Gate Decision

- **Local Closeout Outcome**: benchmark-only/no runtime promotion
- **Promoted Tokenizer**: [NONE]
- **Step 4 Unblocked**: [NO]
- **Rationale**: The strengthened benchmark substrate showed no stable winner in the current lexical roster; HF/subword was benchmarkable but rejected; and the later Mecab reopening attempt closed as blocked-with-artifact before implementation. Step 2 therefore remains benchmark-only/no runtime promotion and Step 4 remains blocked.

---
*This document is the durable strengthened-current-roster proof record for the lexical productionization program.*
