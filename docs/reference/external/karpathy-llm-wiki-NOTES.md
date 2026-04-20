# Karpathy LLM Wiki — Snowiki Analysis Notes

## Repository / artifact
- Canonical artifact: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## What this is
One of the clearest original public statements of the "LLM-maintained wiki" pattern: local files, human-curated sources, machine-maintained compiled knowledge, and a simple workflow loop.

## Key patterns to preserve for Snowiki

### Three-layer architecture
- raw sources
- compiled wiki
- schema/rules layer

This maps cleanly onto Snowiki's `sources/`, `wiki/`, and contract/governance surfaces.

### Minimal workflow surface
- `ingest`
- `query`
- `lint`

This is a useful simplification anchor for Snowiki's Step 3: current shipped contract should stay disciplined and small.

### Human vs agent responsibility split
- Human curates sources and asks questions.
- LLM does summarization, cross-linking, filing, and maintenance.

This remains one of Snowiki's strongest product-alignment references.

### Index-first navigation and append-only maintenance
- The wiki is not only a retrieval cache.
- It is a maintained artifact that gains structure over time.

## What Snowiki should not copy literally
- Karpathy's artifact is conceptual and intentionally lightweight.
- It is not a mature packaged skill/runtime contract in the way Snowiki now requires.

## Relevance to Snowiki steps
- Step 3: Wiki skill design

## Concrete Snowiki takeaways

1. Preserve the three-layer model as a first-class explanatory surface.
2. Keep the shipped command surface small and contract-driven.
3. Treat lint/maintenance as part of the product loop, not post-processing.
