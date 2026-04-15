# Step 1: Lexical Foundation

## Goal

Lock the lexical retrieval contract so the current lexical runtime is deterministic, parity-tested across CLI, MCP, and daemon surfaces, protected from benchmark leakage, and gated by an executable promotion check.

## Non-Goals

- Do not change tokenization or add a tokenizer-selection path.
- Do not add or enable hybrid, semantic, vector, or rerank retrieval.
- Do not replace the retrieval backend.
- Do not expand MCP beyond its current read-only contract.
- Do not redesign daemon lifecycle, cache topology, or automatic root hydration.
- Do not change skill or workflow surfaces.

## Scope Boundaries

- In scope: direct lexical search parity for CLI `query`, MCP `search`, and daemon `/query` using the direct topical path.
- In scope: recall routing parity for CLI `recall`, MCP `recall`, and daemon `/query` with `operation=recall`.
- In scope: explicit rebuild, stale-state, and mismatch verification for the lexical runtime contract.
- In scope: executable lexical promotion gate that fails closed.
- In scope: benchmark/runtime boundary enforcement so benchmark code cannot become runtime truth without an explicit promotion action.
- Out of scope: new retrieval strategies, benchmark ranking changes, skill behavior changes, and host-level policy expansion.

## TDD Execution Model

1. Add failing parity tests first.
2. Refactor runtime surfaces onto one lexical contract seam until the new parity tests pass.
3. Add failing mismatch and promotion-gate tests.
4. Implement strict rebuild and promotion checks until the new tests pass.
5. Run targeted verification after each commit and full verification at the end.

## Deliverables

### Files to Create

- `.sisyphus/plans/step1_lexical-foundation.md`
- `src/snowiki/search/contract.py`
- `tests/governance/test_retrieval_surface_parity.py`
- `scripts/promote_lexical_policy.py`
- `tests/governance/test_lexical_policy_promotion.py`

### Files to Modify

- `src/snowiki/search/__init__.py`
- `src/snowiki/cli/commands/query.py`
- `src/snowiki/cli/commands/recall.py`
- `src/snowiki/mcp/server.py`
- `src/snowiki/daemon/server.py`
- `src/snowiki/daemon/warm_index.py`
- `src/snowiki/cli/commands/rebuild.py`
- `src/snowiki/rebuild/integrity.py`
- `tests/cli/test_query.py`
- `tests/mcp/test_search.py`
- `tests/daemon/test_warm_index.py`
- `tests/daemon/test_fallback_integration.py`
- `tests/cli/test_rebuild.py`
- `tests/rebuild/test_integrity.py`

## Deliverable Intent

- `src/snowiki/search/contract.py`: one canonical lexical contract seam for recall strategy resolution and shared hit-shape normalization used by CLI, MCP, and daemon.
- `tests/governance/test_retrieval_surface_parity.py`: one governance suite that proves parity across surfaces using the same dataset and the same query intents.
- `src/snowiki/daemon/warm_index.py`, `src/snowiki/cli/commands/rebuild.py`, `src/snowiki/rebuild/integrity.py`: explicit stale-state and rebuild verification surface for strict checks.
- `scripts/promote_lexical_policy.py`: one executable gate that runs the lexical promotion proof and exits non-zero on any drift, mismatch, or boundary violation.
- `tests/governance/test_lexical_policy_promotion.py`: one test that freezes the gate contract and its fail-closed behavior.

## Acceptance Criteria

- Pass: `tests/governance/test_retrieval_surface_parity.py` proves that CLI `query`, MCP `search`, and daemon `/query` direct topical retrieval return the same ordered hit identities for the same query against the same fixture dataset.
- Fail: any direct-search surface returns a different ordered `id` or `path` list, omits required identity fields, or uses a different lexical retrieval path.

- Pass: `tests/governance/test_retrieval_surface_parity.py` proves that CLI `recall`, MCP `recall`, and daemon `/query` with `operation=recall` choose the same strategy for `date`, `temporal`, `known_item`, and `topic` inputs.
- Fail: any recall surface chooses a different strategy or returns a different ordered hit identity list for the same intent.

- Pass: MCP `search` remains a direct search tool and does not adopt recall auto-routing.
- Fail: parity is achieved by widening MCP `search` into a recall router.

- Pass: daemon diagnostics continue to expose freshness state, and strict verification fails when served snapshot identity does not match current content identity.
- Fail: stale or mismatched state is only logged or implied and still passes strict verification.

- Pass: `tests/search/test_runtime_lexical_separation.py` still proves runtime lexical assembly does not instantiate benchmark BM25 indexes or benchmark promotion paths.
- Fail: runtime assembly reaches benchmark-only builders, baselines, or promotion paths.

- Pass: `scripts/promote_lexical_policy.py --strict` exits `0` only when parity, rebuild integrity, freshness checks, and runtime-boundary tests all pass.
- Fail: the promotion gate exits `0` while parity drift, stale-state mismatch, or benchmark/runtime leakage still exists.

- Pass: all listed verification commands succeed with `uv run`.
- Fail: any required command fails or requires manual interpretation beyond documented exit status.

## Verification Commands

- `uv run pytest tests/search/test_runtime_lexical_separation.py`
- `uv run pytest tests/cli/test_query.py`
- `uv run pytest tests/mcp/test_search.py`
- `uv run pytest tests/daemon/test_warm_index.py`
- `uv run pytest tests/cli/test_rebuild.py`
- `uv run pytest tests/rebuild/test_integrity.py`
- `uv run pytest tests/governance/test_retrieval_surface_parity.py`
- `uv run pytest tests/governance/test_lexical_policy_promotion.py`
- `uv run pytest tests/daemon/test_fallback_integration.py -m integration`
- `uv run ruff check src/snowiki tests scripts`
- `uv run ty check`
- `uv run python scripts/promote_lexical_policy.py --strict`

## Atomic Commit Plan

1. `test: add lexical retrieval surface parity governance coverage`
   - Create `tests/governance/test_retrieval_surface_parity.py`.
   - Extend `tests/cli/test_query.py` with frozen parity expectations for CLI query and recall payloads.
   - Extend `tests/mcp/test_search.py` with frozen parity expectations for MCP search and recall payloads.
   - Extend `tests/daemon/test_warm_index.py` and `tests/daemon/test_fallback_integration.py` with parity-focused daemon assertions.
   - Expected state: new tests fail because the contract is still duplicated and shape-drift still exists.
   - Verification: run the new governance test and the touched targeted tests.

2. `refactor: centralize lexical routing and hit contract`
   - Create `src/snowiki/search/contract.py`.
   - Export the shared contract from `src/snowiki/search/__init__.py`.
   - Modify `src/snowiki/cli/commands/query.py`, `src/snowiki/cli/commands/recall.py`, `src/snowiki/mcp/server.py`, and `src/snowiki/daemon/server.py` to consume the shared routing and hit-shape seam.
   - Keep MCP `search` as direct search and keep CLI `recall` as the routing authority mirrored by MCP and daemon.
   - Expected state: parity tests pass without changing step scope.
   - Verification: run `tests/cli/test_query.py`, `tests/mcp/test_search.py`, `tests/daemon/test_warm_index.py`, and `tests/governance/test_retrieval_surface_parity.py`.

3. `fix: harden explicit rebuild and freshness mismatch verification`
   - Modify `src/snowiki/daemon/warm_index.py` to expose the strict mismatch facts needed by the gate.
   - Modify `src/snowiki/cli/commands/rebuild.py` and `src/snowiki/rebuild/integrity.py` so explicit rebuild verification produces deterministic lexical readiness facts.
   - Extend `tests/cli/test_rebuild.py`, `tests/rebuild/test_integrity.py`, and `tests/daemon/test_warm_index.py` so stale or mismatched state fails strict checks until explicit rebuild or reload occurs.
   - Expected state: mismatch and rebuild semantics are executable and fail closed.
   - Verification: run rebuild, warm-index, and integrity tests.

4. `feat: add executable lexical promotion gate`
   - Create `scripts/promote_lexical_policy.py`.
   - Create `tests/governance/test_lexical_policy_promotion.py`.
   - The script must run the Step 1 lexical gate checks and return a strict exit code.
   - Expected state: one command proves Step 1 promotion readiness.
   - Verification: run the new governance test, `uv run python scripts/promote_lexical_policy.py --strict`, then `uv run ruff check src/snowiki tests scripts` and `uv run ty check`.

## Risks And Mitigation

| Risk | Mitigation |
| :--- | :--- |
| Parity tests freeze accidental surface quirks instead of the intended contract. | Define parity around authoritative routing, hit identity, required metadata fields, and direct-vs-recall boundary before refactoring. |
| Shared contract refactor widens scope into hybrid or broader search redesign. | Limit the new seam to lexical routing and hit normalization only. Do not add new retrieval modes or engine abstractions. |
| Daemon stale-state handling turns into auto-reload work. | Keep normal daemon behavior explicit and visible. Apply hard-fail only to strict verification and promotion paths. |
| Promotion gate becomes a second undocumented policy source. | Make the script a thin executable wrapper around the tested lexical contract and keep its checks aligned with the governance tests. |
| Benchmark evidence leaks into runtime truth through convenience reuse. | Keep runtime lexical separation tests mandatory in the gate and reject any benchmark-only builder in runtime assembly. |

## Dependencies

- External dependency changes: none.
- Roadmap dependency: none. Step 1 is the foundation step.
- Internal prerequisites already present:
- `docs/roadmap/step1_lexical-foundation/roadmap.md`
- `docs/roadmap/step1_lexical-foundation/analysis.md`
- `docs/architecture/current-retrieval-architecture.md`
- `tests/search/test_runtime_lexical_separation.py`
- `tests/cli/test_query.py`
- `tests/mcp/test_search.py`
- `tests/daemon/test_warm_index.py`
- `tests/daemon/test_fallback_integration.py`
- Toolchain dependency: `uv`, `pytest`, `ruff`, and `ty` already defined in repo policy.
- Explicit constraint: no `pyproject.toml` dependency changes in this step.

## Done Definition

Step 1 is done when:

- lexical routing and hit shape are proven equivalent across CLI, MCP, and daemon for the covered direct-search and recall intents;
- stale-state and rebuild mismatch are surfaced as explicit machine-checked failures in strict verification;
- benchmark/runtime separation remains enforced;
- one strict promotion command proves readiness without manual interpretation;
- all work lands in the four atomic commits above.
