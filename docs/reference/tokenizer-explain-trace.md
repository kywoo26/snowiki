# Tokenizer Explain Trace

## Purpose

`experimental.token_explain.v1` is an experimental benchmark diagnostics schema for inspecting Snowiki's lexical retrieval behavior.

Its purpose is to explain which analyzer and tokenizer produced which query tokens and which lexical terms matched returned documents during benchmark runs. It exists to make Korean morphology, mixed CJK/code, and identifier or path-heavy benchmark cases reviewable without changing runtime retrieval behavior.

This is a diagnostic surface for benchmark evidence, not a stable runtime contract.

## Scope

The explain trace is limited to lexical benchmark diagnostics.

- It appears only when benchmark diagnostics are requested with `--include-diagnostics`.
- It is intended for benchmark reports and related evidence review.
- It is not exposed in stable `snowiki query` JSON output.
- It does not expand the minimal `RuntimeSearchIndex` protocol or the stable CLI or MCP retrieval payload.

This scope matches Snowiki's current runtime boundary: the shipped runtime remains lexical-only BM25 retrieval, and tokenizer access stays a concrete backend diagnostic rather than a protocol-level requirement.

## Schema Version

Current schema version:

- `experimental.token_explain.v1`

The `experimental.` prefix is intentional. Breaking changes are allowed without a deprecation period.

## Schema Fields

Each explain trace entry should include these fields:

| Field | Meaning |
| :--- | :--- |
| `schema_version` | Versioned schema identifier. Must be `experimental.token_explain.v1`. |
| `analyzer_name` | Human-readable analyzer lane or analyzer identity used for the trace. |
| `tokenizer_name` | Tokenizer identity from the existing tokenizer registry and cache identity path. |
| `tokenizer_version` | Version string for the tokenizer implementation. |
| `tokenizer_config` | Active tokenizer configuration used for tokenization. |
| `query_tokens` | Query token stream after normalization and tokenization. |
| `matched_terms` | Compact lexical term evidence for traced returned documents. |
| `stages` | Stage labels that explain where tokens or matches came from in the lexical pipeline. |
| `limits` | Explicit caps used to bound trace size. |
| `truncated` | Boolean flags that record whether any cap was exceeded. |

The trace is intentionally compact. It explains tokenization and match evidence without dumping full backend state.

## Size Caps

The experimental trace uses hard caps to keep benchmark artifacts reviewable and bounded:

- Maximum `128` query tokens.
- Maximum `5` traced returned documents per query.
- Maximum `64` matched terms per traced document.

These limits belong to the diagnostics payload, not to retrieval or ranking behavior.

## Truncation Behavior

When a cap is exceeded, the trace keeps the bounded subset and records truncation with boolean flags in `truncated`.

Expected behavior:

- If more than `128` query tokens are produced, `query_tokens` is capped and the query-token truncation flag is `true`.
- If more than `5` returned documents are eligible for tracing, only the bounded subset is included and the document-trace truncation flag is `true`.
- If a traced document has more than `64` matched terms, only the bounded subset is included and the matched-term truncation flag is `true`.

The `limits` object should make the active caps explicit so report consumers can interpret `truncated` without out-of-band assumptions.

## Diagnostic-Only Surface

The explain trace is intentionally diagnostic-only.

- Present: benchmark CLI reports generated with `--include-diagnostics`.
- Absent: default benchmark reports without diagnostics.
- Absent: stable `snowiki query` JSON output.
- Absent: stable runtime result payloads exposed by normal CLI or MCP retrieval.

This keeps benchmark observability separate from the shipped runtime contract.

## Privacy And Text Policy

The trace is bounded to reviewable lexical evidence and avoids raw full-text leakage.

- Allowed inputs: benchmark query text already present in benchmark metadata.
- Allowed evidence: document IDs, query tokens, matched lexical terms, stage labels, tokenizer identity, tokenizer configuration, and truncation flags.
- Not allowed: raw full document text.
- Not allowed: full document token dumps.

This follows the same conservative evidence posture used by Snowiki's regression documentation: expose only the minimum reviewable evidence needed to inspect benchmark behavior.

## Example Query IDs

Representative regression queries for this diagnostics surface include:

- `ko_source_provenance_inflection`
- `cjk_mixed_code_bm25_cache`
- `identifier_bm25_index`

These examples cover Korean inflection behavior, mixed CJK and code or path tokenization, and identifier or path-heavy lexical matching.

## Non-Goals

This experimental schema does not imply any of the following:

- No runtime default tokenizer change.
- No BM25 scoring or ranking change.
- No qrels or benchmark corpus change.
- No hybrid retrieval, vector retrieval, semantic reranking, or Reciprocal Rank Fusion.
- No analyzer promotion.
- No stable CLI payload expansion.
- No claim that tokenizer quality improved.

The explain trace is an observability aid for benchmark diagnostics only.

## Versioning Policy

`experimental.token_explain.v1` is an experimental schema.

- It is versioned so benchmark evidence can name the payload shape explicitly.
- It is not a production-ready stability promise.
- Breaking changes are allowed without a deprecation period.

If the payload later needs stronger compatibility guarantees, that should be treated as a separate contract decision rather than assumed from this reference note.
