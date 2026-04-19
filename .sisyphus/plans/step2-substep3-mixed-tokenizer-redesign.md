# Step 2 Substep 3: Mixed-Language Tokenizer Redesign

## Summary

Implement the smallest real mixed-language tokenizer redesign that follows the script-aware freeze -> Korean morphology -> lexical merge direction chosen in substep 1.

## Deliverable Type

- implementation artifact

## Canonical Owner Files

- `src/snowiki/search/kiwi_tokenizer.py`
- `src/snowiki/search/registry.py`
- `src/snowiki/search/bm25_index.py`

## Supporting Files

- `tests/search/test_kiwi_tokenizer.py`
- `tests/search/test_kiwi_tokenizer_integration.py`
- `tests/search/test_bm25_index.py`
- `.sisyphus/plans/step2-substep3-mixed-tokenizer-redesign.md`

## Exact Scope

In scope:
- make `BilingualTokenizer` preserve regex-style non-Korean signal while still adding Korean morphology
- make Kiwi benchmark candidates use the bilingual tokenizer path, not the pure Korean tokenizer path
- deduplicate appended query/corpus tokens in BM25 candidate assembly
- add mixed-language unit and integration coverage

Out of scope:
- rerun benchmark proof in this substep
- change candidate roster or policy thresholds
- promote a tokenizer at runtime

## Acceptance Criteria

- `BilingualTokenizer` returns both preserved English/code/path tokens and Korean morphology on mixed input
- registry creation for `kiwi_morphology_v1` / `kiwi_nouns_v1` uses the bilingual path
- BM25 candidate index/query token assembly deduplicates appended tokens cleanly
- mixed-language tests prove English identifiers are no longer dropped
- local verification passes

## Verification Commands

- `uv run ruff check src/snowiki tests`
- `uv run ty check`
- `uv run pytest tests/search/test_kiwi_tokenizer.py tests/search/test_kiwi_tokenizer_integration.py tests/search/test_bm25_index.py`
- if fallout appears: `uv run pytest tests/search`

## Must NOT Do

- do not reopen policy thresholds
- do not change runtime default tokenizer
- do not claim the redesign is already benchmark-proven

## Completion Condition

Substep 3 is complete when the repository has a genuine mixed-language tokenizer path under benchmark candidates and tests prove that English/code/path signal is preserved rather than silently discarded.
