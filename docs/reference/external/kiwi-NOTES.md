# bab2min/Kiwi — Snowiki Analysis Notes

## Repository
- https://github.com/bab2min/Kiwi

## What this is
C++ Korean morphological analyzer with multiple bindings. Core candidate for Snowiki's Korean lexical layer.

## Key findings already extracted
- Model families: KNLM, SBG, CoNg, `largest` selector
- SIMD dispatch: sse2, sse4_1, avx2, avx_vnni, avx512*, neon
- C API exposes builder pattern, `AnalyzeOption`, match flags, typo transformer
- Bindings: Java/Android, Swift/SPM, WASM/TS, external Python (`kiwipiepy`)
- Performance: ~1.9 ms/line base model; typo correction adds memory but improves accuracy

## Open questions for Snowiki
- Which model size (small / base / large) is the right latency/quality tradeoff for a local CLI tool?
- How does `kiwipiepy` compare to Lindera (used in `vlwkaos/ir` and `seCall`) in terms of install size and cold-start?
- Should we build a **pluggable tokenizer abstraction** or promote a single policy?

## Relevance to Snowiki steps
- Step 2: Korean tokenizer selection
