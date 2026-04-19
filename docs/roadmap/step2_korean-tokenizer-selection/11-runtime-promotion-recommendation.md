# Sub-step L: Runtime-Promotion Recommendation

## Purpose

Record the current recommendation after the strengthened current-roster proof rerun and the bounded external-family comparison lane.

## Current rerun outcome

### 1. Current rerun outcome: no stable winner in the strengthened current roster

The strengthened 90-query judged set does **not** produce a stable winner among the current roster:
- `regex_v1`
- `kiwi_morphology_v1`
- `kiwi_nouns_v1`

This is not yet the final closeout of every possible future Step 2 attempt.
It is the conclusive result for the **current roster on the strengthened benchmark**.

## Recommendation

### 2. No runtime-promotion recommendation is issued from this checkpoint

No runtime-promotion recommendation is issued from this reopening cycle.

### 3. The current candidate set remains canonically closed

The prior Step 2 closeout still stands:
- `benchmark-only / no runtime promotion`
- promoted tokenizer: `NONE`
- Step 4 remains blocked

## External-family lane result

### 4. The bounded HF/subword external-family lane is now complete

The bounded external-family comparison lane has been executed with the admitted-in-principle HF/subword representative:

- chosen family: `huggingface/tokenizers` / WordPiece
- canonical tokenizer identity: `hf_wordpiece_v1`
- merged implementation PR: `#71`
- result: benchmarkable, but `overall_quality_gate_failed`

That means:
- no more Kiwi variant churn
- no more benchmark growth beyond the maturity bar
- one external family only **was used in this round**
- no runtime promotion in that lane
- no second family lane opens implicitly from this result

### 5. Mecab remains admitted in principle, not active in this round

Mecab is still part of the frozen admission packet as an **admitted-in-principle** family, but it is **not** part of the current execution round anymore because the one-family external lane budget was already spent on HF/subword.

If Mecab is ever reopened, that must happen through a later explicit canonical decision rather than by silently broadening this substep.

## Step 4 implication

### 6. Step 4 remains blocked

Because the sparse branch is still not proven and the strengthened current roster has no stable winner, Step 4 runtime work remains blocked.

## Next bounded lane

### 7. The correct next move is Substep 5 final comparative proof/recommendation

The next canonical move is to close the final comparative proof package for the HF result and determine whether Step 2 now terminates as **no stable winner** or explicitly reopens Substep 3 under evidence.

## Acceptance criteria

- the note explicitly states that the strengthened current roster has no stable winner
- the note explicitly states that no runtime-promotion recommendation is issued
- the note explicitly preserves the existing Step 2 benchmark-only closeout
- the note explicitly records the bounded HF/subword lane result
- the note explicitly names Substep 5 as the next canonical move
