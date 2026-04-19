# Sub-step J: Benchmark Maturity Bar

## Purpose

Freeze the minimum judged-set and evaluation maturity required before the Step 2 reopening program is allowed to compare tokenizer families meaningfully.

## Decision question

> Are the current benchmark assets mature enough for a production-confidence family comparison, and if not, what is the minimum bounded upgrade required?

## Current maturity assessment

The current benchmark harness is credible, but the benchmark assets are **not yet mature enough** for the reopened family-comparison goal.

The current strengths are:
- canonical `queries.json` / `judgments.json`
- stable `ko / en / mixed` language slices
- stable `known-item / topical / temporal` intent slices
- candidate-matrix and proof discipline already in place

The current weaknesses are:
- total judged query volume is still too small for a production-confidence family decision
- ambiguous and hard-negative cases are underrepresented
- identifier/path/code-heavy golden queries are not yet guaranteed at a sufficient density
- no explicit no-answer slice policy is frozen for the reopening

## Frozen maturity bar

The reopening program requires the following minimum benchmark maturity before the final family comparison is treated as decisive:

### 1. Query volume
- target total judged queries: **90–120**
- fewer than 90 judged queries is insufficient for this reopening decision

### 2. Language × intent coverage
- preserve `ko`, `en`, `mixed`
- preserve `known-item`, `topical`, `temporal`
- require **at least 8 judged queries per language × intent cell**

### 3. Edge-case density
- require **at least 20%** of all judged queries to be tagged as one of:
  - ambiguous intent
  - hard negative
  - identifier/path/code-heavy
  - explicit no-answer

### 4. Judgment discipline
- every query must have either:
  - at least one judged relevant artifact, or
  - an explicit no-answer expectation
- pooled judgments across the compared family set are required before final scoring
- binary relevance remains sufficient for this reopening; graded judgments are deferred unless binary results prove unstable

### 5. Metric discipline
- required reporting at `top_k = 1 / 3 / 5 / 10 / 20`
- required decision metrics:
  - Recall@k
  - MRR@10
  - nDCG@10
- required slices in the final comparative proof:
  - `ko`
  - `en`
  - `mixed`
  - identifier/path/code-heavy subset
  - ambiguous/no-answer subset

## Maturity decision

### 1. Current assets are insufficient

The current benchmark assets do **not** meet the reopening bar.

That means a family comparison run performed on the current assets may still be informative, but it would not be strong enough to justify a production-confidence winner recommendation.

### 2. Benchmark-asset changes are mandatory before the decisive family comparison

Because the current assets are below the frozen bar, the reopening program requires a bounded benchmark-asset strengthening step before the decisive cross-family comparison.

## Governance implication

This packet does **not** modify benchmark assets by itself.

However, it does establish that benchmark-asset changes are mandatory for the reopening program to proceed to a decisive comparison.

Because `benchmarks/queries.json` and `benchmarks/judgments.json` are inventory-sensitive, the later benchmark-asset substep must either:
1. proceed only with the required approval/governance path, or
2. close as blocked-with-artifact if that approval is unavailable

## Stop rule

Do **not** keep expanding the benchmark once the frozen bar is reached.

If the strengthened set still fails to discriminate tokenizer families stably, that is a valid **no stable winner** signal, not a reason for endless benchmark growth.

## Acceptance criteria

- the note states that current assets are insufficient
- the note freezes the minimum judged-set bar numerically
- the note freezes edge-case and slice coverage requirements
- the note states that benchmark-asset changes are mandatory before the decisive family comparison
- the note explicitly ties that later asset work to governance constraints
