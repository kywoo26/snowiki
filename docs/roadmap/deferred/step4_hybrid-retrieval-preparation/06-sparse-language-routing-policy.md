# Sparse + Language Routing Policy

## Purpose

Define how Step 4 should treat the unresolved sparse branch and language-routing problem after Step 2 closed as benchmark-only / no runtime promotion.

This document exists because hybrid retrieval quality is downstream of sparse quality. Dense retrieval cannot be allowed to hide uncertainty in Korean and mixed-language lexical behavior.

## Scope

This sub-step covers:
- how Step 2's unresolved outcome constrains Step 4
- language-slice expectations for hybrid evaluation
- sparse-branch policy for Korean, English, and mixed queries
- whether routing or tokenizer variance must remain visible during Step 4 evaluation

Out of scope:
- selecting a new tokenizer immediately
- implementing runtime language detection
- query expansion design

## Current truth carried forward from Step 2

Step 2 produced useful benchmark evidence but **did not** justify runtime promotion of a new sparse branch.

Therefore Step 4 must assume:
- the lexical shipped default remains canonical
- mixed-language sparse behavior is still a live risk surface
- dense lift must be evaluated against that risk, not around it

## Policy stance

### 1. Hybrid does not resolve sparse uncertainty by itself
Hybrid may improve semantic recall, but it must not be used to excuse regressions in exact-match or language-sensitive retrieval.

### 2. Step 4 evaluation must expose language slices explicitly
At minimum, hybrid work must report:
- Korean-only slice
- English-only slice
- mixed Korean-English slice
- identifier-heavy / exact-match slice

### 3. Sparse branch behavior must remain configurable in benchmark work
If Step 2 leaves more than one plausible sparse strategy alive, Step 4 benchmark work should keep the benchmark surface capable of comparing hybrid behavior across those sparse variants rather than assuming a single resolved tokenizer path.

### 4. Language routing is a planning question, not an implementation footnote
Snowiki still needs an explicit answer to questions like:
- do mixed-language queries use one shared sparse branch?
- do some collections or corpora justify different sparse preprocessing?
- does hybrid evaluation need tokenizer-specific ablations?

These do not all need code now, but they must be visible in planning.

## Required benchmark interaction

This policy doc requires Step 4 evaluation work to separate:
1. dense-model lift
2. sparse-branch variability
3. fusion/non-regression behavior

If those three effects are blended together in one report, the hybrid result is not trustworthy enough for promotion.

## Deliverables

1. a written rule for how Step 2's unresolved state constrains Step 4
2. required language-specific benchmark slices
3. a policy for whether sparse variants remain benchmark-visible during hybrid evaluation
4. a list of routing questions that must be closed before runtime-default discussion

## Acceptance criteria

- Step 4 no longer reads as if dense retrieval can simply paper over sparse uncertainty
- benchmark slices explicitly cover Korean, English, mixed-language, and exact-match behavior
- the document makes clear whether tokenizer/routing variance must remain visible during hybrid evaluation
