# Step 2 Substep 7: Runtime-Promotion Decision Package

## Summary

Close the current Step 2 candidate set with a canonical decision: no tokenizer earns runtime promotion, Step 2 remains benchmark-only, and future reopening requires a new bounded hypothesis rather than more unstructured iteration.

## Deliverable Type

- decision artifact

## Canonical Owner Files

- `docs/roadmap/step2_korean-tokenizer-selection/07-runtime-promotion-decision.md`
- `docs/roadmap/STATUS.md`

## Supporting Files

- `.sisyphus/plans/step2-substep7-runtime-promotion-decision.md`
- `tests/docs/test_step2_runtime_promotion_decision_sync.py`
- existing Step 2 docs-governance tests

## Exact Scope

In scope:
- freeze the current Step 2 outcome for the present candidate set
- define whether any further Step 2 work is still mandatory
- define the exact condition for reopening Step 2 in the future
- sync status wording to the closed decision

Out of scope:
- changing benchmark evidence
- changing runtime tokenizer defaults
- GitHub/manual parity reruns
- introducing new tokenizer families in this substep

## Acceptance Criteria

- the repository has one canonical runtime-promotion decision memo
- the memo explicitly states that no tokenizer is promoted from the current candidate set
- the memo explicitly states that Step 4 remains blocked
- the memo explicitly states that future reopening requires a new bounded hypothesis or candidate family, not more open-ended retry work
- `STATUS.md` reflects that there is no further mandatory Step 2 residual work for the current candidate set

## Verification

- `uv run ruff check src/snowiki tests`
- `uv run ty check`
- `uv run pytest tests/docs/test_step2_closeout_normalization.py tests/docs/test_step2_gate_audit_sync.py tests/docs/test_step2_gate_reconciliation_sync.py tests/docs/test_step2_mixed_tokenizer_strategy_sync.py tests/docs/test_step2_operational_evidence_sync.py tests/docs/test_step2_runtime_promotion_decision_sync.py`

## Completion Condition

Substep 7 is complete when the current Step 2 line is canonically closed as benchmark-only/no runtime promotion, and the repository states exactly what would justify reopening it later.
