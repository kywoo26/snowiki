# Step 1 Analysis Notes

## Current test posture

### What is already guarded
- `tests/search/test_runtime_lexical_separation.py`
  - Asserts that `RetrievalService.from_records_and_pages` uses runtime lexical builders, not benchmark BM25 indexes.
  - Asserts that `SnowikiReadOnlyFacade` uses the same runtime assembly and does not promote benchmark baselines.
- These are **negative guards** (what must NOT happen).

### What is missing (positive parity)
- No test directly compares CLI `query` output, MCP `search` tool output, and daemon `/query` response for the **same query intent** against the **same data**.
- No automated diff exists for result ordering, score shapes, or field presence across the three surfaces.
- No test verifies that `recall` routing decisions (temporal vs known-item vs topical) are identical across CLI, MCP, and daemon.

## Identified drift risks

1. **Query mode interpretation**
   - CLI exposes `--mode [lexical|hybrid]` but currently forces `semantic_backend=None` for `lexical`.
   - MCP exposes `search` tool without an explicit mode flag; it always uses the current runtime policy.
   - If policy promotion semantics differ, results diverge silently.

2. **Rebuild / cache invalidation timing**
   - CLI `rebuild` is synchronous and explicit.
   - Daemon `warm_index.py` and `cache.py` may serve stale snapshots until invalidation triggers.
   - No cross-surface test validates snapshot freshness after an ingest.

3. **Hit payload shape**
   - `tests/cli/test_query.py` asserts JSON structure for CLI hits.
   - `tests/mcp/test_search.py` asserts `structuredContent` shape for MCP hits.
   - The two shapes are similar but not guaranteed identical by a single test.

## Recommended next actions for this step

1. Add `tests/governance/test_retrieval_surface_parity.py`
   - Build a single fixture dataset.
   - Run the same query through CLI `query`, MCP `search`, and daemon search.
   - Assert identical hit ordering, path sets, and score normalization within a tolerance.
2. Harden the explicit-rebuild contract with an automated test that fails if benchmark index paths are reachable from runtime assembly (extend current negative guards).
3. Document the promotion gate as a script (`scripts/promote_lexical_policy.py`) that checks benchmark victory + runtime safety + parity proof, rather than a manual checklist.

## File references
- `tests/search/test_runtime_lexical_separation.py` — negative guards
- `tests/cli/test_query.py` — CLI functional tests
- `tests/mcp/test_search.py` — MCP functional tests
- `src/snowiki/search/workspace.py` — runtime assembly seam
- `src/snowiki/mcp/server.py` — MCP facade seam
