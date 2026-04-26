# BM25 Retrieval Engine

## Purpose

This document describes Snowiki's primary lexical retrieval engine.

Snowiki uses BM25 candidate generation for CLI query, CLI recall, read-only MCP
retrieval, and the runtime-shaped benchmark target while preserving the external
runtime contract.

## Decision

BM25 is the primary runtime retrieval substrate.

The compatibility seam is the external result contract, not an internal dual
engine path. CLI and MCP payloads continue to expose stable result fields:

- `id`
- `path`
- `title`
- `kind`
- `source_type`
- `score`
- `matched_terms`
- `summary`

## Runtime architecture

```text
CLI / MCP
  -> query and recall orchestration
  -> RuntimeSearchIndex
       -> RuntimeCorpusDocument records/pages
       -> BM25RuntimeIndex
       -> BM25SearchIndex candidate generation
       -> SearchHit / SearchDocument result adapter
```

The active implementation lives in:

- `src/snowiki/search/engine.py`
- `src/snowiki/search/protocols.py`
- `src/snowiki/search/bm25_index.py`
- `src/snowiki/search/corpus.py`
- `src/snowiki/search/workspace.py`

## Query and recall split

`query` and `recall` remain separate user intents.

- `query` is topical document retrieval.
- `recall` is memory reconstruction with time, session, source, and known-item
  clues.

Both use BM25 for candidate generation, while recall keeps first-class routing
for date, temporal, known-item, and topical strategies.

## Analyzer status

The default runtime tokenizer remains the regex tokenizer. Kiwi, MeCab, and
other analyzers remain benchmarkable BM25 candidate lanes until they pass Korean,
mixed-language, path, code, CLI/tool, known-item, session/history, latency, and
packaging gates.

## Deferred work

- Deterministic graph/taxonomy prefilters.
- Optional vector recall and Reciprocal Rank Fusion.
- Analyzer promotion after Snowiki-owned golden query and public benchmark gates.
