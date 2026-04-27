# Analyzer Promotion Gates

## Purpose

This document defines how Snowiki evaluates Korean and mixed-language analyzer
candidates before any tokenizer can become a runtime default.

Analyzer promotion is a benchmark decision, not a library-brand decision. Kiwi,
MeCab, WordPiece, and future analyzers must improve Korean retrieval while
preserving Snowiki's English, mixed-language, path, code, CLI/tool, known-item,
and session-history retrieval behavior.

## Current candidates

The benchmark target registry exposes these comparison lanes:

- `snowiki_query_runtime_v1`
- `bm25_regex_v1`
- `bm25_kiwi_morphology_v1`
- `bm25_kiwi_nouns_v1`
- `bm25_mecab_morphology_v1`
- `bm25_hf_wordpiece_v1`

The default runtime tokenizer remains `regex_v1` until a candidate passes the
public and Snowiki-owned gates.

## Evidence layers

Promotion requires all four evidence layers:

1. **Public Korean retrieval**: `miracl_ko` at `standard` level, primarily
   `ndcg_at_10` and `recall_at_100`.
2. **Public regression checks**: English public datasets in the official matrix
   must not regress beyond the documented tolerance.
3. **Snowiki-owned slices**: Korean, English, mixed, known-item, topical,
   temporal/session-history, hard-negative, and identifier/path/code-heavy slices
   must be reported separately so aggregate gains cannot hide product-critical
   regressions.
4. **Golden query regressions**: the existing golden fixture must remain green for
   CLI/tool command, session/history, and source/provenance queries.

## Slice reporting

Benchmark queries may carry metadata:

- `group`: language or corpus group such as `ko`, `en`, or `mixed`
- `kind`: query intent such as `known-item` or `topical`
- `tags`: hard cases such as `identifier-path-code-heavy` or `hard-negative`

The benchmark runner reports slice metrics under cell details as `slices`, using
slice IDs like `group:ko`, `kind:known-item`, and
`tag:identifier-path-code-heavy`.

## Contract

The default gate contract lives at
`benchmarks/contracts/analyzer_promotion_gates.yaml`. It records the baseline,
candidate targets, required public datasets, required Snowiki-owned slices, and
numeric tolerance policy.

The contract is intentionally separate from runtime code. Passing it is a
precondition for a future runtime-default PR; it does not itself promote an
analyzer. Use `snowiki benchmark-gate --report <benchmark.json>` to evaluate an
existing benchmark report against the contract without rerunning the matrix.
Gate evaluation is intentionally strict: a public-only report may show Korean
quality gains, but it still fails promotion when Snowiki-owned slice or golden
query evidence is absent. A future Snowiki-owned benchmark matrix should produce
those required slices directly from `benchmarks/queries.json`,
`benchmarks/judgments.json`, and `fixtures/retrieval/golden_queries.json`.

## Non-goals

- Do not tune BM25 `k1`/`b` as part of analyzer promotion.
- Do not add vector retrieval, reranking, or RRF to make an analyzer pass.
- Do not promote a Korean analyzer if exact path, code, CLI/tool, session/history,
  source/provenance, or known-item retrieval regresses.
