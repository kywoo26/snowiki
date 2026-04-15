# Embedder Lifecycle + Model Policy

## Purpose

Define the default local embedding model, lifecycle behavior, and degraded-mode policy for Step 4 hybrid retrieval.

## Scope

This sub-step covers:
- local CPU-first embedding model selection
- lazy loading and lifecycle management for CLI, MCP, and daemon usage
- model-version invalidation behavior
- deterministic fallback behavior when the model is missing or unavailable

## Model comparison

### `BAAI/bge-small-en-v1.5`

Strengths:
- smallest and safest local-CPU starting point of the three candidates
- strong English retrieval quality
- lower cold-start and memory burden for local CLI users

Weaknesses:
- English-centric; mixed Korean-English retrieval quality depends more heavily on the sparse branch
- less future-proof if Step 2 proves dense multilingual lift is essential

### `BAAI/bge-m3`

Strengths:
- best fit for Snowiki's mixed-language target among the compared options
- designed for multilingual retrieval rather than English-only retrieval
- strongest long-term alignment with a corpus that mixes Korean prose and English identifiers

Weaknesses:
- heavier local CPU footprint than `bge-small-en-v1.5`
- higher cold-start cost and stronger need for lazy loading

### `multilingual-e5`

Strengths:
- multilingual by design and viable for mixed-language retrieval
- broadly recognized retrieval family with good semantic behavior

Weaknesses:
- less aligned with the qmd / ir lineage references than the BGE family
- not the best local-CPU-first tradeoff if Snowiki wants one canonical default without expanding support surface early

## Decision

Choose **`BAAI/bge-m3` as the canonical Step 4 target model**.

Why:
- Step 4 explicitly serves a mixed Korean-English use case, not an English-only corpus.
- The architecture memo already frames multilingual performance as a real requirement rather than an optional nice-to-have.
- Choosing the multilingual-capable model now avoids designing lifecycle and schema work around an English-first default that would likely be replaced later.

Operational policy:
- `bge-m3` is the documented default model for hybrid mode.
- `bge-small-en-v1.5` remains an implementation-time escape hatch for constrained local testing, but it is **not** the roadmap default.
- `multilingual-e5` is not selected as the primary Step 4 target.

## Lifecycle policy

### 1. Lazy loading

- The embedder is loaded only when hybrid or vector mode is explicitly requested, or when a vector rebuild is explicitly invoked.
- Lexical mode must never pay model-load cost.
- The daemon may warm the embedder only after confirming the model exists locally.

### 2. Process behavior

- **CLI**: load on first hybrid/vector use within the process; unload at process exit.
- **MCP**: reuse a loaded model within the running server process when hybrid mode is requested.
- **Daemon**: keep the model warm only when hybrid mode is enabled and local resources allow it; otherwise serve BM25-only.

### 3. Version tracking

- the configured model identifier is part of vector-store freshness
- changing model family or version invalidates existing vector rows
- rebuild must fully re-embed stale content rather than mixing embeddings from different models

## Fallback policy

When the model is missing, cannot load, or fails during inference:

1. do not fail the user query
2. skip vector retrieval
3. skip fusion and rerank steps that depend on vector candidates
4. return BM25-only results
5. expose a diagnostic fallback reason such as `embedder_unavailable`

This fallback is canonical behavior, not an exceptional edge case.

## Non-goals

- implementing model download UX
- selecting GPU-first infrastructure
- adding cloud embedding APIs
- choosing a reranker model

## Deliverables

1. a closed decision naming `BAAI/bge-m3` as the Step 4 default embedding model
2. a lifecycle policy for CLI, MCP, and daemon processes
3. a model-version invalidation rule for vector freshness
4. a degraded-mode contract that falls back to BM25-only when embeddings are unavailable

## Acceptance criteria

- the chosen model is justified against the **local-CPU-first** constraint rather than abstract benchmark quality alone
- the comparison explains why `bge-m3` is preferred over `bge-small-en-v1.5` and `multilingual-e5` for Snowiki's mixed-language target
- lazy-loading behavior is concrete enough to implement without reopening lifecycle questions
- BM25-only fallback is explicitly specified for missing or unavailable models
