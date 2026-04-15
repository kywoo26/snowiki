# Step 5: Rust Core Migration Path

## Purpose

Define when and how to move proven hot paths from Python to a Rust extension, without destabilizing the runtime contract or harming install ergonomics.

## Why now

Long-term performance and stability may justify native acceleration, but only after the boundaries are proven in Python. Premature migration risks packaging complexity and contract drift. This step sets the decision criteria and boundary design so that the migration is evidence-driven.

## Current reality

- `docs/reference/architecture/rust-native-acceleration-roadmap.md` already defines gating criteria and boundary guidance.
- No Rust code exists in the Snowiki runtime yet.
- The current Python implementation is fast enough for the current workload; hotspots have not been conclusively identified.

## Scope

In scope:
- Identify and rank candidate hot paths (tokenization, indexing, fusion, query parsing).
- Define the PyO3 / maturin boundary API: what data crosses the boundary, how config is serialized, and how Rust owns index state.
- Specify packaging tradeoffs (manylinux, Windows/macOS ABI, developer experience, stub generation).
- Set the profiling evidence threshold that triggers a Rust spike.

Out of scope:
- Rewriting the entire engine in Rust.
- Moving orchestration, CLI, config parsing, or skill logic to Rust.
- Daemonizing the core before an extension proof is successful.

## Non-goals

- Do not start a Rust rewrite without CPU-bound profiling evidence.
- Do not move Python-side contract or agent-facing logic to Rust.
- Do not force users to install a Rust toolchain to use Snowiki.

## Dependencies

- **Step 1** must be complete so that boundaries are stable.
- **Step 4** is strongly recommended so that hybrid boundaries clarify what truly belongs in the hot path.

## Risks

| Risk | Mitigation |
| :--- | :--- |
| Premature Rust migration destabilizes the contract | Require profiling evidence + stable Python contract before any spike. |
| Packaging complexity harms install ergonomics | Start with `maturin` wheels; test on Linux, macOS, and Windows CI. |
| Boundary API churn wastes effort | Design the serialized schema/config boundary first; keep live Python callbacks out of the hot loop. |

## Deliverables

1. **Rust migration decision record** (`rust-migration-decision-record.md`) with:
   - Candidate hot path ranking and rationale.
   - Boundary API sketch (config in, results out).
   - Packaging and CI tradeoff analysis.
2. **Profiling baseline** showing the exact Python functions that consume the most CPU during realistic workloads.

## TDD and verification plan

1. Capture profiling evidence with `uv run snowiki benchmark --preset retrieval`.
2. Confirm that Python-level optimization cannot close the gap.
3. Only then write a Rust extension prototype for the single hottest path.
4. Verify the prototype with:
   - Functional parity tests against the Python implementation.
   - `maturin build` passing on target platforms.
   - No regression in CLI startup time or install size.

## Promotion criteria to `.sisyphus/plans/`

This step graduates to execution when:
- A single hot path is proven CPU-bound under realistic workloads.
- Its Python contract is stable (no API changes expected for 2+ release cycles).
- A Rust extension prototype matches or beats the Python implementation.
- Packaging does not add friction for end users (wheels available, no Rust toolchain required).

## Reference citations

- `docs/reference/architecture/rust-native-acceleration-roadmap.md` — existing gating criteria and deferred rationale inside Snowiki.
- `vlwkaos/ir` — Rust implementation of a qmd-like retrieval engine, demonstrating how tokenization, indexing, BM25, vector search, and hybrid fusion can live in Rust while exposing CLI and MCP surfaces. [`Cargo.toml`](https://github.com/vlwkaos/ir/blob/main/Cargo.toml) · [`src/search/hybrid.rs`](https://github.com/vlwkaos/ir/blob/main/src/search/hybrid.rs)
- `huggingface/tokenizers` — proven pattern of Rust core + Python bindings via PyO3/maturin, with stub generation for typing support. [CONTRIBUTING](https://github.com/huggingface/tokenizers/blob/main/CONTRIBUTING.md) · [Python bindings README](https://github.com/huggingface/tokenizers/blob/main/bindings/python/README.md)
- `quickwit-oss/tantivy-py` — Rust search index owned by Python config: schema, path, and reuse flags cross the boundary as declarative values. [`src/index.rs`](https://github.com/quickwit-oss/tantivy-py/blob/main/src/index.rs)
- `ParadeDB` — backward-compatible tokenizer/schema behavior while evolving the Tantivy-backed core. [`pg_search/src/schema/mod.rs`](https://github.com/paradedb/paradedb/blob/main/pg_search/src/schema/mod.rs) · [`pg_search/src/index/search.rs`](https://github.com/paradedb/paradedb/blob/main/pg_search/src/index/search.rs)

## Open questions

- Which hot path is the best first candidate: **tokenizer**, **indexer**, or **fusion loop**?
- Should we maintain a **dual-stack** (Python + Rust) for a transition period, or cut over atomically?
- How do we handle **debuggability** when the core is in Rust and the agent/skill logic is in Python?
