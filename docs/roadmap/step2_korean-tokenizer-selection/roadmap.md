# Step 2: Korean Tokenizer Selection

## Purpose

Benchmark and select the Korean and mixed-language lexical strategy that will serve as the sparse branch for future hybrid retrieval.

## Why now

Korean retrieval is still an open lexical/tokenization question. The choice of tokenizer directly affects the quality of the sparse (BM25) branch, which is the foundation of any future hybrid system. As agreed in the architecture discussion, lexical strategy should be exhausted before semantic escalation, and the chosen strategy must be forward-compatible with hybrid fusion.

## Current reality

- `src/snowiki/search/kiwi_tokenizer.py` exists as an adjacent candidate path, but it is **not** the default runtime path.
- The current tokenizer handles mixed text by simple splitting and case folding, without morphological analysis.
- Mixed-language notes (Korean prose + English identifiers + file paths + code literals) are the real benchmark target, not Korean-only text in isolation.

## Scope

In scope:
- Compare the current tokenizer against Kiwi-backed tokenization (`kiwipiepy`) on Korean-only and mixed-language retrieval tasks.
- If baseline data permits, include Kkma/Okt-style baselines for reference.
- Evaluate known-item vs topical retrieval separately.
- Measure latency, memory, and installation/platform constraints.
- Produce a recommendation that selects the strategy for runtime promotion and future hybrid sparse branch.

Out of scope:
- Vector multilingual retrieval (Step 4).
- Changing the runtime default without passing the safety gate from Step 1.

## Non-goals

- Do not adopt Kiwi (or any tokenizer) without benchmark victory.
- Do not treat this as a one-time script; the benchmark must be reproducible and versioned.
- Do not ignore mixed-language reality.

## Dependencies

- **Step 1** must be complete so that the benchmark harness and runtime contract are stable.

## Risks

| Risk | Mitigation |
| :--- | :--- |
| Benchmark corpus does not match real user notes | Use a corpus that includes code, paths, identifiers, and mixed Korean-English sentences. |
| Chosen tokenizer wins on synthetic data but fails in production | Run integration tests on actual compiled wiki pages and session records. |
| Kiwi adds heavy native dependencies that complicate packaging | Evaluate install size, build-from-source risk, and platform coverage explicitly. |

## Deliverables

1. **Benchmark report** with Recall@k, MRR, nDCG for Korean-only and mixed-language slices.
2. **Latency / memory / platform matrix** for each candidate.
3. **Recommendation memo** that names the promoted tokenizer strategy.

## TDD and verification plan

1. Add benchmark slices before changing any runtime code.
2. Ensure the benchmark harness can swap tokenizers without editing runtime paths.
3. Verify with:
   - `uv run pytest tests/cli/test_query.py` — no regressions on existing queries.
   - `uv run snowiki benchmark --preset retrieval` — new Korean/mixed slices pass.
   - `uv run pytest -m integration` — tokenizer integration does not break runtime assembly.

## Promotion criteria to `.sisyphus/plans/`

This step graduates to execution when:
- One tokenizer strategy is clearly superior on mixed-language metrics.
- It passes the runtime safety gate (green test suite, no hidden dependencies).
- The benchmark is reproducible by another developer without manual setup.

## Reference citations

- `bab2min/Kiwi` — C++ Korean morphological analyzer with `kiwipiepy` Python bindings. Supports KNLM/SBG/CoNg model families and multiple language bindings. [Repo](https://github.com/bab2min/Kiwi)
- `docs/reference/research/qmd-lineage-and-korean-strategy.md` — internal design synthesis that frames Korean retrieval as a lexical/tokenization problem first.
- `hang-in/seCall` — uses Lindera as default with optional Kiwi fallback; demonstrates tokenizer init failure handling and conservative whitespace fallback. [`search/tokenizer.rs`](https://github.com/hang-in/seCall/blob/main/crates/secall-core/src/search/tokenizer.rs)
- `vlwkaos/ir` — uses standalone preprocessor executables for Korean (Lindera) and Japanese (IPADIC) with line-in/line-out protocol, applied at both index and query time. [`preprocessors/ko/lindera-tokenize/src/main.rs`](https://github.com/vlwkaos/ir/blob/main/preprocessors/ko/lindera-tokenize/src/main.rs)
- `AutoRAG example tokenizer benchmark` — shows that `ko_kiwi` can trail `ko_okt` and `ko_kkma` on some BM25 top-k metrics, emphasizing the need for corpus-specific evaluation. [README](https://github.com/Marker-Inc-Korea/AutoRAG-example-tokenizer-benchmark/blob/main/README.md)
- LangChain-OpenTutorial PR #509 — `10-Kiwi-BM25-Retriever` tutorial, showing active ecosystem integration. [PR](https://github.com/LangChain-OpenTutorial/LangChain-OpenTutorial/pull/509)

## Open questions

- Do we need a **pluggable tokenizer abstraction** in `workspace.py` so multiple strategies can coexist, or should we promote a single policy?
- If Kiwi is selected, which model size (small / base / large) strikes the right latency/quality tradeoff for a local CLI tool?
