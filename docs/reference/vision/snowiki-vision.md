# Snowiki Vision

## What Snowiki is

Snowiki is a **provenance-aware, compiled knowledge engine**.

Its purpose is not to answer questions by re-deriving everything from raw sources on every query, and not merely to store notes in a searchable bucket. Instead, Snowiki incrementally compiles raw material into a persistent, inspectable, interlinked knowledge artifact that can be queried, linted, recalled, and improved over time.

In practical terms, Snowiki sits between:
- external source roots and raw provenance snapshots,
- retrieval/search infrastructure,
- and a maintained wiki-like knowledge artifact.

It is therefore closer to a **knowledge compiler** or **knowledge operating substrate** than to a generic chat-with-documents RAG application.

## Foundational philosophy

### 1. Compilation, not storage
The core idea is that value is created during compilation.

Raw sources, session traces, and notes are not the final product. The final product is a derived artifact built from them:
- summaries
- concepts
- entities
- topics
- comparisons
- questions
- overviews

This means Snowiki is not optimized around “store everything and search later,” but around “turn sources into a higher-order knowledge structure and keep that structure useful.”

### 2. Epistemic integrity
Snowiki is intended to preserve the difference between:
- facts and inferences
- evidence and synthesis
- source truth and derived knowledge

This is why provenance matters. Snowiki’s long-term direction is not only “better retrieval,” but **better grounded retrieval and better grounded compiled knowledge**.

### 3. Compounding knowledge
Snowiki inherits the most important philosophical thread from Karpathy’s llm-wiki direction: the artifact should improve with time.

The goal is not merely to answer well once, but to make the next answer easier, more grounded, more structured, and more reusable. Queries, ingests, and corrections should all contribute to this compounding process.

### 4. Local-first and inspectable
Snowiki assumes a local-first posture.

This means:
- deterministic local operation matters
- explicit benchmark/evaluation discipline matters
- inspectable machine-readable outputs matter
- hidden cloud-only magic is not the default assumption

This does not forbid later semantic or model-backed layers, but it means they must remain subordinate to a system that is still understandable and operable locally.

### 5. Agent-friendly by design
Snowiki is not only for humans. It is also meant to become a strong tool for LLMs and agents.

That implies:
- stable CLI contracts
- machine-readable JSON output
- MCP-friendly retrieval primitives
- composable workflows/skills
- deterministic enough behavior to be reliable inside agent loops

Agent ergonomics are not documentation polish; they are part of the architecture.

## Lineage and what Snowiki should inherit

Snowiki did not emerge in isolation. Several lineages matter, but they matter in different ways.

### Karpathy / llm-wiki lineage
This is the philosophical starting point: a maintained wiki that improves by absorbing sources and conversation, rather than a system that only performs query-time retrieval.

What Snowiki should inherit:
- compounding knowledge
- persistent artifact over ephemeral answer generation
- human-in-the-loop knowledge growth

What Snowiki should not inherit uncritically:
- optimism that organization alone solves epistemic problems
- under-specification of provenance and verification

### qmd lineage
qmd matters as a **retrieval substrate reference**.

What Snowiki should inherit:
- lexical-first discipline
- local-first operation
- optional hybrid/rerank hooks as extensions, not default assumptions
- retrieval as an evidence-producing subsystem, not just a UX surface

What Snowiki should not inherit as product identity:
- becoming “just a search engine”
- conflating retrieval power with a complete knowledge system

### seCall lineage
seCall matters as a provenance-first, local workflow sibling.

What Snowiki should inherit:
- session/source/workflow seriousness
- maintenance discipline
- emphasis on real-world local usage

What Snowiki should not inherit blindly:
- any assumptions that belong to its own product boundary rather than Snowiki’s

## Product identity

Snowiki should be understood as:

> a local-first, provenance-aware, agent-friendly system that compiles sources and sessions into a maintained knowledge artifact, then serves search, recall, linting, and future reasoning workflows from that artifact.

It is **not** best described as:
- generic RAG
- chat with docs
- a pure memory layer
- a plain markdown search engine

Those may be adjacent systems or useful comparisons, but they are not the center of Snowiki’s identity.

## Current strategic direction

At the current stage, Snowiki should prioritize:
1. a clear source/raw/normalized/compiled taxonomy
2. a canonical retrieval/corpus contract
3. lexical-first retrieval quality and performance
4. stronger evidence and benchmark discipline
5. clearer agent-facing runtime contracts

It should explicitly defer, for now:
- default semantic/vector retrieval
- reranking in the default path
- backend replacement
- model-heavy local flows as the mainline architecture

## Success condition

Snowiki is truly succeeding when it can:
- ingest real source/session material,
- compile it into a useful evolving knowledge artifact,
- expose that artifact reliably through CLI/MCP/agent-friendly contracts,
- preserve provenance and structural health,
- and make future knowledge work easier instead of harder.
