# Sub-step D: Gate Reconciliation and Fresh-Evidence Program

## Purpose

Reconcile the current Step 2 canonical owner surfaces with repository history, then define the correct next program required to reopen the Step 2 -> Step 4 gate.

## Evidence reviewed

This reconciliation reads the current canonical roadmap owners, durable proof surfaces, runtime tokenizer code, and policy/governance tests:

- `docs/roadmap/STATUS.md`
- `docs/roadmap/main-roadmap.md`
- `docs/roadmap/step2_korean-tokenizer-selection/roadmap.md`
- `docs/roadmap/step2_korean-tokenizer-selection/analysis.md`
- `docs/roadmap/step2_korean-tokenizer-selection/03-tokenizer-candidate-matrix.md`
- `docs/roadmap/step2_korean-tokenizer-selection/tokenizer-benchmark-proof.md`
- `docs/roadmap/step4_hybrid-retrieval-preparation/roadmap.md`
- `src/snowiki/search/registry.py`
- `src/snowiki/search/workspace.py`
- `src/snowiki/search/kiwi_tokenizer.py`
- `src/snowiki/search/bm25_index.py`
- `src/snowiki/bench/matrix.py`
- `src/snowiki/bench/verdict.py`
- `tests/docs/test_step2_closeout_normalization.py`
- `tests/bench/test_candidate_matrix.py`
- `tests/governance/test_tokenizer_candidate_matrix.py`

## Reconciliation decision

### 1. The current canonical Step 2 truth is still the owner truth

The current canonical owner surfaces on `main` still say:

- **Local Closeout Outcome**: `benchmark-only/no runtime promotion`
- **Promoted Tokenizer**: `[NONE]`
- **Step 4 Unblocked**: `[NO]`
- **Current runtime default tokenizer**: `regex_v1`

Those facts are still consistent with the current proof memo, runtime registry, and governance tests.

### 2. historical PR/branch evidence does not override the current canonical owner surfaces

Repository history may contain branch-local or PR-local artifacts that describe a different Step 2 follow-up posture. If those artifacts are not present in the current canonical owner surfaces on `main`, they do **not** override the current owner truth.

For Step 2, the live owner surfaces are still:

- `docs/roadmap/STATUS.md`
- `docs/roadmap/step2_korean-tokenizer-selection/tokenizer-benchmark-proof.md`

The repository must therefore treat the current canonical files as authoritative until new evidence changes them.

### 3. Step 2 remains blocked for runtime promotion

The current proof still fails the promotion policy:

- `mixed` promotion delta requires `+0.03`; current Kiwi results are `+0.027778`
- `en` guardrail fails for both Kiwi candidates
- `ko` guardrail fails for `kiwi_nouns_v1`
- operational evidence remains incomplete because memory/disk are unmeasured

So the blocker is still real, and Step 4 runtime work remains blocked.

## Fresh-evidence program decision

### 4. The correct next work is not more closeout normalization

Step 2 no longer needs another normalization-only or stale-blocker audit pass.

If the goal is to change the gate state, the repository now needs a **fresh evidence program**, not more proof-format cleanup.

### 5. The fresh evidence program has four mandatory lanes

Any legitimate reopening of Step 2 must address all of the following:

1. **Mixed-language tokenizer strategy adequacy**
   - current bilingual handling is structurally weak
   - Korean + English identifier/path/code handling needs a real lexical strategy
2. **Operational evidence instrumentation**
   - memory and disk evidence must become policy-usable
3. **Fresh benchmark proof generation**
   - local proof must be re-run after evidence-generating changes
   - GitHub/manual reproduction must remain available when required
4. **Canonical decision sync**
   - proof, status, and Step 4 gate state must all be updated together if the evidence changes

## Current structural blockers the fresh evidence program must resolve

The fresh evidence program is not abstract benchmarking debt. The current codebase already points to two concrete structural problems:

1. **Mixed-language tokenizer handling is structurally weak**
   - `src/snowiki/search/kiwi_tokenizer.py` defines `BilingualTokenizer`, but the current implementation simply delegates to `KoreanTokenizer`.
   - English identifiers, paths, code literals, and other mixed-language tokens are therefore not handled as a first-class lexical stream.
   - `tests/search/test_kiwi_tokenizer.py` confirms the weakness: the bilingual path is only smoke-tested and currently returns no useful English tokens.

2. **Operational evidence is policy-required but not instrumented**
   - `src/snowiki/bench/matrix.py` still records memory and disk evidence as `not_measured` for the candidate set.
   - `src/snowiki/bench/verdict.py` treats missing memory/disk evidence as a promotion blocker.
   - So the benchmark/report pipeline currently lacks the instrumentation needed to produce a policy-usable promotion result.

These are the two mandatory evidence-generating lanes that matter most if Step 2 is to move beyond `benchmark-only/no runtime promotion`.

### 6. Step 4 remains blocked until this fresh evidence exists

Step 4 planning may continue, but Step 4 runtime implementation may not be treated as unblocked while Step 2 remains at `benchmark-only/no runtime promotion`.

## Canonical posture after this reconciliation

- Step 2 is still canonically closed at `benchmark-only/no runtime promotion`
- Step 2 is still blocked for runtime promotion
- Step 4 is still blocked pending a proven sparse branch
- the correct next mandatory work is a fresh Step 2 evidence program, not more closeout normalization

## Acceptance criteria

- the document states that current canonical owners remain authoritative
- the document states that history/PR artifacts do not override absent canonical owner changes
- the document states that Step 2 still fails runtime-promotion proof
- the document states that the next mandatory work is a fresh evidence program
- the document states that Step 4 remains blocked
