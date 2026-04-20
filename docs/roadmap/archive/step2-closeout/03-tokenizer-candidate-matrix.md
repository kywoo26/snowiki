# Sub-step C: Tokenizer Candidate Matrix

## Purpose

Freeze the candidate set and the pass/fail evaluation gates for Step 2 so tokenizer promotion is based on explicit evidence rather than narrative preference.

## Decision

Step 2 will evaluate a **closed candidate matrix**. No additional tokenizer may enter the comparison after benchmarking starts unless the matrix document itself is intentionally revised.

The initial candidate set is:

1. `regex_v1` — current runtime lexical tokenizer path
2. `kiwi_morphology_v1` — Kiwi morphology mode, corresponding to the current broad extractable-tag path
3. `kiwi_nouns_v1` — Kiwi noun-only mode
4. `lindera_ko_v1` — optional reference candidate, included only if a reproducible local install path is available without changing Step 2 scope

`lindera_ko_v1` is a **nice-to-have reference candidate**, not a gating dependency for Step 2 completion. The required promotion decision must still be made among the available closed set even if Lindera is not admitted.

## Scope

In scope:

- Freeze the candidate list and canonical names.
- Define evaluation dimensions for quality, speed, memory, platform support, and installation ergonomics.
- Define explicit thresholds for promote, keep-as-reference, or reject.

Out of scope:

- Benchmark implementation details.
- Adding Kkma, Okt, or other analyzers beyond a documented matrix revision.
- Runtime promotion before the matrix gates are satisfied.

## Candidate definitions

### `regex_v1`

The current Snowiki runtime tokenizer based on normalization, splitting, and case folding. This is the control baseline and the backward-compatibility anchor.

### `kiwi_morphology_v1`

The Kiwi-backed candidate that extracts the broader morphology token set currently represented by `morphology` mode in `src/snowiki/search/kiwi_tokenizer.py`.

### `kiwi_nouns_v1`

The Kiwi-backed candidate that extracts noun-focused tokens corresponding to the current `nouns` mode.

### `lindera_ko_v1`

An optional reference candidate for Korean lexical analysis. It may be used to sanity-check whether Kiwi is the only serious non-regex option, but it is not required for Step 2 exit.

## Evaluation dimensions

Every candidate in the matrix must be assessed on these dimensions:

1. **Quality**
   - Recall@k
   - MRR
   - nDCG@k
   - results reported overall and by `ko`, `en`, and `mixed` group slices
   - results reported separately for known-item, topical, and temporal query kinds

2. **Latency**
   - query-time p50
   - query-time p95
   - index-build time only if the candidate changes indexing cost materially

3. **Memory**
   - peak resident memory during index build
   - steady-state index size on disk when measurable

4. **Platform constraints**
   - macOS support
   - Linux x86_64 support
   - Linux aarch64 support
   - Windows support
   - whether unsupported platforms fail closed, fail open, or require fallback

5. **Install ergonomics**
   - prebuilt wheel or package availability
   - build-from-source requirements
   - hidden bootstrap steps or model downloads
   - operational complexity for local CLI users and CI

## Promotion and rejection thresholds

### Promote to runtime default

A candidate may be promoted only if all of the following are true:

- It meets or exceeds the existing benchmark quality gates overall.
- On the `mixed` slice, it beats `regex_v1` by at least:
  - `+0.03` Recall@k
  - `+0.03` MRR
  - `+0.03` nDCG@k
- It does not regress `ko` or `en` slice Recall@k by more than `0.01` against `regex_v1`.
- Its query latency p95 is no worse than `1.25x` the control candidate.
- Its memory or packaging burden does not introduce a platform exclusion for the default shipped runtime unless a documented fallback path preserves current user experience.

### Keep as benchmark-only or optional candidate

A candidate stays benchmark-only or opt-in if any of the following are true:

- It improves mixed-language quality but misses the promotion delta on one metric.
- It wins quality but exceeds the runtime latency or packaging budget for the default path.
- It is not portable enough for the default runtime but remains useful as a research reference.

### Reject

A candidate is rejected for Step 2 promotion if any of the following are true:

- It fails the overall benchmark quality gates.
- It does not materially outperform `regex_v1` on the `mixed` slice.
- It introduces unacceptable install or platform fragility without a deterministic fallback.
- Its quality result cannot be reproduced from versioned assets and pinned candidate identity.

## Comparison rules

- `mixed` is the primary decision slice.
- `ko` and `en` are non-regression guardrails, not secondary optional data.
- The control baseline is always `regex_v1`.
- Candidate ranking must be based on the frozen canonical corpus, not ad hoc supplemental queries.
- If two candidates tie within `0.01` on all quality metrics, choose the simpler operational candidate.

## Deliverables

1. A frozen candidate list with canonical names.
2. A metric matrix template covering quality, latency, memory, platform, and install ergonomics.
3. A written promote/optional/reject policy with explicit thresholds.

## Non-goals

- Do not keep adding candidates mid-stream because an upstream library looks interesting.
- Do not treat benchmark anecdotes or external blog results as promotion evidence.
- Do not promote a tokenizer because it is linguistically richer if it fails Snowiki's mixed-language retrieval gates.

## Acceptance criteria

- The candidate set is closed and names the control baseline plus the required Kiwi variants explicitly.
- Evaluation dimensions include recall@k, latency, memory, platform constraints, and install ergonomics.
- The matrix defines explicit promote versus reject thresholds, including a concrete mixed-slice improvement requirement over `regex_v1`.
- The document states how to handle candidates that help quality but are too operationally heavy for default runtime promotion.
- Step 2 can proceed to implementation and benchmarking without reopening which candidates belong in scope.
