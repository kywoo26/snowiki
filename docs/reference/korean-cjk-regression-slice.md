# Korean and CJK Regression Slice

## Phase 3 scope summary

This slice covers the Phase 3 Korean and CJK regression evidence used to audit Snowiki-owned retrieval qrels. The scope is conservative: only queries with exact supporting evidence in the regression corpus or cited source files are eligible.

## Conservative qrels

Conservative qrels means a positive label is allowed only when the cited document has an exact excerpt in `benchmarks/regression/snowiki_retrieval/regression/corpus.json` or in the referenced source file. No paraphrase-only evidence counts. No inferred relevance counts. No synthetic-only benchmark promotion is allowed.

## Required tag list

- `ko-spacing`
- `ko-inflection`
- `cjk-mixed-code`
- `identifier-path-code-heavy`
- `long-natural-question`

## Underpowered policy

If any required tag has fewer than 2 queries, mark the slice `UNDERPOWERED` and block bakeoff.

## Promotion policy

- No synthetic-only benchmark promotion.
- No model bakeoff until qrels quality is sufficient.
- The evidence set must stay reviewable and source-backed before any promotion discussion.

## Notes

This slice is a reporting contract for regression evidence, not a runtime behavior change.
