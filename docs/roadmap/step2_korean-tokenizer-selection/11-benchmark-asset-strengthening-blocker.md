# Sub-step K: Benchmark-Asset Strengthening Blocker

## Purpose

Record the smallest blocked-with-artifact packet required to continue the Step 2 reopening program after the benchmark maturity bar has been frozen.

## Why the program is blocked

The reopening program now has:
- a frozen reopening contract
- a frozen family roster
- a frozen benchmark maturity bar

But the current benchmark assets are below that bar, and the required next move would directly modify:
- `benchmarks/queries.json`
- `benchmarks/judgments.json`

Those files are **inventory-sensitive canonical assets**.
In plain terms: benchmark assets are inventory-sensitive canonical assets.
By repository governance, they must not be modified autonomously.

So the reopening is now blocked, not because the technical direction is unclear, but because the next mandatory step requires explicit approval.

## Minimum required benchmark delta

The smallest benchmark-asset change set that would justify reopening execution is:

1. increase total judged queries from the current 60 to at least 90
2. ensure at least 8 judged queries per language × intent cell
3. add explicit tags or coverage for:
   - ambiguous intent
   - hard negatives
   - identifier/path/code-heavy cases
   - explicit no-answer cases
4. extend `judgments.json` so every new query has either relevant artifacts or an explicit no-answer expectation

## What is not required yet

The following are **not** mandatory before approval:
- graded relevance labels
- broad benchmark redesign beyond the frozen maturity bar
- family implementation work
- runtime promotion discussion

## Approval surface

The minimum approval required is permission to perform one bounded benchmark-asset strengthening pass on:
- `benchmarks/queries.json`
- `benchmarks/judgments.json`

under the already-frozen maturity criteria from `10-benchmark-maturity-bar.md`.

## What happens if approval is not granted

If benchmark-asset approval is not granted, the correct closeout is:
- Step 2 reopening ends as **blocked-with-artifact**
- current candidate set remains closed
- Step 2 remains benchmark-only/no runtime promotion
- Step 4 remains blocked

## Acceptance criteria

- the note explicitly states that the blocker is governance-sensitive benchmark asset work
- the note defines the minimum required asset delta
- the note defines the exact approval surface
- the note states the terminal blocked outcome if approval is unavailable
