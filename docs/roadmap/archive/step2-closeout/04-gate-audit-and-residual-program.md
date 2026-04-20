# Sub-step D: Gate Audit and Residual Program Decision

## Purpose

Audit whether the current Step 2 blocker is stale or still legitimate, then decide whether any mandatory residual Step 2 closeout work remains before the Step 2 -> Step 4 gate can be considered settled.

## Evidence reviewed

This audit reads the canonical Step 2 proof, candidate-matrix policy, registry/runtime surfaces, benchmark report contract, and governance tests:

- `docs/roadmap/STATUS.md`
- `docs/roadmap/main-roadmap.md`
- `docs/roadmap/step2_korean-tokenizer-selection/tokenizer-benchmark-proof.md`
- `docs/roadmap/step2_korean-tokenizer-selection/02-tokenizer-abstraction-registry.md`
- `docs/roadmap/step2_korean-tokenizer-selection/03-tokenizer-candidate-matrix.md`
- `src/snowiki/search/registry.py`
- `src/snowiki/search/workspace.py`
- `src/snowiki/search/bm25_index.py`
- `src/snowiki/bench/contract.py`
- `src/snowiki/bench/report.py`
- `src/snowiki/bench/verdict.py`
- `src/snowiki/bench/matrix.py`
- `tests/docs/test_step2_closeout_normalization.py`
- `tests/governance/test_tokenizer_candidate_matrix.py`
- `tests/bench/test_candidate_matrix.py`
- `tests/bench/test_retrieval_benchmarks_integration.py`
- `tests/search/test_tokenizer_registry.py`

## Gate-audit decision

### 1. The current Step 2 blocker is legitimate, not stale

The blocker remains valid because the current proof still fails the promotion policy encoded in the canonical owners:

- `mixed` is the promotion slice and requires `+0.03` improvement over `regex_v1` on Recall@k, MRR, and nDCG@k.
- `ko` and `en` are non-regression guardrails and may not regress Recall@k by more than `0.01`.
- promotion requires usable operational evidence; memory and disk evidence must be measured.

The durable proof memo records that both Kiwi candidates missed the `mixed` promotion delta (`+0.027778`, not `+0.03`), both regressed the `en` guardrail, `kiwi_nouns_v1` regressed the `ko` guardrail, and operational evidence remains incomplete.

### 2. Step 2 is already legitimately closed locally

The current official truth is the correct Step 2 local closeout state:

- **Local Closeout Outcome**: `benchmark-only/no runtime promotion`
- **Promoted Tokenizer**: `[NONE]`
- **Step 4 Unblocked**: `[NO]`
- **Current runtime default tokenizer**: `regex_v1`
- **Kiwi runtime policy**: benchmark-supported only, not runtime-supported

This means Step 2 does **not** require another mandatory closeout sub-program just to reaffirm the same decision. The benchmark proof already supports the current closeout, and the governance tests already defend the key invariants.

### 3. Step 4 remains blocked

Step 4 stays blocked because Step 4 depends on a **proven sparse branch**, not merely a finished benchmark memo. The proof memo is explicit: Step 4 cannot be unblocked without both local blocking evidence and GitHub reproduction parity. GitHub parity exists, but the local blocking evidence still resolves to `benchmark-only/no runtime promotion`, so the Step 4 gate remains closed.

## Residual-program decision

### Mandatory residual Step 2 work

There is **no additional mandatory Step 2 residual substep** required to make the current closeout legitimate.

The only required action from this audit is to keep the canonical surfaces synchronized so they no longer imply that more Step 2 closeout work is inherently pending.

### Optional future work that would reopen Step 2

Step 2 should be reopened only as a **new evidence program**, not as continuing closeout work, if and only if fresh evidence is intentionally collected that could change the gate state. That future re-open path would need to satisfy the same candidate-matrix and proof rules, including:

1. refreshed benchmark evidence on the frozen candidate set or an intentionally revised matrix
2. `mixed` slice delta meeting or exceeding `+0.03`
3. `ko` and `en` non-regression guardrails passing
4. measured memory and disk evidence
5. runtime-promotion evidence that justifies changing the shipped default away from `regex_v1`

Until that happens, Step 2 should be treated as canonically closed at `benchmark-only/no runtime promotion`.

## Canonical posture after this audit

- Step 2 local closeout remains `benchmark-only/no runtime promotion`.
- Step 2 does **not** have a stale blocker; it has a legitimate no-promotion decision.
- Step 4 remains blocked because the sparse branch is still not proven.
- Further Step 2 work is optional reopening, not mandatory closeout debt.

## Acceptance criteria

- The audit leaves no ambiguity about whether the blocker is stale.
- The audit states whether Step 2 is closed, blocked, or reopened.
- The audit states whether Step 4 remains blocked.
- The audit distinguishes mandatory residual work from optional future reopening.
