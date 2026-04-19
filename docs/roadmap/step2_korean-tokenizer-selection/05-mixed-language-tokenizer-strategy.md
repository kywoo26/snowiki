# Sub-step E: Mixed-Language Tokenizer Strategy

## Purpose

Freeze the mixed-language lexical strategy direction for Step 2 before attempting any tokenizer redesign or fresh benchmark proof.

## Current problem statement

The current Step 2 proof is blocked not only because Kiwi failed a threshold numerically, but because the current mixed-language tokenizer design is structurally weak.

The repository now has enough evidence to say that the current architecture is unlikely to produce a legitimate runtime-promotion result without a clearer bilingual lexical strategy.

## Evidence reviewed

- `docs/roadmap/step2_korean-tokenizer-selection/tokenizer-benchmark-proof.md`
- `docs/roadmap/step2_korean-tokenizer-selection/03-tokenizer-candidate-matrix.md`
- `docs/roadmap/step2_korean-tokenizer-selection/04-gate-reconciliation-and-fresh-evidence-program.md`
- `src/snowiki/search/kiwi_tokenizer.py`
- `src/snowiki/search/tokenizer.py`
- `src/snowiki/search/bm25_index.py`
- `src/snowiki/search/registry.py`
- `tests/search/test_kiwi_tokenizer.py`
- `tests/search/test_kiwi_tokenizer_integration.py`

## Structural diagnosis

### 1. The current `BilingualTokenizer` is not actually a mixed-language tokenizer

`src/snowiki/search/kiwi_tokenizer.py` defines `BilingualTokenizer`, but the current implementation simply delegates to `KoreanTokenizer`.

That means:
- Korean morphology is handled
- English identifiers are not promoted to a first-class lexical stream
- paths, filenames, CLI flags, and code literals are not handled by a strategy specialized for mixed text

So the current bilingual surface is a naming convenience, not a true mixed-language lexical design.

### 2. The benchmark BM25 path fuses token streams naïvely

`src/snowiki/search/bm25_index.py` builds BM25 tokens by:
- taking `bm25s` token output
- then appending Kiwi tokens

This append-only fusion has three important weaknesses:
- no cross-stream coordination
- no explicit deduplication policy
- no explicit protection for English/code/path identifiers as the mixed slice’s high-signal lexical units

### 3. The current proof failure fits the code design

The proof memo shows:
- mixed delta: `+0.027778` instead of the required `+0.03`
- `en` guardrail failure for both Kiwi candidates
- `ko` guardrail failure for `kiwi_nouns_v1`

That pattern is consistent with a tokenizer path that adds Korean morphology signal without preserving English-heavy mixed-language signal well enough.

## Strategy decision

### Chosen next direction: script-aware freeze -> Korean morphology -> lexical merge

The next implementation-capable substep should pursue a **script-aware freeze/merge strategy**, not a deeper version of the current append-only fusion.

That means:

1. **Freeze non-Korean high-signal spans first**
   - paths
   - filenames
   - CLI flags
   - code-like identifiers
   - English product or tool terms

2. **Run Korean morphology only where Korean morphology is actually useful**
   - Korean prose
   - Korean compounds and inflections

3. **Merge both streams under one stable lexical policy**
   - explicit deduplication
   - stable normalization
   - no silent loss of English/code signal

### Why this direction wins

It is the narrowest strategy that addresses the current structural failures directly:
- it preserves English-heavy mixed tokens instead of hoping Kiwi tags will do it indirectly
- it keeps Korean morphology where morphology actually helps
- it gives the benchmark a plausible path to improving the `mixed` slice without sacrificing `en`

## Rejected or deferred directions

### Reject: keep the current append-only BM25 + Kiwi fusion and just retune thresholds

This would treat a structural tokenizer problem as a policy-threshold problem. The current evidence does not justify that.

### Reject: promote Kiwi directly as runtime default if it barely clears the mixed threshold later

Promotion without a real mixed-language lexical design would still leave the repository with a misleading bilingual path.

### Defer: large tokenizer-family expansion before redesign

The current candidate matrix is already closed enough for Step 2. The next evidence-generating move should improve the mixed-language lexical strategy first, not expand the candidate roster prematurely.

## Relationship to operational evidence

This strategy note does **not** resolve memory/disk instrumentation. That remains a separate required lane in the fresh-evidence program.

So Step 2 still cannot reopen on tokenizer strategy alone.

## Relationship to Step 4

This note does not unblock Step 4.

It only narrows the lexical redesign direction that Step 2 must test before Step 4 runtime implementation can be reconsidered.

## Next implementation-capable move

The next implementation-capable Step 2 substep should do one of the following:

1. build a true mixed-language tokenizer strategy seam using the freeze/merge approach
2. or prove with smaller instrumentation that this redesign path is not worth implementing

The repository should not continue with vague bilingual-tokenizer language after this point.

## Acceptance criteria

- the note explicitly states that the current bilingual path is structurally insufficient
- the note selects the freeze -> morphology -> merge direction as the next strategy to test
- the note explicitly rejects threshold-retuning as the primary answer
- the note explicitly states that Step 2 remains blocked and Step 4 remains blocked
