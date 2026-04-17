## Problem / Motivation
<!-- Why this change? Quantify if possible (e.g., "query latency is 3x slower with >10k docs"). -->

## Proposed Change
<!-- What changes at the contract/surface level? A reviewer should understand the impact without reading the diff. -->

## Alternatives Considered
<!-- What else did you consider and why was it rejected? Skip for trivial changes. -->

## Surfaces Touched
<!-- Check all that apply based on your change scope: -->
- [ ] CLI
- [ ] Search / Retrieval
- [ ] Storage / Index
- [ ] Skill / Agent
- [ ] Docs
- [ ] CI / Build
- [ ] Benchmarks

## Verification
<!-- Run the subset from AGENTS.md that matches your surfaces. -->

**Always:**
- [ ] `uv run ruff check src/snowiki tests`
- [ ] `uv run ty check`
- [ ] `uv run pytest`
- [ ] `uv run pytest -m integration`

**If search / retrieval / perf related:**
- [ ] `uv run snowiki benchmark --preset retrieval --output reports/retrieval.json`

## Contract Sync
<!-- If you changed a surface, did you update its mirror? -->
- [ ] N/A (no surface change)
- [ ] AGENTS.md updated (rule / process change)
- [ ] skill/SKILL.md updated (skill interface change)
- [ ] docs/architecture/ updated (architecture change)

## Risks / Rollback
<!-- Breaking changes? Migration notes? Performance regressions? Skip if none. -->
