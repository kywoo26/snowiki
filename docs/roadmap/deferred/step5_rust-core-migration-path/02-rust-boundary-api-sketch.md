# Rust Boundary API Sketch

## Purpose

Define the narrow declarative interface Snowiki would use if Step 5 promotes a Rust acceleration spike. This sub-step exists to lock down what may cross the Python↔Rust boundary before any native implementation work begins.

## Scope

In scope:
- define the request and response structs that may cross the boundary
- define how configuration is serialized
- define what Rust owns versus what Python owns
- define the invariants that keep the boundary declarative and stable

Out of scope:
- implementing PyO3 bindings
- choosing the final hot path before profiling evidence exists
- moving CLI orchestration, config parsing, or agent-facing behavior into Rust
- designing a large object-oriented native API surface

## Non-goals

- Do not allow Python callbacks inside the hot loop.
- Do not pass live Python objects across the boundary for core retrieval work.
- Do not let the native layer own user-facing workflow semantics.
- Do not create a boundary that depends on implicit Python process state.

## Boundary design principles

1. **Config in / results out**: Python sends declarative inputs; Rust returns plain results and diagnostics.
2. **Stable data contracts**: boundary objects must be versionable, serializable, and inspectable.
3. **Native ownership of hot state**: if Rust is used, it owns native index/search state rather than re-entering Python during core loops.
4. **Explicit metadata**: tokenizer signature, schema signature, and index compatibility data must be returned or persisted explicitly.

## Ownership split

Python owns:
- CLI commands
- user-facing config parsing
- workflow orchestration
- skill and agent behavior
- fallback-path selection and diagnostics presentation

Rust owns:
- CPU-bound tokenization or preprocessing kernels if promoted
- native index build/search kernels if promoted
- persisted native index state if a native index is introduced
- boundary-level diagnostics about native execution and index compatibility

## Serialization strategy

### Recommended format

- Python wrapper layer constructs typed Python dataclasses or Pydantic-like internal objects
- boundary crossing uses plain primitives, lists, and maps compatible with PyO3 extraction
- persisted metadata uses an explicit JSON-serializable schema so the same config can be logged, inspected, and versioned

### Rules

- request and response structs must be representable without Python object identity
- all enums crossing the boundary must have explicit string forms
- file paths, schema versions, and tokenizer signatures must be explicit fields rather than hidden globals
- binary-native state may remain inside Rust, but its opening/build configuration must be serializable from Python

## Proposed boundary structs

The exact first implementation may use only a subset of these, but Step 5 should constrain the allowed shape now.

### `TokenizerConfig`

Purpose:
- describe the tokenizer/preprocessing behavior as declarative config

Fields:
- `version: str`
- `tokenizer_name: str`
- `normalization: list[str]`
- `split_pattern: str | None`
- `lowercase: bool`
- `stopword_policy: str`
- `language_mode: str`
- `metadata_signature: str`

### `IndexSchema`

Purpose:
- declare indexed fields and compatibility-relevant schema information

Fields:
- `version: str`
- `document_id_field: str`
- `text_fields: list[str]`
- `stored_fields: list[str]`
- `metadata_fields: list[str]`
- `tokenizer_signature: str`
- `schema_signature: str`

### `IndexOpenOptions`

Purpose:
- declare how an existing index should be opened or validated

Fields:
- `index_path: str`
- `create_if_missing: bool`
- `reuse_if_compatible: bool`
- `expected_schema_signature: str`
- `expected_tokenizer_signature: str`
- `read_only: bool`

### `IndexBuildRequest`

Purpose:
- provide all inputs needed to build or rebuild an index without Python callbacks

Fields:
- `index_path: str`
- `schema: IndexSchema`
- `tokenizer: TokenizerConfig`
- `documents: list[DocumentRecord]`
- `rebuild_mode: str`
- `commit_policy: str`

### `DocumentRecord`

Purpose:
- represent a fully materialized document payload crossing into the hot path

Fields:
- `document_id: str`
- `text: str`
- `title: str | None`
- `source_path: str | None`
- `metadata: dict[str, str]`

### `SearchRequest`

Purpose:
- represent a lexical search request or analysis request without runtime callbacks

Fields:
- `index_path: str`
- `query_text: str`
- `top_k: int`
- `filters: dict[str, str]`
- `include_scores: bool`
- `include_explain: bool`
- `include_debug: bool`

### `SearchHit`

Purpose:
- return a single ranked result

Fields:
- `document_id: str`
- `score: float`
- `rank: int`
- `matched_fields: list[str]`
- `highlights: list[str]`
- `metadata: dict[str, str]`

### `AnalyzerOutput`

Purpose:
- expose a stable debug surface for tokenization and preprocessing behavior

Fields:
- `input_text: str`
- `normalized_text: str`
- `tokens: list[str]`
- `token_count: int`
- `tokenizer_signature: str`

### `IndexDiagnostics`

Purpose:
- expose compatibility and execution-path information needed for debugging

Fields:
- `engine_path: str`
- `index_path: str`
- `schema_signature: str`
- `tokenizer_signature: str`
- `compatible: bool`
- `rebuild_required: bool`
- `details: list[str]`

## Allowed boundary operations

The boundary may expose only operations in this family:
- `build_index(IndexBuildRequest) -> IndexDiagnostics`
- `search(SearchRequest) -> list[SearchHit]`
- `analyze(text, TokenizerConfig) -> AnalyzerOutput`
- `describe_index_config(IndexOpenOptions) -> IndexDiagnostics`
- `explain(SearchRequest) -> dict[str, str | list[str] | float]`

## Boundary invariants

1. no Python callback may execute from inside tokenization, indexing, or search loops
2. all hot-path inputs must be available before control enters Rust
3. all hot-path outputs must return as plain result structs
4. tokenizer and schema compatibility must be explicit and inspectable
5. the boundary must remain narrow enough that `abi3` stays plausible for packaging

## Deliverables

1. this API sketch as the canonical Step 5 boundary reference
2. a mapped list from current Python-side concepts to proposed boundary structs
3. a short follow-up note, once profiling is complete, naming which subset of the boundary is actually needed for the first spike

## Acceptance criteria

This sub-step is complete only when all are true:

1. the boundary is explicitly declarative: config in, results out
2. exact request and response structs are named with concrete fields
3. the serialization strategy is defined well enough to implement thin Python wrappers later
4. Python ownership versus Rust ownership is unambiguous
5. no Python callbacks are permitted in the hot loop

## Exit condition for the next sub-step

Packaging policy may assume this boundary shape only if the first Rust spike can stay inside these declarative constraints.
