# BM25 Retrieval Engine v2 Plan

## Purpose

This document defines the next retrieval architecture direction for Snowiki.

Snowiki should move from the current `InvertedIndex(regex_v1) + topical_recall`
runtime toward a BM25-first lexical runtime while preserving the installed CLI,
read-only MCP, provenance, and benchmark contracts.

This is a plan for follow-up implementation PRs, not a claim that BM25 is already
the shipped runtime.

## Decision

Use BM25 lexical retrieval as the next primary runtime direction.

Do not keep a long-lived internal dual runtime seam around the legacy
`InvertedIndex`. The compatibility seam that must remain stable is the external
runtime contract: CLI/MCP payload shape, provenance fields, result identity,
and benchmark comparability.

## Evidence

Local benchmark prechecks support BM25 as the right next engine direction:

| Dataset | Target | Recall@5 | Hit-rate@5 | MRR@10 | nDCG@10 | p95 |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `beir_scifact` standard | `snowiki_query_runtime_v1` | 0.6333 | 0.6533 | 0.5400 | 0.5797 | 14.4ms |
| `beir_scifact` standard | `bm25_regex_v1` | 0.6707 | 0.6867 | 0.5708 | 0.6112 | 0.2ms |
| `beir_scifact` standard | `bm25_kiwi_morphology_v1` | 0.6701 | 0.6867 | 0.5744 | 0.6130 | 0.4ms |
| `miracl_ko` standard | `snowiki_query_runtime_v1` | 0.4169 | 0.5915 | 0.4653 | 0.4339 | 311.1ms |
| `miracl_ko` standard | `bm25_regex_v1` | 0.3470 | 0.4930 | 0.3930 | 0.3500 | 5.2ms |
| `miracl_ko` standard | `bm25_kiwi_morphology_v1` | 0.4159 | 0.5681 | 0.4382 | 0.4115 | 4.6ms |

Interpretation:

- BM25 is already stronger on `beir_scifact` and much faster in both standard
  precheck slices.
- Korean quality is not settled. The current runtime is still slightly stronger
  on `miracl_ko`, so Korean and mixed-language promotion gates are mandatory.
- `bm25_hf_wordpiece_v1` is not a promotion candidate based on quick benchmark
  evidence.

External and local reference systems point to the same staged direction:

- qmd-style systems use BM25 plus vector search plus reranking as separate modes.
- seCall treats SQLite FTS5 BM25 as a first-class runtime mode, then adds vector
  recall, Reciprocal Rank Fusion, session diversity, graph prefilters, and
  optional semantic graph extraction on top.
- LLM wiki implementations that start with vector retrieval still preserve a
  lexical or index-routing fallback for exact titles, paths, commands, and code
  tokens.

## Non-goals for the first BM25 runtime PR

- Do not ship vector retrieval as part of the first BM25 runtime change.
- Do not ship semantic reranking as part of the first BM25 runtime change.
- Do not make graph or taxonomy ranking mandatory.
- Do not remove query/recall/MCP output contracts.
- Do not promote Kiwi, MeCab, or any Korean analyzer without the Korean and
  mixed-language gates below.

## Runtime contract to preserve

The following result fields remain the stable external seam:

- `id`
- `path`
- `title`
- `kind`
- `source_type`
- `score`
- `matched_terms`
- `summary`

Runtime metadata should also expose enough identity for agents to understand the
retrieval backend when the implementation changes:

- retrieval backend, for example `bm25_v2`
- tokenizer/analyzer identity
- semantic backend status, if any
- freshness/cache identity, when available

## Proposed architecture

```text
CLI / MCP
  -> query and recall orchestration
  -> RetrievalEngineV2
       -> CorpusBuilder
            -> normalized records
            -> compiled pages
       -> MixedLanguageAnalyzer
            -> English / numbers / code / path token preservation
            -> Korean morphology candidate tokens
       -> BM25 candidate generation
       -> Metadata and graph prefilters
       -> Diversity policy
       -> ResultAdapter
            -> existing CLI/MCP payload contract
```

### CorpusBuilder

Build a common search corpus from normalized records and compiled pages.

It must preserve:

- document identity
- path and title
- `kind` (`session`, `page`, or future stable kinds)
- source type and provenance
- timestamps for date and temporal recall
- aliases/tags/related records where available

### MixedLanguageAnalyzer

The analyzer must support Snowiki's real corpus shape, not only natural prose.

It should preserve tokens for:

- Korean natural language
- English words
- numbers
- file paths
- `snake_case`
- `kebab-case`
- `camelCase`
- dotted names such as `package.module.symbol`
- CLI commands and flags
- Python/TypeScript symbols
- Markdown headings

The first implementation may have two benchmarked variants:

- regex/code/path preserving BM25
- Korean morphology plus regex/code/path preserving BM25

### BM25 candidate generation

BM25 becomes the primary lexical candidate generator.

The first implementation can reuse the existing benchmark BM25 implementation if
it satisfies runtime payload and freshness requirements. If SQLite FTS5 is chosen
instead, it must remain rebuildable from Snowiki storage artifacts and must not
become the source of truth.

### Metadata and graph prefilters

Graph and taxonomy signals should start as prefilters, not rankers.

Examples:

- source path allowlists
- kind filters
- date windows
- tag/topic filters
- deterministic related-page or record-id filters

LLM semantic graph extraction is deferred until after the BM25 runtime is stable.

### Diversity policy

The engine should prevent one source, page, or session from monopolizing the
first screen of results.

Start with a simple cap such as max results per source/kind/session and verify it
against `hit_rate_at_5` and `recall_at_5`.

## Query and recall split

`query` and `recall` should not collapse into one generic search command.

- `query` is topical document retrieval.
- `recall` is memory reconstruction with time, session, source, and known-item
  clues.

BM25 lexical-v2 should power candidate generation for both, but recall keeps
first-class routing for date, temporal, known-item, and topic intents.

## Promotion gates

BM25 runtime promotion requires:

1. no CLI JSON payload regression,
2. no read-only MCP payload regression,
3. no provenance/source identity regression,
4. `hit_rate_at_5` and `recall_at_5` improvement or tie on English public slices,
5. no unacceptable Korean regression on `miracl_ko`,
6. no regression on Snowiki-owned golden queries for Korean, English, mixed
   language, path, code, CLI/tool, known-item, and session/history cases,
7. acceptable p95 latency,
8. full `uv run ruff check src/snowiki tests && uv run ty check && uv run pytest`,
9. `uv run pytest -m integration`.

## Snowiki-owned golden slices

Before runtime promotion, add a Snowiki-domain retrieval set with at least these
slices:

1. Korean query -> Korean document
2. Korean query -> English or code-heavy document
3. English query -> Korean document
4. mixed Korean/English query
5. exact path or filename query
6. code/API/symbol query
7. CLI/tool command query
8. session/history query
9. topical exploratory query
10. source/provenance validation query

## PR sequence

### PR 1: benchmark baseline and architecture contract

- Add top-k benchmark metrics and a runtime-shaped query target.
- Capture standard precheck evidence.
- Add this BM25 runtime v2 plan.

### PR 2: runtime corpus and analyzer contract

- Introduce typed corpus documents for runtime retrieval.
- Introduce the mixed-language analyzer contract and tests.
- Add Snowiki-owned golden query fixtures.

### PR 3: BM25 runtime implementation

- Add `RetrievalEngineV2` with BM25 candidate generation.
- Preserve CLI/MCP payload parity.
- Keep recall routing but use BM25 for candidate generation.

### PR 4: remove legacy primary path

- Remove `InvertedIndex` as the primary runtime query engine.
- Keep only compatibility/test helpers that are still justified.
- Remove or rename fake hybrid/reranker surfaces that do not represent active
  behavior.

### PR 5: graph/vector follow-up

- Add deterministic graph/taxonomy prefilters.
- Add optional vector recall and RRF only after the BM25 runtime is stable.
