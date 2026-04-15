# Hybrid Evaluation Plan

## Purpose

This document defines the evidence Snowiki needs before the hybrid retrieval path can move from roadmap target to implementation promotion and, later, to runtime default consideration.

It is the evaluation companion to `hybrid-architecture.md`.

---

## 1. Evaluation principle

Hybrid retrieval must prove two things at the same time:

1. It improves semantically difficult retrieval.
2. It does **not** damage exact-match, known-item, or provenance-trust behavior.

The evaluation framework therefore needs both **quality-lift slices** and **safety/regression slices**.

---

## 2. Required benchmark slices

### A. Exact-match / known-item slice

Goal: prove hybrid does not degrade the cases where lexical search is already strong.

Query types:
- exact page titles
- file paths
- entity/tool names
- code/library identifiers
- date/session known-item queries

Primary metrics:
- top-1 accuracy
- recall@5
- shortcut coverage

### B. Paraphrase / semantic slice

Goal: prove hybrid adds real value on semantically related queries that lexical alone underserves.

Query types:
- paraphrased concepts
- indirect descriptions
- "what was the discussion about X"-style reformulations
- mixed wording where the answer page does not share the dominant lexical surface

Primary metrics:
- recall@5
- MRR@10
- nDCG@10

### C. Mixed-language slice

Goal: prove the sparse and dense branches cooperate on Korean-English mixed corpora.

Query types:
- Korean prose mentioning English library names
- English identifiers embedded in Korean notes
- mixed query language vs mixed page language

Primary metrics:
- recall@5
- top-1 accuracy
- failure-case notes by tokenizer policy

### D. Fallback / degraded-mode slice

Goal: prove the system remains correct when vector or rerank components are unavailable.

Conditions:
- embedder unavailable
- vector store stale or absent
- reranker unavailable

Primary metrics:
- successful query completion rate
- lexical-equivalent recall@5
- diagnostic field correctness

---

## 3. Variants to compare

Minimum comparison set:

1. **Lexical baseline**
2. **BM25-only runtime candidate**
3. **Hybrid (RRF only)**
4. **Hybrid + shortcut**
5. **Hybrid + rerank**

Deferred until later:
- query expansion variants
- alternative weighted score fusion variants

Expansion stays out of the initial evaluation matrix because the architecture memo already defers it until reranker evidence is strong.

---

## 4. Required ablations

To avoid treating hybrid as a single opaque win/loss number, Snowiki should run these ablations:

1. **Shortcut on vs off**
2. **RRF with vs without position bonus**
3. **Diversity cap on vs off**
4. **Rerank on vs off**
5. **Different tokenizer backends for mixed-language corpora**

These ablations matter because Step 2 and Step 4 are coupled: sparse quality determines how much hybrid helps and how often the shortcut safely triggers.

---

## 5. Promotion gates

Hybrid can be promoted to an execution-ready implementation plan only when all of the following are met:

1. **Semantic recall lift**
   - recall@5 improves by **at least +10%** on the semantic/paraphrase slice relative to lexical baseline.

2. **Exact-match preservation**
   - top-1 accuracy on exact-match / known-item queries does not regress by more than **2%**.

3. **Latency envelope**
   - p95 hybrid latency is at most **2×** the lexical baseline on a representative local corpus.

4. **Shortcut usefulness**
   - shortcut triggers on at least **30%** of mixed benchmark queries without harming exact-match safety.

5. **Fallback correctness**
   - degraded-mode queries complete successfully and match lexical-only behavior when vector/rerank layers are unavailable.

6. **Provenance integrity**
   - every final hit preserves `doc_path` plus chunk/section provenance fields when hybrid is active.

---

## 6. Evaluation artifacts to save

Each hybrid benchmark run should produce:

1. machine-readable metrics report
2. slice-by-slice confusion/failure summary
3. shortcut hit-rate report
4. latency distribution summary
5. fallback behavior report

Recommended location:
- `reports/retrieval/*.json`
- summarized into `docs/roadmap/step4_hybrid-retrieval-preparation/`

---

## 7. Test requirements before implementation promotion

The following tests should exist before Step 4 becomes execution-ready:

1. `tests/search/test_semantic_abstraction.py`
   - seam/contract tests for enabling or disabling semantic components

2. integration tests for embedder-disabled fallback
   - hybrid mode should degrade to lexical-only cleanly

3. governance tests for diagnostic fields
   - verify `fallback_reason`, `shortcut_applied`, `shortcut_tier`, and mode reporting

4. mixed-language benchmark harness coverage
   - ensure Step 2 tokenizer decisions are tested inside Step 4 evaluation slices

---

## 8. Non-goals of this evaluation plan

- Do not use a single aggregate score as the only decision input.
- Do not treat benchmark wins as automatic runtime-default permission.
- Do not blur runtime and benchmark surfaces.
- Do not treat vector availability as guaranteed.

---

## Bottom line

Snowiki should promote hybrid retrieval only when the benchmark evidence proves it is:

- materially better on hard semantic queries,
- safe on lexical/known-item queries,
- fast enough for local use,
- and trustworthy under fallback conditions.

Anything less remains research, not roadmap-ready implementation.
