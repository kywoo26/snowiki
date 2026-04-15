# Sub-step A: Mixed-Language Benchmark Corpus

## Purpose

Freeze the benchmark corpus definition for Step 2 so tokenizer selection is measured against Snowiki's real retrieval surface rather than Korean-only toy text.

## Decision

For Snowiki, a **true mixed-language corpus** means retrieval data where a single query, document, or both may combine all of the following in the same item:

- Korean prose or questions
- English identifiers and product terms
- file paths and filenames
- code literals, flags, JSON keys, diff fragments, or command names

The benchmark corpus for Step 2 will therefore keep three explicit slices:

- `ko`: Korean-first phrasing with minimal English leakage
- `en`: English-first phrasing with repository and tool terms
- `mixed`: Korean prose interleaved with English identifiers, file paths, filenames, and code literals

The `mixed` slice is the promotion slice for tokenizer choice. `ko` and `en` remain guardrail slices so a candidate cannot win mixed retrieval by regressing the monolingual edges.

## Scope

In scope:

- Define the canonical corpus contents used for tokenizer comparison.
- Freeze how fixtures, queries, and judgments are sourced and labeled.
- Define query-to-page pairing rules for known-item, topical, and temporal retrieval.
- Require reproducibility metadata so another developer can rebuild the same corpus without hand-curation.

Out of scope:

- Adding new runtime ingestion behavior.
- Changing benchmark thresholds in `benchmarks/AGENTS.md`.
- Expanding into semantic retrieval or embedding evaluation.

## Corpus sources

Step 2 will use the existing canonical benchmark fixture set as the base corpus source of truth because it is already wired through `src/snowiki/bench/corpus.py` and reproducibly seeded into an isolated benchmark root.

Required source classes:

1. Claude JSONL fixtures from `fixtures/claude/`
2. OpenCode database fixtures from `fixtures/opencode/`
3. Compiled wiki pages and normalized records produced by the benchmark ingest/rebuild flow from those fixtures

Step 2 does **not** introduce ad hoc local notes, manually copied wiki pages, or developer-specific vault exports. Corpus provenance must stay entirely inside repository-tracked fixtures plus deterministic rebuild output.

## Labeling rules

### Query group labeling

- Label a query as `ko` only when its natural-language framing is predominantly Korean and any English token is incidental.
- Label a query as `en` only when its natural-language framing is predominantly English, even if it references repository terms.
- Label a query as `mixed` when Korean and English both contribute meaning to retrieval, especially when the query contains any of the following:
  - code or CLI terms such as `tool_use`, `resume continuation`, `privacy gate`
  - filenames such as `design-notes.md` or `benchmarks/judgments.json`
  - paths such as `fixtures/opencode/with_diffs.db`
  - symbols or literals whose English form should remain searchable

If a query can be rewritten into pure Korean without losing retrieval intent, it does not belong in `mixed`.

### Document slice labeling

The benchmark does not add a separate persisted document-slice field. Instead, document relevance is inferred from the query slice and the frozen judgments. This keeps Step 2 aligned with the current benchmark asset format in `benchmarks/queries.json` and `benchmarks/judgments.json`.

### Fixture labeling

Each relevant judgment must resolve to a stable fixture identifier already supported by the benchmark lookup path, such as `claude_basic`, `claude_tools`, or `omo_diffs`. Do not use ephemeral compiled page paths as canonical labels.

## Query and page pairing strategy

### Known-item queries

- Each known-item query must have exactly one primary target fixture.
- Additional relevant results are allowed only when the intent explicitly names a family of materials rather than a single source.
- The gold answer should map through the fixture lookup layer, not through machine-local compiled page paths.

### Topical queries

- Topical queries must have two or more relevant targets when the concept genuinely spans multiple fixtures.
- The relevant set should prefer coverage across source types when justified, for example Claude plus OpenCode fixtures for the same topic.
- Topical judgments must reward retrieval of the right topic cluster, not just a single filename mention.

### Temporal queries

- Temporal queries must ground to fixtures whose record or session timestamps support the temporal phrasing.
- The relevant set may include more than one fixture if multiple fixtures legitimately satisfy the same day- or period-based request.

### Page/record parity rule

When a compiled page and its originating fixture represent the same benchmark target, the judgment remains anchored to the fixture identifier. The benchmark may surface either the record or the compiled page, but evaluation must collapse both back to the same canonical fixture target. This preserves comparability across index implementations.

## Deliverables

1. A frozen corpus spec that defines `ko`, `en`, and `mixed` slices.
2. A versioned benchmark asset update plan that keeps queries and judgments in repository-tracked JSON.
3. A provenance note format that records benchmark ID, source fixture set, creation date, and update date.

## Non-goals

- Do not create a Korean-only benchmark track divorced from Snowiki's mixed-language notes.
- Do not permit one-off local fixture additions for tokenizer experiments.
- Do not evaluate candidates against undocumented or manually assembled corpora.

## Acceptance criteria

- The Step 2 corpus definition names `ko`, `en`, and `mixed` slices explicitly, with `mixed` defined as Korean prose plus English identifiers, file paths, or code literals in the same retrieval item.
- Corpus inputs are fully versioned in repository-tracked fixtures plus repository-tracked `benchmarks/queries.json` and `benchmarks/judgments.json`.
- Another developer can reproduce the same benchmark corpus by seeding the canonical benchmark root and rebuilding, with no manual note selection.
- Query and judgment labels are stable fixture identifiers rather than machine-local compiled output paths.
- Known-item, topical, and temporal pairing rules are documented and leave no ambiguity about when multiple relevant targets are allowed.
