# Sub-step I: Candidate-Family Admission

## Purpose

Freeze the representative tokenizer-family set for the Step 2 reopening program so benchmark strengthening and later implementation work are bounded by a known comparison roster.

## Decision question

> Which tokenizer families are admitted into the reopening program, and which families are deferred or excluded from this specific run?

## Admission principles

The reopening compares **families**, not many variants of one family.

A family may be admitted only if it satisfies all of the following:
- it represents a materially different lexical strategy from the control or existing closed set
- it is relevant to Korean or mixed-language lexical retrieval for Snowiki's corpus
- it can be compared within a bounded implementation and benchmark budget
- it does not force unbounded candidate sprawl

## Frozen family set for this reopening

### 1. Control baseline — admitted
- **Family**: `regex_v1`
- **Representative**: current runtime lexical tokenizer
- **Role**: control baseline
- **Why admitted**: shipped behavior, decision anchor, and the baseline every reopening candidate must beat

### 2. Kiwi family — admitted
- **Representative**: `kiwi_morphology_v1`
- **Role**: morphology-first Korean lexical family
- **Why admitted**:
  - already deeply integrated and benchmarked
  - strongest family representative from the closed set
  - serves as the continuity baseline for whether a family-level reopening adds value beyond the prior failed line
- **What is deferred**: `kiwi_nouns_v1` is not a separate reopening representative because it already failed more strongly and does not add enough family diversity

### 3. Mecab family — admitted in principle
- **Representative target**: `python-mecab-ko` as the bounded Mecab-family representative for Korean morphology
- **Role**: alternate morphology-first family with strong external retrieval reputation
- **Why admitted**:
  - external Korean retrieval evidence suggests Mecab-like morphology remains a serious family-level baseline
  - it is the strongest contrast to Kiwi within the morphology family class
- **Special note**: implementation depends on dependency/governance feasibility. If no safe bounded path exists, this family must close as blocked-with-artifact rather than silently expanding scope.

### 4. Subword/HF family — executed in this round
- **Representative target**: `huggingface/tokenizers` represented by `BertWordPieceTokenizer` as the bounded multilingual subword representative
- **Role**: mixed-language/code-heavy comparison family
- **Why admitted**:
  - external benchmark practice suggests mixed-language and identifier-heavy corpora can favor subword-style segmentation over morphology-only strategies
  - Snowiki needs one family that is not morphology-first to test whether the mixed-language problem is fundamentally family-related
- **Execution result**:
  - merged in `#71 feat(search): add hf wordpiece benchmark comparison lane`
  - canonical tokenizer identity: `hf_wordpiece_v1`
  - benchmarkable on the blocking retrieval preset
  - final result for this round: `overall_quality_gate_failed`
- **Special note**: this is still a lexical-family comparison, not a semantic embedding experiment.

## Deferred or excluded families

### 5. Okt / social-text morphology — deferred
- **Why deferred**:
  - it is only justified if benchmark maturity work proves the corpus contains enough noisy conversational Korean to warrant a dedicated social-text family
  - adding it now would increase candidate breadth before the benchmark maturity bar is frozen

### 6. Additional Kiwi variants — excluded
- **Why excluded**:
  - the reopening is not a variant sweep of the already closed family
  - more Kiwi variants would recreate the same local search space that just failed

### 7. Character / byte / n-gram-only families — excluded for this reopening
- **Why excluded**:
  - useful for typo/OCR-heavy corpora, but not yet justified by current Snowiki benchmark slices
  - may be reconsidered only if benchmark strengthening shows that typo/noise-heavy retrieval is materially underrepresented

## External-family execution rule

This admission packet allows one bounded external-family lane to add the minimum runtime dependencies required for exactly one admitted-in-principle family representative.

That lane has now been spent on the HF/subword representative in `#71`. Any future Mecab-family execution would require a later explicit canonical reopening decision rather than silent scope broadening inside the same round.

Hard constraints still apply:
- only one family may be opened at a time
- dependency changes must remain bounded to that one family lane
- benchmark asset changes and docs/tests must still ship in the same PR sequence when relevant
- the reopening program must not silently broaden scope into multiple family integrations at once

## Current reopening roster

| Family | Representative | State | Reason |
| :--- | :--- | :--- | :--- |
| Control | `regex_v1` | admitted | required baseline |
| Kiwi | `kiwi_morphology_v1` | admitted | strongest incumbent family representative |
| Mecab | `python-mecab-ko` | admitted in principle | strong Korean morphology family baseline |
| HF / subword | `huggingface/tokenizers` (`BertWordPieceTokenizer`) | executed in this round | mixed-language/code-heavy comparison family; benchmarkable but rejected |
| Okt / social-text | TBD | deferred | only if corpus evidence justifies it |

## Acceptance criteria

- the note freezes the family-level roster clearly
- it distinguishes admitted, admitted-in-principle, deferred, and excluded families
- it explicitly prevents the reopening from turning into a variant sweep of Kiwi
- it explicitly states that only one external family may execute in a round unless a later canonical reopening expands scope
