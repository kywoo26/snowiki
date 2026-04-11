# ROADMAP

This file tracks strategic work that is likely to matter over multiple PRs.

- **Use this file for**: medium/long-term direction, major initiatives, and backlog items that are not yet broken down for immediate execution.
- **Do not use this file for**: execution-ready task lists. Those belong in `.sisyphus/plans/*.md`.

## Current State

Recently completed foundation work:
- governance and path-contract cleanup
- test suite split into fast unit vs explicit integration paths
- migration to standard `src/snowiki/` package layout

The repository is now in a better state to take on larger product and performance work without layout/policy churn.

## Near-Term

### 1. Search and retrieval performance deep dive
Profile and improve the current hot paths in indexing and query execution.

Why:
- performance-sensitive wiki workloads will concentrate here first
- the benchmark system already exists, but tuning and architecture work remain

Likely scope:
- identify dominant costs in BM25/tokenization/index build/query flows
- reduce avoidable rebuild/query overhead
- make performance regressions easier to diagnose from benchmark output

### 2. Benchmark workflow ergonomics
Add an on-demand GitHub workflow for benchmark execution without making benchmarks a default PR hard gate.

Why:
- benchmark command exists, but is currently local/manual only
- perf-sensitive work would benefit from reproducible shared runs in GitHub Actions

Deferred because:
- the current priority is fixing the core lexical/query/index hot path itself, not workflow UX around benchmarking
- benchmark automation should follow measured optimization work, not get mixed into the first performance deep dive

Likely scope:
- `workflow_dispatch` benchmark workflow
- preset selection (`core`, `retrieval`, `full`)
- artifact upload for JSON benchmark reports

Pull-forward trigger:
- perf-sensitive PRs become frequent
- benchmark verification keeps happening manually and repeatedly
- the team needs shared, reproducible benchmark runs outside local machines

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

## Mid-Term

### 5. Search architecture hardening
Clarify boundaries between tokenization, indexing, reranking, retrieval orchestration, and benchmark/evaluation surfaces.

Why:
- easier profiling
- easier replacement of hot paths
- less coupling between product behavior and benchmark code

Deferred because:
- the immediate next step is a profiling-first optimization pass, not a broad architecture rewrite
- boundary changes should be driven by measured hotspots and concrete pressure points

Pull-forward trigger:
- hotspot analysis keeps landing on coupling between search layers rather than one isolated function
- benchmark and product code become too entangled to optimize safely
- backend or local-model experiments require cleaner boundaries

### 6. Semantic quality and linting expansion
Extend quality checks beyond structural integrity into knowledge quality.

Examples:
- contradiction detection
- stale claim detection
- weak-link or orphan-topic surfacing
- citation/provenance quality checks

### 7. Incremental rebuild and ingest efficiency
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

### 8. Optional native acceleration for hot paths
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

### 9. Local semantic and hybrid retrieval layer
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

### 10. Broader benchmark and evaluation system
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
