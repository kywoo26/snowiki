# Step 1: Lexical Foundation Solidification

## Purpose

Lock the lexical retrieval contract, eliminate drift between runtime surfaces, and make policy promotion safe and repeatable.

This step ensures that CLI, daemon, MCP, and benchmark all speak the same retrieval language before any tokenizer or hybrid work begins.

## Why now

The current active retrieval backbone is lexical and deterministic, but the main architecture risk is **drift** between surfaces that should be equivalent. If the foundation is not solid, later work (Korean tokenizer selection, hybrid preparation, wiki skill design) will be built on an unstable substrate.

## Current reality

- `src/snowiki/search/workspace.py` owns the shared retrieval assembly path.
- `src/snowiki/config.py` gates the promoted lexical policy.
- `tests/search/test_runtime_lexical_separation.py` guards against benchmark indexes leaking into runtime assembly.
- Explicit rebuild and hard-fail-on-mismatch behavior are already documented and partially enforced.

However, edge-case parity gaps may still exist between CLI `recall`, daemon `/query`, and MCP `search`/`recall` under policy changes or cache invalidation races.

## Scope

In scope:
- Parity verification across CLI, daemon, and MCP for the same query intent.
- Hardening the explicit rebuild / mismatch / hard-fail path.
- Documenting and automating the lexical-policy promotion gate.
- Enforcing the benchmark/runtime boundary so benchmark baselines cannot silently become runtime truth.

Out of scope (covered in later steps):
- Integrating a new tokenizer (Step 2).
- Semantic/vector implementation (Step 4).
- Backend replacement (Step 5).

## Non-goals

- Do not add semantic or vector retrieval.
- Do not swap the backend engine.
- Do not relax the benchmark/runtime separation.

## Dependencies

None. This is the foundation step for all subsequent work.

## Risks

| Risk | Mitigation |
| :--- | :--- |
| Over-invest in lexical-only perfection without forward compatibility | Design tests and abstractions so the contract can absorb new tokenizers and later hybrid modes without rewrites. |
| Under-invest and leave hidden drift | Add automated parity diff tests that compare result structures and routing decisions across surfaces. |

## Deliverables

1. **Parity test suite** covering CLI / daemon / MCP alignment for lexical retrieval.
2. **Documented promotion gate** that is executable, not just prose.
3. **Zero silent benchmark-to-runtime leakage** enforced by tests and CI.

## TDD and verification plan

1. Write failing parity/regression tests for CLI/MCP/daemon lexical contract alignment.
2. Fix the drift; keep tests green.
3. Verify with:
   - `uv run pytest tests/search/test_runtime_lexical_separation.py`
   - `uv run pytest tests/cli/test_rebuild.py`
   - `uv run pytest tests/cli/test_query.py`
   - New governance test: `tests/governance/test_retrieval_surface_parity.py`

## Promotion criteria to `.sisyphus/plans/`

This step graduates to execution when:
- All active retrieval surfaces produce identical strategy routing and result structures for the same inputs.
- The promotion gate can be run as a script or test suite, not just read as documentation.
- No benchmark-only path can reach runtime assembly without an explicit, auditable promotion action.

## Reference citations

- `docs/architecture/current-retrieval-architecture.md` — canonical runtime contract and seam definitions.
- `tests/search/test_runtime_lexical_separation.py` — regression guard against benchmark leakage.
- `docs/reference/architecture/retrieval-decision-matrix.md` — framework for retrieval strategy choices and gating.
- `docs/roadmap/archive/follow-up-program.md` — predecessor that identified search architecture hardening as the next layer.

## Open questions

- Should we add a formal **contract diff** tool that compares two surfaces for the same query and reports structural or semantic drift?
- How aggressively should we unify daemon cache invalidation with CLI rebuild semantics?
