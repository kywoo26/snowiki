# AutoRAG Korean BM25 / Tokenizer Benchmark Notes

## Sources reviewed
- https://velog.io/@autorag/%ED%95%9C%EA%B5%AD%EC%96%B4-BM25%EC%97%90%EC%84%9C-%EC%B5%9C%EA%B3%A0%EC%9D%98-%ED%86%A0%ED%81%AC%EB%82%98%EC%9D%B4%EC%A0%80%EB%8A%94-%EB%AC%B4%EC%97%87%EC%9D%B8%EA%B0%80-%ED%95%9C%EA%B5%AD%EC%96%B4-%ED%86%A0%ED%81%AC%EB%82%98%EC%9D%B4%EC%A0%80-%EB%B2%A4%EC%B9%98%EB%A7%88%ED%81%AC-%EA%B0%80%EB%B3%B4%EC%9E%90%EA%B3%A0
- https://velog.io/@autorag/%ED%95%9C%EA%B5%AD%EC%96%B4-%EB%AC%B8%EC%84%9C%EC%97%90%EC%84%9C-BM25-%EC%82%AC%EC%9A%A9-%EC%8B%9C-%EA%BC%AD-%ED%99%95%EC%9D%B8%ED%95%B4%EC%95%BC-%ED%95%A0%EA%B2%83
- AutoRAG docs and dataset format references
- AutoRAG tokenizer benchmark example repo
- Korean-MTEB / KURE / rank_bm25 / Kiwi references

## Why this note exists
This note preserves the external benchmark/evaluation takeaways that remained useful during Snowiki Step 2. It is not a benchmark proof owner. It is a roadmap-owned external evidence note.

## Durable takeaways for Snowiki

### 1. Tokenizer winners are corpus-specific
The strongest external lesson is that there is no universally winning Korean BM25 tokenizer. AutoRAG-style experiments show corpus-specific variance, and the benchmark repo cited by the posts found `ko_okt` best on one corpus while `ko_kkma` and `ko_kiwi` remained competitive.

**Snowiki implication**: treat tokenizer selection as dataset-specific evidence work, not as a library-brand decision.

### 2. Top-k sweeps matter more than one cutoff
The benchmark practice around Korean BM25/tokenizer evaluation uses multiple top-k values (`1/3/5/10/50`) and multiple retrieval metrics (`Recall`, `MRR`, `nDCG`, often `Precision`/`F1` as supporting signals).

**Snowiki implication**: do not trust a single `top_k=5` result or a single metric when deciding tokenizer promotion.

### 3. Golden-set quality matters as much as tokenizer choice
Industry-grade evaluation practice is not just “many queries.” It requires:
- query coverage that mirrors real user traffic
- explicit positives / relevance judgments
- ambiguous and hard-negative cases
- identifier/path/code-heavy queries when the domain needs them
- judged-aware evaluation discipline when pools are incomplete

**Snowiki implication**: the benchmark corpus and judgments are first-class product assets, not disposable scaffolding.

### 4. Preserve English/code/path signal explicitly
The external Korean BM25 advice lines up with Snowiki's own findings: English defaults are not enough for Korean corpora, but pure Korean morphology also does not automatically solve mixed-language lexical retrieval.

**Snowiki implication**: mixed Korean-English wiki/session search needs explicit preservation of:
- identifiers
- file paths
- tool names
- code-like tokens
alongside Korean morphology.

### 5. Operational evidence should be measured, not guessed
The external benchmark sources emphasize practical retriever choices, but production-grade decision making still needs memory/disk/platform/install evidence.

**Snowiki implication**: Step 2 was right to require operational evidence before promotion; that requirement should remain part of any future candidate-family reopening.

## Recommended benchmark discipline if Step 2 is reopened later

1. Keep `queries.json` / `judgments.json` canonical and versioned.
2. Evaluate multiple top-k values, not just one.
3. Report `Recall@k`, `MRR`, and `nDCG` as the main decision signals.
4. Keep Korean-only, English-only, and mixed-language slices explicit.
5. Include identifier/path/code-heavy golden queries.
6. Use judged-aware evaluation discipline when judgments are incomplete.
7. Compare tokenizer families and tokenizer strategies separately.

## What not to overlearn from the external sources
- Do not assume AutoRAG's best tokenizer on one corpus will be Snowiki's best tokenizer.
- Do not assume a near-miss benchmark means runtime promotion is “close enough.”
- Do not replace domain-specific judgments with generic leaderboard confidence.

## Concrete Snowiki takeaway
**Tokenizer choice is corpus-specific; Kiwi is a strong candidate family, not a universal winner.**
