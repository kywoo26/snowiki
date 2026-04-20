# Step 4 Substep Execution Protocol

## Purpose

Define how a Step 4 substep becomes a delegable work unit with a reviewable deliverable.

This document exists so that later work can be handed off as:
- `01`, `02`, `03`, ... `0z`
- one unit at a time
- with the expectation that the unit will be carried through **deep plan -> execution or deep research -> reviewable closeout -> PR-ready state**

## Core rule

A Step 4 substep is valid only if it produces a durable artifact that can be reviewed on its own.

That artifact may be one of three types:
1. **Implementation artifact**
   - code + tests + benchmark/report changes
2. **Research artifact**
   - deep source review + synthesized evidence note + narrowed decision surface
3. **Decision artifact**
   - ADR-style closeout, candidate matrix, threshold table, or policy record

If a substep cannot name its durable artifact, it is not ready for delegation.

## Standard substep lifecycle

Every Step 4 substep should follow this sequence.

### Phase 1 — Deep plan

Before execution starts, the substep must produce a deep plan that includes:
- exact scope
- canonical owner files
- dependencies and blockers
- verification commands
- expected deliverable type
- PR surfaces likely to change

If unresolved architecture questions remain, the substep stays in planning/research mode and does not jump straight into implementation.

### Phase 2 — Execution mode selection

A substep may run in one of three modes.

#### A. Research-first mode
Use when the substep is still primarily about source review, benchmarking design, or narrowing a decision.

Required outputs:
- updated evidence note, decision note, or matrix
- explicit keep / reject / defer conclusion
- narrowed next-step implementation surface

#### B. Decision-closeout mode
Use when the substep already has enough evidence and needs a durable policy/ADR-style closeout.

Required outputs:
- the canonical decision document
- acceptance criteria
- promotion rule for when implementation may start

#### C. Implementation mode
Use when architecture questions are already closed enough that code can land safely.

Required outputs:
- code changes
- tests
- benchmark/report updates if relevant
- doc sync for any changed normative facts

## Deliverable contract by substep type

### Implementation substep
A completed implementation substep should leave behind:
- runnable code
- passing verification commands
- synced docs/roadmap updates
- a PR-ready diff that can be reviewed independently

### Research substep
A completed research substep should leave behind:
- a durable note or matrix in `docs/roadmap/` or `docs/roadmap/external/`
- explicit decision pressure removed from later implementation work
- a clearly smaller set of open questions than before

### Decision substep
A completed decision substep should leave behind:
- one canonical decision owner
- explicit thresholds or rules
- clear downstream implementation constraints

## PR-ready closeout rule

A delegated substep is not "done" merely because exploration finished.

It is done only when it reaches one of these closeout states:
1. **PR-ready implementation state**
2. **PR-ready research/decision state** with a durable artifact that should land as docs-only or docs-heavy work
3. **blocked-with-artifact** state where the blocking condition is itself written down canonically and narrows the next unit of work

## What later delegation should look like

Future delegation should be possible in forms like:
- "Take `05-embedding-candidate-matrix` through deep plan and close it as a decision artifact."
- "Take `01-chunker-vector-schema` through deep plan and implementation if the schema questions are already closed."
- "Take `07-topology-cache-ann-mode-parity` through deep research and produce the ADR-grade closeout needed before implementation."

The important invariant is that the delegated unit owns one reviewable outcome.

## Relationship to `.sisyphus/plans/`

A Step 4 substep should be promoted into `.sisyphus/plans/` only when:
- its deliverable type is known
- the remaining open questions are small enough for atomic execution planning
- verification commands are stable
- the resulting work can be reviewed as one coherent PR or one coherent decision/docs PR

## Relationship to PR workflow

For later execution work, the expected operating rhythm is:
1. choose one numbered substep
2. create or refine the deep plan
3. execute in the correct mode (research / decision / implementation)
4. sync canonical docs and mirrors in the same change set when facts change
5. verify according to repo policy
6. produce a PR-ready result

That means a substep may legitimately end as:
- a docs-only decision PR
- a docs + benchmark artifact PR
- a code + tests + docs PR

## Non-goals

This protocol does not:
- require every substep to produce code immediately
- require every substep to be merged before the next can be researched
- replace repo-wide PR discipline or verification policy

## Practical interpretation for Step 4

The user should be able to say:
- "Do `01`"
- "Do `05`"
- "Take `07` to deep research closeout"

And the system should understand that as:
- one numbered unit
- one durable artifact
- one reviewable closeout path
- one PR-ready end state, even if the PR is research/decision only
