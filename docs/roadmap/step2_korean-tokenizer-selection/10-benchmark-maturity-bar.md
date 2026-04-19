# Sub-step J: Benchmark Maturity Bar

## Purpose

Freeze the minimum judged-set and evaluation maturity required before the Step 2 reopening program is allowed to compare tokenizer families meaningfully.

## Decision question

> Are the current benchmark assets mature enough for a production-confidence family comparison, and if not, what is the minimum bounded upgrade required?

## Current maturity assessment

The current benchmark harness is credible, and the strengthened benchmark assets are now mature enough for the reopened family-comparison goal.

The current strengths are:
- canonical `queries.json` / `judgments.json`
- stable `ko / en / mixed` language slices
- stable `known-item / topical / temporal` intent slices
- candidate-matrix and proof discipline already in place
- strengthened canonical 90-query asset set already landed
- explicit `retrieval` blocking gate with `core` / `full` informational context already in use

The current weaknesses are:
- the current lexical family roster is still not proven even on the strengthened substrate
- stronger benchmark maturity alone did not create a stable winner

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

### 1. Current assets now satisfy the maturity bar

The current canonical benchmark assets now meet the reopening bar for a decisive family comparison.

That means the Mecab reopening lane must run on the already-strengthened substrate rather than reopening benchmark-asset growth again.

### 2. The decisive blocking gate remains the `retrieval` preset

The decisive gate for the Mecab reopening lane is the blocking `retrieval` preset on the current 66-query slice.

The `core` and `full` presets remain useful informational context, but they do not replace the blocking `retrieval` gate.

## Governance implication

This packet does **not** modify benchmark assets by itself.

However, it now establishes that the current strengthened benchmark state is the canonical Mecab comparison substrate and that benchmark-asset growth is no longer the next blocker for this lane.

Because `benchmarks/queries.json` and `benchmarks/judgments.json` are already strengthened and canonical, the Mecab reopening lane must not reopen benchmark-asset changes unless a later separate canonical decision explicitly changes the benchmark program again.

## Stop rule

Do **not** keep expanding the benchmark once the frozen bar is reached.

If the strengthened set still fails to discriminate tokenizer families stably, that is a valid **no stable winner** signal, not a reason for endless benchmark growth.

## Acceptance criteria

- the note states that the current strengthened assets satisfy the maturity bar
- the note freezes the minimum judged-set bar numerically
- the note freezes edge-case and slice coverage requirements
- the note states that the Mecab reopening lane must use the current strengthened benchmark state without new asset growth
- the note explicitly defines `retrieval` as the blocking preset and `core` / `full` as informational
