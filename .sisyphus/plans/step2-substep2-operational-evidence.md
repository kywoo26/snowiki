# Step 2 Substep 2: Operational-Evidence Instrumentation Plan

## TL;DR

> **Summary**: Close the operational-evidence question as a decision artifact by defining the narrowest instrumentation path that can produce policy-usable memory/disk evidence for Step 2 without reopening benchmark scope or adding dependencies prematurely.
> **Deliverables**:
> - canonical operational-evidence instrumentation note
> - docs sync test that locks the note to current matrix/verdict/proof surfaces
> **Effort**: Short
> **Parallel**: YES - independent of tokenizer redesign implementation
> **Critical Path**: 1 -> 2 -> 3

## Objective

Produce a durable plan that answers:

1. What exact operational evidence is currently missing
2. Where in the benchmark pipeline it must be measured
3. What the narrowest implementation path is
4. What should explicitly remain out of scope for the instrumentation substep

## Deliverable Type

- **Primary**: decision artifact

## Canonical Owner Files

- `docs/roadmap/step2_korean-tokenizer-selection/06-operational-evidence-instrumentation.md`

## Supporting Files

- `.sisyphus/plans/step2-substep2-operational-evidence.md`
- `tests/docs/test_step2_operational_evidence_sync.py`

## Scope

In scope:
- define the exact memory/disk evidence gap
- freeze the preferred measurement approach
- define where measured values should enter the benchmark report and candidate matrix
- define what benchmark docs/presentation must change once instrumentation is implemented

Out of scope:
- implementing memory/disk measurement
- adding dependencies
- editing benchmark assets
- rerunning benchmark proof

## Acceptance Criteria

- the note states that current matrix values are placeholders, not real measured evidence
- the note defines the preferred measurement path and why
- the note identifies the exact code seams for later implementation
- the note states which parts remain deferred or require a later explicit decision
- a docs sync test locks the note against the current proof and policy surfaces

## Verification

- `uv run ruff check src/snowiki tests`
- `uv run ty check`
- `uv run pytest tests/docs/test_step2_closeout_normalization.py tests/docs/test_step2_gate_audit_sync.py tests/docs/test_step2_gate_reconciliation_sync.py tests/docs/test_step2_operational_evidence_sync.py`

## Must NOT Do

- do not add `psutil` or other new dependencies here
- do not claim operational evidence is already measured
- do not change candidate policy thresholds in this substep

## Completion Condition

Substep 2 is complete when the repo has one canonical instrumentation plan that lets a later implementation substep add memory/disk evidence without reopening policy or scope questions.
