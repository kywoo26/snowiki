# Sub-step G: Runtime-Promotion Decision

## Purpose

Close the current Step 2 candidate set with a canonical runtime-promotion decision.

This note exists to answer the final question left after the fresh-evidence program:

> Given the current candidate set and the fresh evidence collected so far, should any tokenizer be promoted to runtime use?

## Evidence base

This decision is based on the merged Step 2 evidence program:

- `04-gate-reconciliation-and-fresh-evidence-program.md`
- `05-mixed-language-tokenizer-strategy.md`
- `06-operational-evidence-instrumentation.md`
- `tokenizer-benchmark-proof.md`
- the merged tokenizer redesign and operational-evidence implementation lanes

## Current decision

### 1. No tokenizer is promoted from the current candidate set

The current candidate set remains:
- `regex_v1` (control)
- `kiwi_morphology_v1`
- `kiwi_nouns_v1`

Decision:
- **Promoted Tokenizer**: `[NONE]`
- **Local Closeout Outcome**: `benchmark-only/no runtime promotion`

### 2. Why no promotion is justified

The evidence now shows all of the following:

1. operational evidence is measured
2. the first mixed-tokenizer redesign attempt did not improve the mixed slice enough to promote
3. the redesigned Kiwi candidates now regress the mixed slice relative to `regex_v1`
4. the redesigned Kiwi candidates still fail the `en` non-regression guardrail
5. the redesigned Kiwi candidates fail broader quality gates strongly enough to be rejected rather than kept as near-promotion candidates

So the current line cannot be described as “almost ready.”

## What this means for Step 2

### 3. There is no further mandatory residual work for the current candidate set

The current Step 2 program has done its job:
- it audited the blocker
- it measured operational evidence
- it attempted a real mixed-language redesign
- it reran the local proof
- it re-evaluated the gate

That is enough to close the line for the current candidate set.

### 4. Step 2 stays benchmark-only for now

Step 2 remains a benchmark-only result because the present candidates do not earn runtime promotion.

This is no longer because of missing instrumentation or missing follow-up paperwork.
It is because the current tokenizer candidates and the first redesign attempt do not satisfy the quality gate.

## What this means for Step 4

### 5. Step 4 remains blocked

Step 4 runtime implementation remains blocked because the sparse branch is still not proven.

Step 4 planning may exist, but Step 4 runtime work must not be treated as unblocked from the current Step 2 evidence.

## Future reopening rule

### 6. Reopen Step 2 only under a new bounded hypothesis

Any future reopening of Step 2 must come from a **new bounded evidence program**, for example:
- a different mixed-language tokenizer architecture hypothesis
- a different tokenizer family admitted through candidate-matrix governance
- a new measurement or benchmark methodology change justified by policy

What is explicitly **not** allowed:
- reopening Step 2 just because the current result is disappointing
- another unscoped retry on the same candidate set without a new hypothesis
- treating Step 4 semantic/hybrid work as a substitute for unresolved lexical proof

## Canonical closeout posture

- current candidate set: closed
- runtime promotion: none
- Step 2 status: benchmark-only / no runtime promotion
- Step 4 status: blocked
- future reopening: allowed only via a new bounded hypothesis or candidate-family program

## Acceptance criteria

- the document explicitly states that no tokenizer is promoted
- the document explicitly states that there is no further mandatory residual work for the current candidate set
- the document explicitly states that Step 4 remains blocked
- the document explicitly defines the reopening rule
