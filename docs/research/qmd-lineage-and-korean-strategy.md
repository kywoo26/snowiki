# qmd Lineage and Korean Strategy

## Purpose

This document explains two related design questions:

1. What Snowiki should inherit from qmd and adjacent lineage systems
2. How Snowiki should think about Korean and mixed-language retrieval before escalating into semantic/vector solutions

## Evidence note

This document is a design-oriented research synthesis built from:
- qmd’s visible public positioning as a local retrieval substrate
- the already-documented role qmd plays in Snowiki’s lineage and roadmap discussions
- local Snowiki code and benchmark surfaces, especially the current lexical backbone and the existence of `kiwi_tokenizer.py` as a future/adjacent retrieval path
- the source appendix below, which records the concrete artifacts this framing rests on

It is intended to support architecture decisions, not to serve as a full scholarly survey of Korean IR methods.

That means:
- statements about qmd’s role are based on its visible retrieval posture and on Snowiki’s own design history
- statements about Korean strategy are partly direct (current code structure) and partly design inference (what should be benchmarked next)
- wherever a conclusion is a recommendation rather than a currently verified Snowiki fact, it should be read as such

## qmd’s role in Snowiki’s lineage

qmd is important to Snowiki, but in a specific way.

It is best treated as a **retrieval substrate reference**, not as Snowiki’s full product blueprint.

### What qmd contributes
- lexical-first discipline
- local-first operation
- optional hybrid/rerank posture instead of semantic-first assumptions
- retrieval as an evidence-producing subsystem
- strong sensitivity to speed/latency tradeoffs

### What qmd does *not* define for Snowiki
- Snowiki’s product identity
- provenance-aware compiled knowledge behavior
- the full wiki/knowledge maintenance model
- the complete agent-facing contract

In other words:

> Snowiki should inherit qmd’s retrieval seriousness, but not collapse into “search engine only.”

## What Snowiki should inherit from qmd

### 1. Lexical-first posture
Exact identifiers, paths, literals, and provenance-bearing text remain critical. Snowiki should continue to treat lexical retrieval as the default backbone.

### 2. Local-first search discipline
qmd’s local-first posture remains a strong architectural influence. Snowiki should preserve deterministic, inspectable, local-first search behavior.

### 3. Strategy-aware layering
The right lesson from qmd is not “always use vectors,” but “add sophistication only when the retrieval problem actually requires it.”

## What Snowiki should not inherit from qmd

### 1. Search-only identity
Snowiki is not trying to be just a search substrate. It is trying to become a provenance-aware knowledge engine.

### 2. Retrieval as the whole product
Retrieval is central, but not sufficient. Snowiki must also care about:
- compiled artifact quality
- provenance
- epistemic integrity
- maintenance loops
- agent ergonomics

## Korean retrieval: the current conclusion

For Snowiki, Korean retrieval should be treated as a **lexical/tokenization problem first**.

That means the next useful work is not “add semantic retrieval to solve Korean,” but to ask:
- how should Korean text be tokenized?
- how should mixed Korean-English text be handled?
- what lexical strategy wins on judged benchmark slices?

## Why this matters

The system already has:
- a lexical backbone
- mixed-language retrieval concerns
- a candidate Korean path via `kiwi_tokenizer.py`

So the correct first move is to benchmark lexical strategy choices, not to skip straight to embeddings.

## Main Korean design questions

### 1. Simple tokenizer vs Kiwi-backed morphology
This is the most concrete immediate question.

Snowiki should compare:
- current tokenizer behavior
- Kiwi-backed morphological tokenization

on:
- Korean-only retrieval
- mixed Korean-English retrieval
- known-item vs topical retrieval

### 2. Noun-heavy vs broader morphology
Korean retrieval quality can change significantly depending on whether the system extracts mostly nouns or allows broader morphological forms.

This should be treated as an explicit benchmark question, not a guess.

### 3. Exact surface forms vs normalized forms
For Korean, aggressive normalization can improve recall in some cases but damage precision or snippet trust in others.

This is especially important in a provenance-aware system, where users may care whether the retrieved text still looks faithful to source expressions.

### 4. Mixed-language retrieval
Snowiki should not assume Korean retrieval is only a Korean-only problem.

Real notes often contain:
- Korean prose
- English identifiers
- library names
- file paths
- code-oriented literals

So the real benchmark target is often **mixed-language lexical retrieval**, not just Korean morphology in isolation.

## What should happen next

### Keep
- lexical-first retrieval backbone
- qmd-like retrieval discipline

### Avoid
- treating vectors as the default answer to Korean retrieval quality
- assuming one Korean tokenizer is universally correct
- letting Korean strategy become detached from mixed-language reality

### Research later
- whether a selectable Korean strategy should exist
- how Korean lexical improvements interact with future hybrid retrieval
- whether semantic layers become justified after lexical benchmarking is exhausted

## Bottom line

Snowiki should treat qmd as a retrieval lineage, not as a product template, and it should treat Korean retrieval as a benchmarked lexical design problem before it treats it as a semantic/vector problem.

## Evidence appendix

Reviewed as of: 2026-04-12

### qmd evidence basis
- URL: https://github.com/tobi/qmd
- Inspected artifacts: public repository positioning and qmd’s visible local retrieval/search framing
- Supports:
  - qmd as a retrieval substrate rather than a full product model for Snowiki
  - lexical-first / local-first retrieval discipline
  - optional hybrid/rerank posture as a later sophistication layer

### Korean strategy evidence basis
- Current active runtime evidence:
  - `src/snowiki/search/indexer.py`
  - `src/snowiki/search/tokenizer.py`
  - `src/snowiki/search/workspace.py`
  - `src/snowiki/cli/commands/query.py`
  - `src/snowiki/cli/commands/recall.py`
- Adjacent Korean-specific evidence:
  - `src/snowiki/search/kiwi_tokenizer.py`
- Mixed-language concern evidence:
  - retrieval architecture and retrieval-focused integration tests
- Supports:
  - current runtime is lexical-first
  - Kiwi exists as an adjacent strategy candidate, not the default runtime path
  - a Korean lexical benchmark is a justified next step before semantic/vector escalation

## Traceability: evidence → conclusion → roadmap consequence

### qmd should be treated as lineage, not identity
- Evidence: qmd’s public posture is substrate-oriented and local retrieval-centric.
- Conclusion: Snowiki should inherit qmd’s retrieval discipline, not its full product scope.
- Roadmap consequence: qmd informs lexical/hybrid strategy and retrieval discipline, not Snowiki’s entire product identity.

### Korean retrieval should be lexical-first for now
- Evidence: Snowiki’s shipped runtime remains lexical-first, while Kiwi is present only as an adjacent candidate path.
- Conclusion: the next meaningful Korean work is benchmarked lexical/tokenization evaluation.
- Roadmap consequence: prioritize a Korean/mixed-language lexical benchmark before semantic/hybrid implementation.

### How to read this appendix
- This is enough evidence for roadmap and architecture sequencing.
- If Snowiki later makes a concrete Korean lexical decision (for example current tokenizer vs Kiwi-backed default), that decision should be backed by a dedicated benchmark/result document.
