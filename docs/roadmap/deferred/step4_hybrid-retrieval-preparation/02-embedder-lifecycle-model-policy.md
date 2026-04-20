# Embedder Lifecycle + Model Policy

## Purpose

Define the **embedding-model decision process**, lifecycle behavior, and degraded-mode policy for Step 4 hybrid retrieval.

## Scope

This sub-step covers:
- local CPU-first embedding candidate selection
- lazy loading and lifecycle management for CLI, MCP, and daemon usage
- model-version invalidation behavior
- deterministic fallback behavior when the model is missing or unavailable

It does **not** assume the exact embedding family is already frozen.

## Candidate families that must stay open

### `BAAI/bge-small-en-v1.5`

Strengths:
- smallest and safest local-CPU starting point of the three original candidates
- strong English retrieval quality
- lower cold-start and memory burden for local CLI users

Weaknesses:
- English-centric; mixed Korean-English retrieval quality depends more heavily on the sparse branch
- less future-proof if Step 2 proves dense multilingual lift is essential

### `BAAI/bge-m3`

Strengths:
- strong fit for Snowiki's mixed-language target among the compared options
- designed for multilingual retrieval rather than English-only retrieval
- strongest long-term alignment with a corpus that mixes Korean prose and English identifiers

Weaknesses:
- heavier local CPU footprint than `bge-small-en-v1.5`
- higher cold-start cost and stronger need for lazy loading
- risks turning a planning preference into a de facto architecture commitment if frozen too early

### `multilingual-e5`

Strengths:
- multilingual by design and viable for mixed-language retrieval
- broadly recognized retrieval family with good semantic behavior

Weaknesses:
- less aligned with the qmd / ir lineage references than the BGE family
- still needs Snowiki-specific measurement rather than reputation-based selection

### Additional realistic candidates that must be considered

The external audit shows Step 4 should keep space for at least one additional multilingual candidate family beyond the original BGE/E5 comparison, especially:
- `Qwen3-Embedding`-class multilingual candidate for a higher-ceiling dense path
- `GTE-multilingual`-class candidate for a lighter local-first baseline

## Decision

Choose **a multilingual embedding family requirement**, not a frozen model, as the current Step 4 planning decision.

Why:
- Step 4 explicitly serves a mixed Korean-English use case, not an English-only corpus.
- The architecture memo already frames multilingual performance as a real requirement rather than an optional nice-to-have.
- But the skeptical audit also shows that freezing `BGE-M3` too early would turn a planning guess into a de facto architecture constraint before Snowiki-specific benchmark evidence exists.

Operational policy:
- the dense path must be **multilingual-capable**
- the exact default model remains **open until a candidate matrix closes**
- a smaller CPU-friendly baseline remains part of the candidate set
- the **final shipped default** is still benchmark-dependent and must be validated on Snowiki's mixed-language corpus.

## Required candidate matrix before model freeze

Before any dense model is treated as the canonical default, Step 4 must close a candidate matrix comparable in rigor to Step 2's tokenizer matrix.

At minimum, the matrix must compare:
1. one BGE-M3-class multilingual candidate
2. one multilingual-e5 or GTE-class simpler dense candidate
3. one higher-ceiling multilingual candidate if runtime cost is acceptable

Every candidate must be judged on:
- mixed Korean-English quality
- exact-match non-regression impact when used inside hybrid retrieval
- CPU indexing time
- CPU query latency
- memory footprint
- install/runtime friction
- availability of a compatible reranker path

If this matrix is not closed, this substep is still planning-only.

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
- `model_version` must eventually encode more than a display name; it should cover the compatibility identity needed to prevent mixed incompatible embeddings

### 4. CPU vs GPU posture

- **CPU-first correctness is mandatory**.
- **GPU acceleration is optional** and should speed up indexing/rerank workloads when available.
- A machine without GPU support must still be able to:
  - build lexical indexes
  - answer lexical queries
  - answer hybrid requests via BM25-only fallback when dense resources are unavailable

### 5. Separation of indexing and query costs

This substep must keep two different costs visible:
1. **vector indexing cost** (embed all chunks, persist rows)
2. **vector query cost** (encode query, retrieve candidates, optional rerank)

Snowiki should not let a good query latency number hide an impractical indexing cost on CPU-only hosts.

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

## Additional unresolved sub-axes this document must acknowledge

This substep is not only about model family. It also sits adjacent to still-open decisions about:
- embedding inference backend (PyTorch, ONNX Runtime, other local runtimes)
- quantization policy for CPU-first operation
- model distribution / caching / CI smoke strategy
- reranker family compatibility

Those may stay outside this one file, but they must not be treated as solved by naming a candidate family.

## Deliverables

1. a closed planning decision that the dense path must be **multilingual-capable**, while the exact default stays open
2. a lifecycle policy for CLI, MCP, and daemon processes
3. a model-version invalidation rule for vector freshness
4. a degraded-mode contract that falls back to BM25-only when embeddings are unavailable
5. a CPU/GPU operating policy that keeps GPU optional
6. a required candidate-matrix gate before model freeze

## Acceptance criteria

- the document does not prematurely freeze one model family before the candidate matrix is run
- the candidate set is explicit enough that implementation planning can benchmark the right families without reopening the whole problem
- lazy-loading behavior is concrete enough to implement without reopening lifecycle questions
- BM25-only fallback is explicitly specified for missing or unavailable models

## Implementation planning notes

### Primary Snowiki files likely involved later
- `src/snowiki/search/semantic_abstraction.py`
- `src/snowiki/search/workspace.py`
- `src/snowiki/daemon/warm_index.py`
- `src/snowiki/cli/commands/query.py`
- `src/snowiki/cli/commands/benchmark.py`

### Expected new runtime surfaces
- `src/snowiki/search/embedder.py`
- optional `src/snowiki/search/rerank_cache.py`

### Explicit benchmark questions this substep must answer later
1. Does the multilingual target materially help the mixed Korean-English slice?
2. What is the CPU indexing time envelope on a representative local vault?
3. Does GPU acceleration change feasibility enough to justify documenting it as a recommended tier?
4. Which smaller fallback model preserves enough quality for development and CI smoke tests?
5. Does a BGE-M3-class candidate earn its extra complexity over simpler multilingual dense baselines?
