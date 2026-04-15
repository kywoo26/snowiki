# ROADMAP

This file tracks strategic work that is likely to matter over multiple PRs.

- **Use this file for**: medium/long-term direction, major initiatives, and backlog items that are not yet broken down for immediate execution.
- **Do not use this file for**: execution-ready task lists. Those belong in `.sisyphus/plans/*.md`.

## Current State

Recently completed foundation work:
- governance and path-contract cleanup
- test suite split into fast unit vs explicit integration paths
- migration to standard `src/snowiki/` package layout
- first retrieval performance deep dive
- canonical retrieval service hardening
- manual benchmark workflow ergonomics

The repository is now in a better state to take on larger product and performance work without layout/policy churn.

## Near-Term

### 1. Korean and mixed-language lexical benchmark
Measure and improve Korean and mixed-language retrieval as a lexical/tokenization problem before escalating into semantic or hybrid retrieval.

Why:
- Korean retrieval is still an unresolved lexical/tokenization question
- mixed-language retrieval is likely to be one of Snowiki’s highest-value differentiators
- lexical strategy should be exhausted before semantic escalation

Likely scope:
- benchmark the current tokenizer against Kiwi-backed alternatives
- compare noun-heavy vs broader morphology tradeoffs
- produce a clear lexical strategy for Korean and mixed Korean-English retrieval

### 2. Skill contract and agent interface design
Rebuild the Snowiki skill layer as a first-class agent interface instead of letting old qmd-oriented workflow text drift away from the shipped runtime.

Why:
- the current install/use contract is now aligned, but the skill layer still needs first-class design work rather than patch-level cleanup
- a good skill is not just usage text; it is an agent contract covering content selection, token budget, tool coupling, front matter, and workflow composability
- Snowiki needs a clear answer for what belongs in the CLI, MCP, skill layer, or roadmap

Deferred because:
- the immediate priority was fixing the current install/use contract mismatch so other sessions do not misunderstand the runtime
- deeper skill redesign should follow deliberate research, not incremental patching

Likely scope:
- Claude/OpenCode/OMO skill contract comparison
- front matter / metadata / token-budget rules
- directory structure and canonical-owner rules for skill docs
- agent-facing output contracts and workflow semantics
- runtime-truth vs deferred-work boundaries

Pull-forward trigger:
- skill docs and runtime drift again after the current alignment PR
- multiple agent platforms need divergent wrappers over the same runtime
- the team is ready to treat skill ergonomics as a first-class product surface

### 3. Coverage governance ratchet
Move from report-only coverage visibility toward a non-regression model once a stable baseline is observed.

Why:
- local/CI policy is now clearer
- coverage should become more actionable without becoming noisy or blocking prematurely

Deferred because:
- current effort is focused on performance and retrieval behavior, not coverage governance
- baseline observation still needs time after the recent unit/integration/src-layout changes

Likely scope:
- baseline observation
- non-regression threshold policy
- changed-area testing expectations for new logic

Pull-forward trigger:
- coverage reports stabilize across several PRs
- regressions begin slipping in despite report-only visibility
- changed-area testing expectations need stronger enforcement

### 4. Test taxonomy audit
Continue checking that slow or real-engine tests are correctly classified as integration tests.

Why:
- the unit/integration split is in place, but taxonomy drift can return over time

Deferred because:
- the highest-value test work just landed and now needs time to prove where drift still exists
- the next performance plan should not broaden into another full taxonomy cleanup unless profiling shows it is necessary

Likely scope:
- audit remaining borderline tests
- tighten markers and naming conventions where needed
- keep default unit loop fast

Pull-forward trigger:
- new slow tests start appearing in the default unit loop
- integration behavior leaks back into unit files
- profiling repeatedly points to misclassified tests rather than runtime code

### 5. Benchmark workflow ergonomics (beyond the current manual trigger)
Build on top of the current manual benchmark workflow without turning benchmarks into a default PR hard gate.

Why:
- benchmark command exists and the first manual workflow is now in place
- perf-sensitive work benefits from reproducible shared runs in GitHub Actions

Deferred because:
- current priority is still retrieval quality and architecture, not benchmark UX polish
- broader benchmark automation should follow measured optimization work, not lead it

Likely scope:
- richer artifact/report ergonomics
- better shared benchmark review flow
- selective benchmark execution patterns beyond the current manual trigger

Pull-forward trigger:
- perf-sensitive PRs become frequent
- benchmark verification keeps happening manually and repeatedly
- the team needs shared, reproducible benchmark runs outside local machines

## Mid-Term

### 6. Search architecture hardening (next layer)
Continue clarifying boundaries between tokenization, indexing, retrieval orchestration, and benchmark/evaluation surfaces after the first canonical retrieval hardening pass.

Why:
- easier profiling
- easier replacement of hot paths
- less coupling between product behavior and benchmark code

Deferred because:
- the first canonical retrieval hardening pass is complete, so the next layer should only move when a new pressure point is clearly identified
- boundary changes should continue to be driven by measured hotspots and concrete pressure points

Pull-forward trigger:
- hotspot analysis keeps landing on coupling between search layers rather than one isolated function
- benchmark and product code become too entangled to optimize safely
- backend or local-model experiments require cleaner boundaries

### 7. Semantic quality and linting expansion
Extend quality checks beyond structural integrity into knowledge quality.

Examples:
- contradiction detection
- stale claim detection
- weak-link or orphan-topic surfacing
- citation/provenance quality checks

### 8. Incremental rebuild and ingest efficiency
Reduce the cost of repeated partial updates to a Snowiki workspace.

Why:
- large vaults will need incremental, not always full, rebuild behavior

Deferred because:
- current performance work is focused on search/query/index latency under the existing full-flow model
- incremental rebuild changes are broader than the first retrieval performance pass

Pull-forward trigger:
- rebuild time becomes a dominant user-visible bottleneck
- real vault sizes make full rebuilds impractical
- daemon/warm-index optimization alone is not enough

## Long-Term

### 9. Optional native acceleration for hot paths
Investigate Rust-backed implementations for the highest-value performance-sensitive paths while keeping Python as the public orchestration/API layer.

Important:
- public import surface should remain `snowiki.*`
- this is explicitly a later-stage optimization, not a current implementation goal

Potential candidates:
- search/index/query hot paths
- tokenization/ranking utilities
- large-scale data transforms where Python overhead becomes dominant

Deferred because:
- profiling-first work must identify real Python bottlenecks before introducing native complexity
- backend/layout foundations were only just stabilized

Pull-forward trigger:
- measured hotspots remain CPU-bound after Python-level optimization
- Tantivy- or native-style tradeoffs become compelling enough to justify migration cost
- local performance targets cannot be met within the current Python implementation

### 10. Local semantic and hybrid retrieval layer
Investigate embeddings, reranking, query expansion, and hybrid retrieval as additive layers on top of the lexical backbone.

Why:
- semantic recall helps with paraphrases, vague queries, and cross-language meaning gaps
- qmd-like systems show that local embeddings and rerankers can materially improve retrieval quality when used carefully

Deferred because:
- the current next plan is intentionally lexical/profiling-first
- semantic and hybrid work should follow measured baseline clarity, not precede it
- local model CPU/GPU tradeoffs need to be treated explicitly, not buried inside a performance PR

Likely scope:
- embedding index insertion points
- rerank and query-expansion hooks
- CPU-only fallback and GPU-optional acceleration policy
- warm/cold model lifecycle and caching strategy

Pull-forward trigger:
- benchmark or user evidence shows lexical retrieval missing too many semantically relevant results
- a strong lexical baseline exists and the next bottleneck is quality rather than raw latency
- local model ergonomics become important enough for agent-facing retrieval quality

### 11. Broader benchmark and evaluation system
Expand from the current deterministic backend benchmark into a richer evaluation framework.

Examples:
- scheduled benchmark runs
- benchmark history/trend tracking
- more slices and workload classes
- memory and higher-percentile latency measurement

Deferred because:
- the current benchmark is already sufficient for the first performance deep dive
- evaluation-system expansion should follow actual optimization work and real measurement pain

Pull-forward trigger:
- current benchmark slices stop reflecting real regressions
- the team needs history/trend visibility rather than one-off reports
- semantic/hybrid retrieval starts requiring broader evaluation dimensions

## Pull-Forward Triggers

Promote a roadmap item into `.sisyphus/plans/` when one or more of these becomes true:
- it blocks current product or architecture work
- the team is repeatedly doing the task manually
- regressions are happening without sufficient automation
- scope is concrete enough to define acceptance criteria and verification commands

## Explicitly Not Tracked Here

These should usually live elsewhere:
- one-off bugs
- single-PR cleanup work
- execution-ready implementation breakdowns
- transient brainstorming without prioritization
