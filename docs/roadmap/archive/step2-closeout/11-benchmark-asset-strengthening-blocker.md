# Sub-step K: Benchmark-Asset Strengthening Blocker

## Purpose

Record the historical benchmark-asset blocker packet and explicitly mark that it is no longer the active blocker for the Mecab reopening lane.

## Historical blocker state

The reopening program once had:
- a frozen reopening contract
- a frozen family roster
- a frozen benchmark maturity bar

At that time, the benchmark assets were below that bar, and the required next move would directly modify:
- `benchmarks/queries.json`
- `benchmarks/judgments.json`

Those files are **inventory-sensitive canonical assets**.
In plain terms: benchmark assets are inventory-sensitive canonical assets.
By repository governance, they must not be modified autonomously.

So the reopening was blocked then, not because the technical direction was unclear, but because the next mandatory step required explicit approval.

## Current Mecab-lane status

That historical blocker is now cleared for the Mecab lane because the strengthened canonical benchmark assets already landed and are already the active comparison substrate.

The Mecab reopening lane therefore does **not** reopen benchmark-asset growth as its next step.

Instead, the next active blocker is the bounded Python 3.14 feasibility gate for `python-mecab-ko`.

## Historical benchmark delta that was required

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

## Historical approval surface

The minimum approval required is permission to perform one bounded benchmark-asset strengthening pass on:
- `benchmarks/queries.json`
- `benchmarks/judgments.json`

under the already-frozen maturity criteria from `10-benchmark-maturity-bar.md`.

## What happens now

For the Mecab reopening lane:
- `benchmarks/queries.json` and `benchmarks/judgments.json` remain frozen canonical assets
- no new benchmark-asset approval is required to begin the Mecab comparison
- if Mecab fails, the correct closeout is `no stable winner` or `blocked-with-artifact` for technical/dependency reasons, not renewed benchmark-asset governance

## What happens if approval is not granted

If benchmark-asset approval is not granted, the correct closeout is:
- Step 2 reopening ends as **blocked-with-artifact**
- current candidate set remains closed
- Step 2 remains benchmark-only/no runtime promotion
- Step 4 remains blocked

## Acceptance criteria

- the note explicitly preserves the historical benchmark-asset blocker
- the note defines the minimum required asset delta
- the note defines the exact historical approval surface
- the note explicitly states that benchmark-asset governance is no longer the active blocker for the Mecab lane
