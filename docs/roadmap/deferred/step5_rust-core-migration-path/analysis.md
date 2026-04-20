# Step 5 Analysis: Rust Core Migration Path

## Executive Summary

Snowiki should treat Rust as an **extension-first hot-path acceleration strategy**, not as a product rewrite. The strongest pattern across `vlwkaos/ir`, `huggingface/tokenizers`, `tantivy-py`, and ParadeDB is consistent:

1. Keep orchestration, contracts, and workflow control in Python.
2. Move **stable, CPU-bound kernels** into Rust.
3. Cross the boundary with **declarative config and plain result structs**, not Python callbacks.
4. Persist tokenizer/schema compatibility as index metadata.
5. Preserve a **dual-stack fallback** so the Python path remains available for debugging, parity checks, and packaging failures.

This means Snowiki's first Rust candidate is most likely **tokenization / indexing / lexical-search infrastructure**, not hybrid orchestration, skill logic, or CLI control flow.

---

## 1. What Step 5 needs to answer

`docs/roadmap/step5_rust-core-migration-path/roadmap.md` asks for five concrete decisions:

1. Which Python hot path should move first?
2. What should cross the Python↔Rust boundary?
3. What packaging/wheel strategy keeps installation ergonomic?
4. How should typed stubs be handled?
5. What compatibility/debuggability rules are required so native acceleration does not destabilize the runtime contract?

This analysis answers those questions from external evidence.

---

## 2. External reference findings

### 2.1 `vlwkaos/ir`

**What it shows**
- Rust can own the full retrieval hot path while still exposing higher-level CLI/MCP surfaces externally.
- Per-collection state, preprocessors, chunking, vector storage, daemon warming, and hybrid search all live in Rust.

**Key files**
- `/home/k/local/ir/src/search/hybrid.rs`
- `/home/k/local/ir/src/preprocess.rs`
- `/home/k/local/ir/src/index/mod.rs`
- `/home/k/local/ir/src/types.rs`
- `/home/k/local/ir/src/config/mod.rs`
- `/home/k/local/ir/src/db/schema_base.sql`

**Lessons for Snowiki**
- Rust should own **search kernels and persisted index state**, not workflow behavior.
- Tokenizer/preprocessor changes should be treated as **index-compatibility events** that trigger rebuild.
- Cold model loading is operationally expensive; if Snowiki ever moves dense work native, it should follow a warmed/daemonized path rather than loading heavyweight models inside the default CLI loop.

### 2.2 `huggingface/tokenizers`

**What it shows**
- A mature mixed Python+Rust package can ship broad wheels with `maturin`, keep a clean Python package surface, and use `abi3` to reduce wheel explosion.

**Key files**
- `https://github.com/huggingface/tokenizers/blob/main/bindings/python/pyproject.toml`
- `https://github.com/huggingface/tokenizers/blob/main/bindings/python/Cargo.toml`
- `https://github.com/huggingface/tokenizers/blob/main/.github/workflows/python-release.yml`
- `https://github.com/huggingface/tokenizers/blob/main/bindings/python/README.md`

**Lessons for Snowiki**
- Prefer a **mixed project layout**: Python package wrappers + compiled Rust extension.
- Prefer **`abi3`** if the native API can remain narrow enough.
- Their custom stub-generation pipeline exists because the API surface is huge; Snowiki does not need that complexity for a first spike.

### 2.3 `tantivy-py`

**What it shows**
- Python can expose a clean declarative API over a Rust-owned index/search engine.
- Schema, writer, searcher, tokenizer registration, and parsing stay Rust-owned, while Python passes plain values.

**Key files**
- `https://github.com/quickwit-oss/tantivy-py/blob/master/src/index.rs`
- `https://github.com/quickwit-oss/tantivy-py/blob/master/src/schemabuilder.rs`
- `https://github.com/quickwit-oss/tantivy-py/blob/master/src/tokenizer.rs`
- `https://github.com/quickwit-oss/tantivy-py/blob/master/tantivy/tantivy.pyi`
- `https://github.com/quickwit-oss/tantivy-py/blob/master/tantivy/py.typed`
- `https://github.com/quickwit-oss/tantivy-py/blob/master/.github/workflows/publish.yaml`
- `https://github.com/quickwit-oss/tantivy-py/blob/master/README.md`

**Lessons for Snowiki**
- Boundary APIs should be **config in / results out**.
- Checked-in `.pyi` + `py.typed` are good enough for a small-to-medium native surface.
- Wheels matter: their source-build fallback is acceptable for a library, but Snowiki should aim for a smoother wheels-first user experience.

### 2.4 ParadeDB

**What it shows**
- Tokenizer behavior must be treated as **persisted schema/config**, not an incidental runtime detail.
- Rust search systems often need explicit tokenizer re-registration and backward-compatibility logic when indexes reopen.

**Key files**
- `https://github.com/paradedb/paradedb/blob/main/pg_search/src/schema/config.rs`
- `https://github.com/paradedb/paradedb/blob/main/pg_search/src/schema/mod.rs`
- `https://github.com/paradedb/paradedb/blob/main/pg_search/src/index/search.rs`
- `https://github.com/paradedb/paradedb/pull/375`
- `https://github.com/paradedb/paradedb/pull/1583`
- `https://github.com/paradedb/paradedb/issues/1499`

**Lessons for Snowiki**
- Tokenizer chains must be versioned and stored in index metadata.
- Reopening an index should validate tokenizer compatibility explicitly.
- Debug surfaces matter because opaque native search state becomes hard to reason about otherwise.

---

## 3. Candidate hot-path ranking for Snowiki

### Tier 1 — best first candidates

1. **Tokenizer / preprocessing path**
   - Most stable contract.
   - Already central to Step 2.
   - Strong evidence from `tokenizers`, `ir`, and ParadeDB.

2. **Index construction / lexical indexing path**
   - Likely CPU-bound on larger corpora.
   - Clear config-boundary candidate.
   - Fits the `tantivy-py` / `ir` pattern well.

3. **Lexical search kernel**
   - Worth considering after indexing/tokenization if profiling shows repeated CPU pressure.

### Tier 2 — defer until later

4. **Hybrid fusion loop / RRF kernel**
   - Small enough that Python may remain sufficient.
   - Only worth native migration if benchmark evidence shows it dominates runtime.

5. **Rerank orchestration / model lifecycle**
   - Operational complexity is the bigger problem, not raw Python overhead.
   - Likely should remain Python-controlled even if some kernels become native.

### Tier 3 — do not move first

6. **CLI orchestration**
7. **MCP adapter layer**
8. **Skill/workflow logic**
9. **Provenance handling and roadmap logic**

These belong in Python per Snowiki's current contract posture.

---

## 4. Boundary API recommendation

Snowiki should design future native boundaries around small immutable structs.

### Proposed request/response surface

```text
TokenizerConfig
IndexSchema
IndexOpenOptions
IndexBuildRequest
SearchRequest
SearchHit[]
AnalyzerOutput
IndexDiagnostics
```

### Boundary rules

- Python provides configuration, file paths, and text payloads.
- Rust returns tokens, hits, diagnostics, and index metadata.
- No Python callback should run inside the hot loop.
- Tokenizer configuration and index signatures must be persisted as metadata.

### Why this is the right shape

- Matches `tantivy-py`'s declarative API style.
- Matches ParadeDB's schema/tokenizer persistence requirements.
- Matches `ir`'s separation between config, index state, and runtime search.

---

## 5. Packaging and wheel policy

### Recommended posture

- Use **PyO3 + maturin**.
- Ship a **mixed Python+Rust package**.
- Prefer **`abi3`** if feasible.
- Do **not** require end users to install a Rust toolchain.

### Why

- `tokenizers` shows the cleanest mature packaging path.
- `tantivy-py` demonstrates that source-build fallback exists, but Snowiki should avoid making that the default user experience.

### Practical requirement for Snowiki

The first native prototype should be judged not only on speed but also on:
- Linux/macOS/Windows wheel viability
- install size
- CLI startup impact
- local developer ergonomics

---

## 6. Type-stub strategy

### Recommended first approach

- Keep Python wrappers thin.
- Check in manual `.pyi` files.
- Include `py.typed`.

### Why

- `tantivy-py` proves this is sufficient for a moderate API surface.
- Snowiki does not need `tokenizers`-style custom stub generation unless the native API grows substantially.

---

## 7. Compatibility, fallback, and debug requirements

Any Snowiki Rust prototype should ship with these rules from day one:

1. **Dual-stack path**
   - Native path and pure-Python path must coexist initially.
   - Users and tests need a force-Python override.

2. **Index metadata versioning**
   - Store tokenizer signature, config version, and schema signature.
   - Any mismatch forces rebuild rather than silent reuse.

3. **Explicit debug surfaces**
   - `analyze(text)`
   - `explain(query)`
   - `describe_index_config()`
   - diagnostics about which path executed (Python vs Rust)

4. **Graceful fallback**
   - If the Rust extension fails to load, Snowiki must continue on the Python path.
   - Failure should be visible in diagnostics, not hidden.

These requirements are strongly supported by ParadeDB's compatibility work and by the inspection-friendly APIs in `tantivy-py`.

---

## 8. Answers to Step 5 open questions

### Which hot path is the best first candidate?

**Answer:** tokenizer / preprocessing first, indexing second, lexical-search third.

### Dual-stack or atomic cutover?

**Answer:** dual-stack transition first. Atomic cutover is too risky before parity and packaging confidence exist.

### How do we preserve debuggability?

**Answer:** require analyzer/explain/config-inspection surfaces and a force-Python fallback mode.

---

## 9. What this means for Snowiki's next documentation layer

Before any Rust implementation plan is promoted into `.sisyphus/plans/`, Snowiki should still add:

1. `rust-migration-decision-record.md`
2. `profiling-baseline.md`

The first should formalize the chosen candidate path and boundary. The second should prove the Python hotspot exists under realistic workloads.

---

## Bottom line

Rust is justified for Snowiki only when a hotspot is both **real** and **stable**. The external evidence strongly suggests that Snowiki's first native boundary should be:

- narrow,
- declarative,
- tokenizer/index-centered,
- wheel-first,
- dual-stack,
- and versioned against tokenizer/schema metadata.

That is the migration path most compatible with Snowiki's current CLI-first and contract-first posture.
