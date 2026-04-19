# Step 2 Substep 4: Operational-Evidence Instrumentation Implementation

## Summary

Implement the narrow stdlib-first operational evidence path defined in `06-operational-evidence-instrumentation.md` so Step 2 benchmark runs can emit policy-usable memory/disk evidence into the candidate matrix.

## Deliverable Type

- implementation artifact

## Canonical Owner Files

- `src/snowiki/bench/phase1_latency.py`
- `src/snowiki/bench/baselines.py`
- `src/snowiki/bench/render.py`
- `benchmarks/README.md`

## Supporting Files

- `src/snowiki/bench/report.py`
- `tests/bench/test_candidate_matrix.py`
- `tests/cli/test_benchmark.py`
- `tests/docs/test_step2_operational_evidence_sync.py`

## Exact Scope

In scope:
- add stdlib-first memory/disk measurement helpers for benchmark runs
- return operational measurement payload from the benchmark execution path
- inject measured values into candidate matrix entries for candidates with benchmark evidence
- render the new operational evidence in human-readable benchmark output
- update benchmark docs so memory is no longer described as a future-phase exclusion once implemented
- update or add tests so policy gates see measured evidence correctly

Out of scope:
- changing tokenizer strategy
- changing benchmark assets
- changing promotion thresholds
- adding new third-party dependencies unless blocked and explicitly revisited

## Dependencies / Blockers

- Depends on the Step 2 reconciliation and operational-evidence planning artifacts now merged on main.
- Must preserve current benchmark asset governance.
- Must not modify CLI signatures.

## Acceptance Criteria

- benchmark execution produces measured memory/disk evidence for supported candidates
- candidate matrix entries with baseline evidence no longer carry placeholder `not_measured` statuses by default
- verdict logic can see `measured` evidence without changing promotion thresholds
- human-readable benchmark output exposes the measured evidence clearly
- `benchmarks/README.md` no longer claims memory metrics are deferred to Phase 2
- local verification and CI pass

## Verification Commands

- `uv run ruff check src/snowiki tests`
- `uv run ty check`
- `uv run pytest tests/bench/test_candidate_matrix.py tests/cli/test_benchmark.py tests/docs/test_step2_operational_evidence_sync.py`
- if broader fallout appears: `uv run pytest`

## PR Surfaces

- Docs + benchmark/runtime implementation + tests

## Must NOT Do

- do not add `psutil` or similar dependencies in the first pass
- do not hardcode measured values into `matrix.py`
- do not alter `benchmarks/queries.json` or `benchmarks/judgments.json`
- do not reopen Step 2 promotion policy wording in this implementation substep

## Completion Condition

Substep 4 is complete when the benchmark pipeline emits measured memory/disk evidence into the candidate matrix and the repository’s docs/tests recognize those measurements as the new canonical operational-evidence path.
