# Rust Migration Decision Record

## Status

**Provisional roadmap decision record** — this is not implementation approval.

The purpose of this record is to pin the current decision posture so later Prometheus/Atlas work starts from explicit constraints instead of re-deriving them.

---

## Decision

Snowiki will pursue **extension-first Rust acceleration** only after profiling confirms a stable CPU-bound hotspot.

The current preferred migration order is:

1. tokenizer / preprocessing
2. index construction / lexical indexing
3. lexical search kernel

Snowiki will **not** begin with:

- CLI orchestration
- MCP bridge logic
- skill/workflow logic
- provenance handling
- hybrid orchestration as a whole

---

## Why this is the current decision

This direction is supported by:

- `docs/roadmap/step5_rust-core-migration-path/analysis.md`
- `docs/reference/architecture/rust-native-acceleration-roadmap.md`
- `vlwkaos/ir` as a Rust retrieval-core reference
- `huggingface/tokenizers` as the strongest mixed-package + wheel strategy reference
- `tantivy-py` as the clearest Python-facing declarative boundary reference
- ParadeDB as the strongest schema/tokenizer-compatibility cautionary reference

---

## Boundary decision

The future Python↔Rust boundary should remain **declarative and narrow**.

### Preferred boundary objects

- `TokenizerConfig`
- `IndexSchema`
- `IndexOpenOptions`
- `IndexBuildRequest`
- `SearchRequest`
- `SearchHit[]`
- `AnalyzerOutput`
- `IndexDiagnostics`

### Boundary rules

- Python owns orchestration and user-facing contracts.
- Rust owns CPU-intensive kernels and persistent native index state.
- No Python callback should execute inside the hot loop.

---

## Packaging decision

### Current preferred posture

- PyO3 + maturin
- mixed Python+Rust package
- wheels-first UX
- prefer `abi3` if feasible
- no Rust toolchain requirement for end users

### Why

This best matches Snowiki's local-first CLI ergonomics and avoids making native acceleration a deployment burden.

---

## Type information decision

### Current preferred posture

- checked-in `.pyi`
- `py.typed`
- thin Python wrappers over native objects

Snowiki should avoid a custom stub-generation pipeline unless the native API grows much larger than currently expected.

---

## Fallback and safety decision

The first native prototype must support:

1. pure-Python fallback
2. index metadata versioning
3. rebuild-on-tokenizer-signature-change
4. explicit diagnostics about whether the Python or Rust path executed
5. debug surfaces such as `analyze(text)`, `explain(query)`, and `describe_index_config()`

---

## What would change this decision

The preferred first candidate could change only if profiling shows that:

- tokenization is not the dominant persistent hotspot, and
- another boundary is both measurably hotter and just as contract-stable.

---

## What is still required before implementation approval

1. `profiling-baseline.md` filled with real benchmark/profile evidence
2. evidence that Python-level optimization does not sufficiently close the gap
3. an execution-ready `.sisyphus/plans/rust-core-migration-path.md`

Until then, this remains a roadmap decision record, not a go-ahead for implementation.
