# Embedding Candidate Matrix

## Purpose

Turn embedder selection from narrative preference into a gated candidate matrix comparable to Step 2's tokenizer matrix.

This document exists because Step 4 needs a multilingual dense path, but the skeptical audit showed that naming one family too early would silently freeze architecture around an unproven assumption.

## Scope

This sub-step covers:
- the closed candidate set for Step 4 dense retrieval evaluation
- the comparison axes and promotion thresholds
- the CPU-first and optional-GPU measurement rules
- how reranker availability influences candidate viability

Out of scope:
- final reranker selection
- model download UX implementation
- direct implementation of any embedder backend

## Candidate-set rule

Once benchmarking starts, the candidate set is closed until this document is intentionally revised.

The initial candidate matrix must include at least:
1. one **BGE-M3-class** multilingual ceiling candidate
2. one **multilingual-e5 or GTE-class** simpler dense baseline
3. one **higher-ceiling multilingual candidate** if runtime cost is acceptable (for example Qwen3-Embedding-class)
4. one **small CPU-safe fallback** candidate for smoke tests and constrained local environments

## Comparison axes

Every candidate must be scored on all of the following axes.

### 1. Retrieval quality
- mixed Korean-English retrieval slice
- Korean-only slice
- English-only slice
- exact-match / identifier-heavy non-regression slice
- semantic/paraphrase slice

### 2. Operational cost
- CPU indexing time
- CPU query latency
- warm-memory footprint
- vector-store size impact
- cold-start penalty

### 3. Runtime friction
- install complexity
- backend/runtime constraints
- quantization requirements or assumptions
- CI feasibility for smoke coverage

### 4. Ecosystem fit
- compatible reranker options
- local-first deployment fit
- alignment with Snowiki's lexical-first posture

## Promotion rule

A candidate may become the default only if it:
1. improves the mixed Korean-English slice enough to justify dense complexity
2. does not erase exact-match / identifier-heavy quality once fused with the sparse branch
3. stays within an acceptable CPU indexing and query envelope for a local CLI tool
4. has a realistic fallback or smoke-test story

If no candidate clears all four conditions, Step 4 must keep the default open and remain planning-only.

## Required benchmark outputs

The matrix must produce a durable record for each candidate including:
- recall / MRR / nDCG by slice
- p50 / p95 latency
- indexing throughput
- memory envelope
- implementation friction notes

## Coupling to other Step 4 docs

- `02-embedder-lifecycle-model-policy.md` defines lifecycle and fallback behavior, but this file decides which candidates are allowed to compete.
- `04-hybrid-evaluation-mode-plumbing.md` defines the benchmark plumbing that will run this matrix.
- `03-hybrid-fusion-shortcut-rerank.md` must consume the winner only after sparse/dense fusion has been tested against exact-match non-regression slices.

## Deliverables

1. a closed candidate set
2. an explicit comparison table template
3. promotion / reject / benchmark-only categories
4. a durable benchmark artifact contract for model selection

## Acceptance criteria

- the dense model default is not frozen outside this matrix
- the matrix is strict enough to reject all candidates if none are operationally credible
- the candidate set includes both a ceiling candidate and a simpler baseline
- the output can be cited directly in later `.sisyphus/plans/` promotion work
