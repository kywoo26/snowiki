# Damoang seCall Series — Snowiki Notes

## Sources

- https://damoang.net/ai/2221
- https://damoang.net/ai/2232
- https://damoang.net/ai/2257
- https://damoang.net/ai/2266

## Why this note exists

The Damoang posts are not a substitute for source-code inspection, but they capture something the repository alone does not: the **author's own explanation of sequencing, tradeoffs, and intended operating model**.

That makes them useful for Snowiki in two ways:
1. they explain why seCall evolved toward BM25 → embeddings → hybrid → vault/wiki workflow
2. they reveal where the methodology is strong operationally but still weak scientifically

## Per-post takeaways

### #2221 — Korean lexical baseline
- seCall begins from Korean-aware lexical retrieval rather than jumping directly to vectors.
- The practical lesson for Snowiki is that mixed-language lexical quality is still the foundation of later hybrid quality.

### #2232 — Embeddings and local-vector path
- The post emphasizes local-first embeddings, chunking, and the real runtime cost of CPU indexing.
- This reinforces that embedding lifecycle and hardware policy are roadmap topics, not afterthoughts.

### #2257 — Hybrid search
- The post presents hybrid as BM25 + vector + RRF with practical comparisons, not formal IR benchmarking.
- This is the sharpest reminder that Snowiki should **borrow the architecture but not the evaluation standard**.

### #2266 — Vault/wiki workflow
- The post shows how search output becomes curated Obsidian/Vault knowledge.
- This is more relevant to Snowiki Step 3 and overall product identity than to Step 4's raw retrieval design.

## Cross-series synthesis

### What Snowiki should borrow
1. lexical-first sequencing
2. local-first fallback discipline
3. the move from search substrate toward curated wiki/workflow surfaces

### What Snowiki should improve
1. explicit benchmark harnesses
2. mixed-language retrieval evaluation with durable reports
3. promotion gates for hybrid readiness instead of narrative confidence

## Bottom line

The Damoang series is valuable because it explains the **development logic** behind seCall.

For Snowiki, that logic should be translated into:
- stronger planning docs
- stronger benchmark/evaluation posture
- clearer separation between raw retrieval capability and curated knowledge-system behavior
