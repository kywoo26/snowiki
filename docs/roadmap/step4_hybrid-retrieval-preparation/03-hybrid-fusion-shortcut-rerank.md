# Hybrid Fusion + Shortcut + Rerank

## Purpose

Define the exact retrieval orchestration rules for hybrid mode so fusion behavior, shortcut behavior, and optional reranking can be tested independently before runtime promotion.

## Scope

This sub-step covers:
- reciprocal rank fusion as the default merge strategy
- the strong-signal shortcut rules
- the optional rerank hook and its placement
- testability requirements for fusion and shortcut logic

## Decisions

### 1. Fusion owner

Fusion lives in a dedicated `HybridSearchService` layer rather than inside `workspace.py`.

Why:
- keeps `workspace.py` focused on index assembly
- makes fusion and shortcut logic unit-testable without building a full retrieval snapshot
- lets benchmark-only hybrid experimentation evolve without destabilizing lexical index construction

### 2. Default fusion algorithm

Use **Reciprocal Rank Fusion** as the default hybrid merge rule.

Bound parameters from the architecture memo:
- `k = 60`
- list weights: first list `1.0`, later lists `0.8`
- position bonus: rank `0 -> +0.05`, ranks `1-2 -> +0.02`
- no score normalization in the initial implementation path

Formula:

```text
rrf_score = weight * (1 / (60 + rank + 1) + position_bonus)
```

Weighted score fusion (`0.80 * vec + 0.20 * bm25`) remains an optional later ablation, not the default Step 4 path.

### 3. Shortcut rules

#### Tier-0: BM25-only shortcut

Return BM25 results immediately when:

```text
top_bm25_score >= 0.75
AND
(top_bm25_score - second_bm25_score) >= 0.10
```

#### Tier-1: fused shortcut

After BM25 and vector retrieval but before rerank, return fused results unchanged when:

```text
top_fused_score >= 0.40
AND
(top_fused_score * score_gap) >= 0.06
```

For Step 4, `score_gap` is defined as the **absolute difference** between the top fused score and the second fused score. That closes the ambiguity left open in the architecture memo and keeps the rule deterministic.

### 4. Shortcut disable conditions

The shortcut must not fire when:
- full-path benchmark evaluation is running
- explicit diagnostic controls disable shortcuts

`--mode hybrid` alone does **not** disable the shortcut. Hybrid mode should exercise the real default hybrid behavior unless evaluation or diagnostic flags request otherwise.

### 5. Optional rerank hook

- rerank runs **after fusion**
- rerank operates on the **top 20 chunks** only
- rerank is optional; if no reranker is available, fused results are returned unchanged
- rerank cache key follows the architecture memo: `sha256(model_id + "\0" + query + "\0" + chunk_content_hash)`

## Independent test contract

### Fusion tests

Fusion must be testable from synthetic ranked lists without requiring:
- a live embedder
- a vector database
- the CLI or daemon runtime

Minimum deterministic tests:
- RRF scoring respects `k=60`
- BM25 list weight `1.0` outranks equivalent lower-priority lists weighted at `0.8`
- rank-0 and rank-1/2 bonuses change ordering exactly as documented
- duplicate candidates keyed by document identity merge predictably

### Shortcut tests

Minimum deterministic tests:
- tier-0 passes when BM25 threshold and gap are both met
- tier-0 fails when either threshold is missed
- tier-1 passes when fused threshold and absolute-gap rule are both met
- tier-1 fails when a second close competitor narrows the gap
- benchmark/evaluation mode suppresses shortcut application

### Rerank tests

Minimum deterministic tests:
- only top-20 fused chunks are sent to the rerank hook
- reranker absence returns fused ordering unchanged
- rerank cache keys are stable for identical `(model_id, query, chunk_content_hash)` tuples

## Non-goals

- implementing query expansion
- selecting the final reranker model
- making weighted score fusion the default path
- changing lexical-mode behavior

## Deliverables

1. a closed fusion rule with exact RRF parameters
2. a closed shortcut policy with exact deterministic thresholds
3. a rerank placement and cache-key contract
4. a test matrix proving fusion and shortcut logic can be validated independently

## Acceptance criteria

- fusion logic is specified so it can be unit-tested independently of runtime index construction
- shortcut behavior has deterministic pass/fail tests for both tier-0 and tier-1
- the document binds the exact architecture parameters: RRF `k=60`, position bonus, shortcut thresholds, and top-20 rerank
- no architecture ambiguity remains about shortcut gap semantics or whether hybrid mode may still use shortcuts
