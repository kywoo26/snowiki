# Sub-step B: Tokenizer Abstraction Registry

## Purpose

Fix the architectural seam for Step 2 before benchmarking more candidates. Tokenizer selection cannot be promoted safely while benchmark code and runtime code use different tokenization wiring models.

## Decision

Step 2 will use a **pluggable tokenizer interface with a single promoted default**, not a hardcoded "pick one tokenizer and wire it directly everywhere" approach.

This is the required direction because:

- the current codebase already has multiple lexical paths (`tokenizer.py` in runtime, Kiwi in `bm25_index.py`)
- the benchmark layer currently hardcodes candidate names in `src/snowiki/bench/baselines.py`
- Step 2 must compare candidates reproducibly before any runtime promotion is final

The registry exists to make evaluation and migration deterministic. It is **not** permission to keep runtime behavior permanently ambiguous. At the end of Step 2, Snowiki still promotes one runtime default policy.

## Scope

In scope:

- Define the tokenizer registry and factory contract used by benchmark and runtime search assembly.
- Define how a tokenizer candidate is named, instantiated, versioned, and persisted in metadata.
- Define the migration path from current special-cased Kiwi flags and baseline aliases.
- Define backward-compatibility rules for existing indexes and benchmark reports.

Out of scope:

- Implementing the registry.
- Adding configuration knobs beyond those needed for Step 2 comparison.
- Introducing semantic or hybrid retrieval abstractions.

## Chosen architecture

### Policy

Snowiki will standardize on these two levels:

1. **Registry level**: multiple tokenizer candidates may exist and be benchmarked.
2. **Runtime level**: one candidate is designated as `default` and used unless a collection explicitly records another tokenizer identity.

### Why not "promote one tokenizer now"?

That option would keep the codebase simple in the short term, but it fails Step 2's actual need:

- it does not solve benchmark/runtime parity
- it makes candidate comparison depend on ad hoc wiring changes
- it weakens reproducibility because candidate identity is not first-class metadata

The registry is therefore mandatory for Step 2 execution.

## Registry and factory API shape

The registry contract for Step 2 is:

- `TokenizerSpec`
  - `name`: stable identifier such as `regex_v1`, `kiwi_morphology_v1`, `kiwi_nouns_v1`
  - `family`: broad backend family such as `regex`, `kiwi`, or `lindera`
  - `version`: Snowiki-controlled spec version, not just upstream package version
  - `runtime_supported`: whether the candidate is allowed in shipped runtime selection
  - `benchmark_supported`: whether the candidate can be evaluated in benchmark runs

- `TokenizerFactory`
  - input: `TokenizerSpec` plus optional backend settings
  - output: a tokenizer object exposing one canonical method for search token generation

- `TokenizerRegistry`
  - `register(spec, factory)`
  - `get(name)`
  - `default()`
  - `all_candidates(scope)` where `scope` is `runtime` or `benchmark`

- `SearchTokenizer`
  - canonical behavior: accept `text: str` and return search tokens suitable for both indexing and query-time use
  - the same candidate identity must be usable at both index-build time and query time

Step 2 does **not** require a richer structured token object yet. Search benchmarking may stay string-token based as long as candidate identity is explicit and stable. Structured offsets and POS metadata are deferred until they are required by a later retrieval feature.

## Candidate identity rules

- Candidate names must be stable and human-readable.
- Benchmark aliases such as `bm25s_kiwi_full` are migration-era names only; they are not the canonical long-term registry identity.
- Canonical identities must encode the lexical policy, not just the library brand. Example: `kiwi_morphology_v1` is preferred over `kiwi_full`.
- If backend behavior changes in a way that can affect retrieval output, bump the Snowiki spec version.

## Metadata and persistence rules

- Every built search index must persist the tokenizer candidate identity used at index-build time.
- Loading an index with a different current default must not silently reinterpret stored tokens.
- If a requested runtime tokenizer differs from the stored tokenizer identity for an index, Snowiki must treat the index as stale and require rebuild rather than silently mixing policies.
- Benchmark reports must record candidate identity using canonical registry names.

## Migration path

Step 2 will treat migration in four ordered stages:

1. **Introduce canonical candidate names** for current regex and Kiwi modes.
2. **Replace baseline-name-to-Kiwi-mode branching** in `src/snowiki/bench/baselines.py` with registry lookup.
3. **Route runtime lexical assembly through the same registry seam** used by benchmark BM25 construction.
4. **Promote one candidate as runtime default** only after Step 2 benchmark gates are satisfied.

The current behavior of `use_kiwi_tokenizer` and `kiwi_lexical_candidate_mode` is treated as a legacy compatibility layer during migration, not the end-state API.

## Backward-compatibility rules

- Existing indexes that only store `use_kiwi_tokenizer` and `kiwi_lexical_candidate_mode` remain loadable during the migration window.
- Legacy metadata must be deterministically mapped into a canonical candidate name on load.
- Existing benchmark preset names may remain as compatibility aliases for one migration cycle, but reports and new code paths must use canonical registry names.
- Runtime default behavior for users who do not opt into Step 2 changes must remain unchanged until a candidate is formally promoted.

## Deliverables

1. A written architectural decision that selects the pluggable registry approach.
2. A canonical naming scheme for tokenizer candidates.
3. A migration sequence from current hardcoded benchmark/runtime seams to registry-driven selection.
4. Backward-compatibility rules for stored metadata and legacy preset aliases.

## Non-goals

- Do not expose arbitrary user-provided shell commands as tokenizer backends in Step 2.
- Do not make tokenizer selection a free-form CLI surface before candidate promotion is complete.
- Do not leave runtime/benchmark parity as a later cleanup item.

## Acceptance criteria

- The architecture decision explicitly chooses a pluggable tokenizer registry with one eventual promoted default.
- The registry/factory API shape is documented clearly enough that implementation can proceed without reopening the design question.
- Candidate identity, metadata persistence, and stale-index rebuild rules are documented.
- The migration path explains how current Kiwi flags and baseline aliases transition into canonical registry names.
- Backward-compatibility rules are explicit for both stored index metadata and benchmark naming.
