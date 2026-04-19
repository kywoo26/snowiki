# Step 2 Substep 1: Mixed-Language Tokenizer Strategy

## TL;DR

> **Summary**: Close the mixed-language tokenizer question as a research/decision artifact by proving that the current bilingual path is structurally insufficient and by selecting the narrowest redesign strategy that is worth implementing next.
> **Deliverables**:
> - canonical mixed-language tokenizer strategy note
> - docs sync test locking that note to the current proof and Step 2 gate state
> **Effort**: Short
> **Parallel**: YES - can proceed independently of operational-evidence instrumentation
> **Critical Path**: 1 -> 2 -> 3

## Objective

Produce a durable strategy decision that answers:

1. Why the current mixed-language tokenizer path is structurally inadequate
2. What redesign shape should be attempted next
3. What redesign ideas should be rejected or deferred

## Deliverable Type

- **Primary**: research artifact
- **Secondary**: decision artifact

## Canonical Owner Files

- `docs/roadmap/step2_korean-tokenizer-selection/05-mixed-language-tokenizer-strategy.md`

## Supporting Files

- `.sisyphus/plans/step2-substep1-mixed-tokenizer-strategy.md`
- `tests/docs/test_step2_mixed_tokenizer_strategy_sync.py`

## Scope

In scope:
- explain why `BilingualTokenizer` is not actually bilingual enough for Step 2 proof
- connect the current proof failure (+0.027778 mixed delta, en/ko guardrail failures) to the code-level tokenizer design
- freeze the recommended redesign direction for the next implementation-capable substep

Out of scope:
- changing runtime tokenizer behavior
- instrumenting memory/disk evidence
- rerunning benchmarks
- modifying benchmark assets

## Acceptance Criteria

- the new strategy note explicitly explains the structural weakness in the current bilingual path
- the note selects one recommended redesign direction and names rejected/deferred alternatives
- the note stays aligned with current proof: Step 2 remains blocked until fresh evidence exists
- a docs sync test locks the note to the current proof and gate state

## Verification

- `uv run ruff check src/snowiki tests`
- `uv run ty check`
- `uv run pytest tests/docs/test_step2_closeout_normalization.py tests/docs/test_step2_gate_reconciliation_sync.py tests/docs/test_step2_mixed_tokenizer_strategy_sync.py`

## Must NOT Do

- do not implement tokenizer redesign in this substep
- do not claim the selected strategy is already benchmark-proven
- do not reopen Step 2 gate state here

## Completion Condition

Substep 1 is complete when the repository has one canonical strategy note that narrows the tokenizer redesign enough for a later implementation substep to proceed without re-litigating the whole mixed-language problem.
