# Embedding Models + Hardware Notes

## Purpose

Capture the external model/hardware guidance that Step 4 should treat as planning input, not as already-approved implementation truth.

This note exists because Step 4 now needs a concrete answer to three separate questions:
- Which embedding family is the default multilingual target?
- What is the CPU-first fallback when the heavier model is too expensive?
- How should Snowiki describe GPU acceleration without making it mandatory?

## Main references

- FlagEmbedding / BGE family
- Sentence-Transformers multilingual models
- Qdrant hybrid/text-search docs
- OpenSearch hybrid search docs

## Extracted findings

### 1. BGE-M3 is a strong ceiling candidate, not a settled default
- BGE-M3 is one of the strongest current fits for Snowiki's mixed Korean-English planning target because it is explicitly multilingual and retrieval-oriented.
- But it should be treated as a **high-capability candidate family**, not as the already-set default, because its extra capability also brings extra architectural and operational weight.

### 2. Lighter multilingual fallbacks still matter
- Sentence-Transformers multilingual families remain useful fallback baselines when:
  - CPU-only environments cannot tolerate the heavier BGE-M3 path
  - developers need a quicker smoke-test dense setup
  - benchmark slices need a lighter control candidate
- This means Snowiki should document **one canonical target** plus **one smaller operational fallback**, not pretend one model fits every machine.

### 3. Hybrid should stay sparse+dense, not dense-only
- External hybrid-search documentation still converges on the same architectural pattern:
  - sparse retrieval
  - dense retrieval
  - fusion (RRF or normalized weighting)
  - optional rerank
- This reinforces Snowiki's lexical-first posture. Dense is additive, not a replacement.

### 4. CPU-first planning must be explicit
- CPU inference is viable but can be slow enough that lifecycle policy matters as much as raw model quality.
- Step 4 therefore must keep:
  - lazy loading
  - explicit fallback to BM25-only
  - benchmark slices that measure indexing cost separately from query cost

### 5. GPU is an acceleration tier, not a product dependency
- GPU or NPU support is worth planning because it materially changes indexing and rerank ergonomics.
- But Snowiki should describe it as an **optional acceleration mode** rather than as a required path.
- This keeps the local CLI experience honest and protects the CPU-only contract.

## Snowiki planning guidance

### Recommended model posture for Step 4 docs
1. **Open candidate set:** include at least
   - BGE-M3-class multilingual candidate
   - multilingual-e5 / GTE-class simpler dense baseline
   - Qwen3-Embedding-class higher-ceiling multilingual candidate if runtime cost is acceptable
2. **Operational fallback:** smaller multilingual baseline for constrained CPU environments and CI smoke paths
3. **Rerank posture:** small optional reranker, chunk-scoped, never a hard dependency for correctness

### Required evaluation posture
The model decision should be tied to:
- mixed Korean-English retrieval slices
- exact-match non-regression slices
- indexing latency / memory measurements
- query latency under CPU-only and optional GPU-accelerated paths

### What Snowiki should avoid
- declaring one dense model final before running mixed-language benchmark slices
- treating GPU as mandatory for a valid hybrid path
- treating dense quality as enough without sparse fallback and exact-match protection

## Concrete Step 4 implication

Step 4 should describe model policy as:
- **multilingual family required, exact model still open**
- **candidate matrix and benchmark gate required before freezing the default**
- **CPU-first correctness required, GPU acceleration optional**
