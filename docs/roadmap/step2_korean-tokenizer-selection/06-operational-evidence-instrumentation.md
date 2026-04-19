# Sub-step F: Operational-Evidence Instrumentation

## Purpose

Freeze the implementation direction for Step 2 operational evidence so memory/disk measurement can be added in one bounded follow-up substep without reopening benchmark governance or candidate-policy questions.

## Current operational-evidence gap

The Step 2 policy already requires operational evidence, but the benchmark pipeline still treats that evidence as missing.

Current repository truth:

- `src/snowiki/bench/matrix.py` records `memory_peak_rss_mb=None` and `disk_size_mb=None` for all candidates
- `src/snowiki/bench/matrix.py` marks both evidence statuses as `not_measured`
- `src/snowiki/bench/verdict.py` treats missing memory/disk evidence as a promotion blocker
- `docs/roadmap/step2_korean-tokenizer-selection/tokenizer-benchmark-proof.md` records operational status as FAIL because memory/disk are unmeasured

So the repository already knows what evidence it wants, but it does not yet collect it.

## Decision

### 1. Operational evidence must become a measured report payload, not a static matrix declaration

`matrix.py` should remain the source of candidate roster and static platform/install posture, but measured memory/disk values must enter the candidate matrix dynamically during benchmark execution.

That means the later implementation substep should not hardcode measured values into `matrix.py`.

### 2. Preferred measurement path: stdlib-first instrumentation

The narrowest preferred implementation path is:

1. use a stdlib-first memory measurement approach for the benchmark process on supported platforms
2. measure disk size from the isolated benchmark workspace after rebuild/index creation
3. inject those measurements into the candidate matrix assembly path

This is preferred because:
- it avoids premature dependency changes
- it fits current benchmark governance
- it stays aligned with the current isolated benchmark execution model

### 3. Preferred seam placement

The later implementation substep should use these seams:

- `src/snowiki/bench/phase1_latency.py`
  - best current place to add a sibling operational measurement flow or a closely related helper
- `src/snowiki/bench/baselines.py`
  - the place where measured operational evidence must be injected into `CandidateMatrixEntry`
- `src/snowiki/bench/render.py`
  - the place where human-readable benchmark output should expose the new evidence
- `benchmarks/README.md`
  - the place where the Phase 1 operational-evidence contract must be updated after instrumentation exists

### 4. What should remain static

These parts should remain static policy declarations until a later explicit decision changes them:

- candidate roster
- zero-cost admission posture
- platform/install declarations in `matrix.py`
- promotion thresholds in candidate policy docs and verdict logic

The instrumentation substep should only move memory/disk from placeholder to measured evidence.

## Rejected directions

### Reject: hardcode measured values into `matrix.py`

That would confuse static candidate policy with run-generated evidence.

### Reject: add new dependencies immediately in the planning substep

Dependency changes belong in a later implementation substep and only if stdlib-first measurement proves insufficient.

### Reject: widen benchmark scope now

This substep should not turn into a benchmark-redesign effort. It is only about making already-required memory/disk evidence measurable.

## Out-of-scope but related follow-up

Once instrumentation exists, later follow-up may still be needed to:

- improve report presentation
- decide how unknown/unsupported platforms should be represented in proof language
- determine whether additional install-burden evidence is needed beyond current static declarations

Those are not required to close this planning substep.

## Relationship to Step 2 gate state

This note does not unblock Step 2.

It only freezes how the missing operational evidence should be implemented so that a later proof run can become policy-usable.

## Acceptance criteria

- the note states that current operational evidence is placeholder-only
- the note selects dynamic report-time injection over static hardcoding
- the note chooses a stdlib-first instrumentation path
- the note identifies the exact code seams for the later implementation substep
- the note explicitly states that Step 2 remains blocked until evidence is measured and proof is rerun
