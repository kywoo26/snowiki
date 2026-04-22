# Benchmark & Quality Playbook

This playbook guides performance-sensitive changes and search quality verification in Snowiki. Use it when modifying search algorithms, indexing logic, or when `AGENTS.md` routes you here for performance verification.

## Benchmark Authority Model

Benchmarks in Snowiki are organized into **execution layers** and **evidence authority classes**. Execution layers define when a benchmark runs; authority classes define what claims the results can support.

### Execution Layers

| Layer | Trigger | Datasets | Metrics | Blocking |
| :--- | :--- | :--- | :--- | :--- |
| `pr_official_quick` | PRs touching benchmark-relevant paths | Same 6 official ko/en datasets, quick volume (150-query cap) | nDCG@10, Recall@100, MRR@10, P95 latency | Yes |
| `scheduled_official_broad` | Weekday-nightly cron + manual | Same 6 official ko/en datasets, standard volume (500-query cap) | nDCG@10, Recall@100, MRR@10, P95 latency | No |
| `release_proof` | Manual only (disabled-by-default) | Holdout set (not configured) | Full scorecard | Yes |

### Authority Classes

| Class | Scope | Gating Power |
| :--- | :--- | :--- |
| `official_standard` | Downloaded public datasets in the fixed ko/en standard suite (MS MARCO, TREC DL, MIRACL, BEIR) | **Release-quality claims.** Results can be cited in release notes and compared externally. |
| `official_candidate` | Datasets awaiting review | **Provisional.** Must be promoted to `official_standard` before release claims. |
| `local_diagnostic` | regression, snowiki_shaped, hidden_holdout | **Candidate-screening only.** Cannot appear in official scorecards or release claims. |

### Official Balanced-Core Backbone

The official benchmark backbone consists of exactly these 6 datasets:

| Dataset | Language | Source |
| :--- | :--- | :--- |
| `ms_marco_passage` | en | Microsoft MSMARCO |
| `trec_dl_2020_passage` | en | NIST TREC DL 2020 |
| `miracl_ko` | ko | MIRACL Korean |
| `miracl_en` | en | MIRACL English |
| `beir_nq` | en | BEIR Natural Questions |
| `beir_scifact` | en | BEIR SciFact |

Local diagnostic datasets (`regression`, `snowiki_shaped`, `hidden_holdout`) are excluded from official scorecards and release claims.

### Phase 1 as the Regression Tier

The current benchmark suite (Phase 1) is the **`regression` tier**. It is a deterministic, headless backend benchmark that verifies core retrieval and performance characteristics on a fixed 90-query set. It focuses on the `ingest -> rebuild -> query -> status/lint` flow using local, deterministic components. No LLM calls or agentic loops are exercised in this phase.

Because the 90-query set is visible and tuned against during development, it is explicitly classified as **regression / candidate-screening only**. It cannot support release-quality or final-proof claims on its own.

### Phase 2 Exclusions (Future Work)
The following items are explicitly excluded from Phase 1 and are planned for future tiers:
- `sync` and `edit` command benchmarking.
- Semantic linting and contradiction detection.
- Claim-level citations and epistemic integrity checks.
- P99 latency metrics (Phase 1 uses P50 and P95).
- Precision@K metrics (Phase 1 uses Recall@K, MRR, and nDCG@K).

Tokenizer-promotion operational evidence (memory/disk) is measured separately from the Phase 1 benchmark pass/fail gate and is no longer treated as a future-only exclusion.

### Snowiki-Shaped Suite Coverage Quotas

The `snowiki_shaped` tier enforces deterministic coverage quotas so the suite reflects real Snowiki workloads:

| Coverage Bucket | Quota |
| :--- | :--- |
| Mixed-language (Korean + English) | 30% |
| Code / documentation lookup | 25% |
| Topical knowledge | 30% |
| Temporal / dated queries | 10% |
| No-answer / abstention cases | 5% |
| LLM-generated content | 0% (none; all corpus assets are scripted/crawled) |

These quotas are fixed at generation time. The shaped suite is authoritative for release-quality claims about Snowiki's target workload, but it is still visible during development and therefore does not serve as final proof.

### Tier-Aware Execution and Latency Sampling

Latency measurement adapts by tier so that large datasets do not distort performance signals:

| Tier | Default Sampling Mode | Rationale |
| :--- | :--- | :--- |
| `regression` | Exhaustive (all queries) | Small, fixed 90-query set; every query matters for deterministic candidate screening. |
| `public_anchor` / `snowiki_shaped` | Stratified (up to 20 queries per stratum) | Large visible suites; stratified sampling by `group` or `kind` preserves representativeness without inflating run time. |
| `hidden_holdout` | Fixed sample (20 queries) | Held-out sets are large by design; a bounded sample protects run time while still producing a stable latency signal. |

Sampling policy is recorded in every report under `protocol.sampling_policy` so the exact population-vs-sampled counts are auditable. Report detail for large non-regression tiers is capped to 20 per-query entries so JSON outputs stay inspectable without dropping aggregate metrics.

## Benchmark Assets

The following files define the **regression / candidate-screening** quality dataset:

- `benchmarks/queries.json`: Bilingual query set (Korean, English, Mixed) covering known-item, topical, and temporal retrieval, with machine-checkable `tags` and optional `no_answer` flags.
- `benchmarks/judgments.json`: Gold relevance judgments for the query set; no-answer queries are represented as queries with no relevant documents.

`benchmarks/*.json` files are benchmark-maintenance assets for the visible regression tier only. They must not be promoted into authoritative `public_anchor`, `snowiki_shaped`, or `hidden_holdout` tiers.

## Real Public Dataset Management

Real public benchmark payloads stay **out of git**. Use the dedicated benchmark fetch cache instead of copying corpora or qrels into `benchmarks/`.

- Default benchmark data root: `SNOWIKI_ROOT/benchmarks`
- Override env var: `SNOWIKI_BENCHMARK_DATA_ROOT`
- Benchmark-owned Hugging Face cache: `<benchmark_data_root>/hf`
- Local lock metadata: `<benchmark_data_root>/locks/<dataset_id>.json`

If you point `--data-root` at the repo-local `benchmarks/` directory for experiments, both payload caches and generated lock files remain local-only and should stay out of git.

Use the flat CLI entrypoint:

```bash
# Fetch a public-anchor dataset into the benchmark-owned HF cache
uv run snowiki benchmark-fetch --dataset miracl_ko

# Force-refresh a repo-local benchmark cache root for local experiments
uv run snowiki benchmark-fetch --dataset beir_scifact --data-root benchmarks --refresh force

# Reuse only locally cached files (no network)
uv run snowiki benchmark-fetch --dataset beir_nq --offline
```

The fetch command stores dataset payloads in the benchmark data root / HF cache and writes small local lock metadata describing every resolved source snapshot, revision, provenance metadata, and allow-listed file scope. Corpora and qrels remain outside git-managed benchmark assets.

## Execution

Run benchmarks using the `snowiki benchmark` command. Always use `uv run` to ensure the correct environment.

When `--root` is omitted, the benchmark runs inside an isolated local Snowiki root created under the JSON output directory and seeded with the regression-tier fixtures. This keeps the run isolated from the user's real `~/.snowiki` runtime tree while leaving benchmark-local artifacts durable for inspection.

The default dataset remains `regression`. Public anchors are opt-in via `--dataset` so release-quality anchor runs stay clearly separated from candidate-screening regression checks.

The `hidden_holdout` dataset exposed in local development is a **synthetic workflow facsimile only**. It exists to test sealing, pooled review, blind adjudication, disagreement handling, and audit-report plumbing without exposing the real release holdout.

### Presets

| Preset | Description |
| :--- | :--- |
| `core` | Fast regression check using known-item queries. |
| `retrieval` | Broader check including known-item and topical queries. |
| `full` | Complete coverage including temporal queries. |

### Example Commands

```bash
# Fast regression check (local diagnostic)
uv run snowiki benchmark --preset core --output reports/core.json

# Official PR quick suite (with layer annotation)
uv run snowiki benchmark-fetch --dataset ms_marco_passage
uv run snowiki benchmark --preset retrieval --dataset ms_marco_passage \
  --sample-mode quick --layer pr_official_quick --output reports/ms_marco.json

# Official scheduled broad suite (with layer annotation)
uv run snowiki benchmark-fetch --dataset miracl_ko
uv run snowiki benchmark --preset retrieval --dataset miracl_ko \
  --sample-mode standard --layer scheduled_official_broad --output reports/miracl_ko.json

# Local diagnostic (not official)
uv run snowiki benchmark --preset retrieval --dataset hidden_holdout \
  --layer pr_official_quick --output reports/hidden_holdout.json
```

### Dataset Selection

`snowiki benchmark` accepts `--dataset` with the following options:

**Official Standard Datasets:**
- `ms_marco_passage`, `trec_dl_2020_passage`
- `miracl_ko`, `miracl_en`
- `beir_nq`, `beir_scifact`

**Local Diagnostic Datasets (not official):**
- `regression`, `snowiki_shaped`, `hidden_holdout`

**Additional Public-Anchor Dataset (supported, but not part of the official standard suite):**
- `beir_nfcorpus`

- `regression` keeps using the deterministic Phase 1 local fixtures.
- `miracl_ko` loads a compact deterministic sample built from the real cached MIRACL Korean parquet assets. Query IDs, document IDs, and qrels come from the public dataset; run `benchmark-fetch` first.
- `beir_scifact` loads a compact deterministic sample built from the real cached BEIR SciFact corpus/queries repo plus the separate SciFact qrels repo. Query IDs, document IDs, and qrels come from the public dataset; run `benchmark-fetch` first.
- `beir_nfcorpus` loads a compact deterministic sample built from the real cached BEIR NFCorpus corpus/queries repo plus the separate NFCorpus qrels repo. Query IDs, document IDs, and qrels come from the public dataset; run `benchmark-fetch` first.
- `snowiki_shaped` loads a deterministic internal scripted-crawl facsimile with mixed Korean+English, code/doc, topical, temporal, and no-answer coverage for Snowiki-shaped evaluation.
- `hidden_holdout` loads a deterministic synthetic sealed-holdout facsimile for development-time verification of visibility-tier sealing, pooled review, blind adjudication, disagreement escalation, and audit sampling. It is not the real release holdout and must not be cited as final proof.

To keep tiers isolated, manifest-backed datasets are seeded only into empty isolated benchmark roots. They do not reuse or silently mix with the regression fixtures.

## Review & Audit Workflow

Authoritative benchmark maintenance uses pooled review rather than single-system qrels alone.

- **Multi-system pooling**: candidate documents are pooled from multiple retrieval systems so adjudication does not inherit a single ranker's blind spots.
- **Blind human adjudication**: reviewers judge pooled candidates without seeing which system retrieved them.
- **Disagreement handling**: when pooled judgments conflict, the query is escalated to adjudication and the benchmark status reports disagreement counts rather than silently collapsing them.
- **Audit sampling**: a quota-controlled sample of adjudicated queries is re-reviewed to estimate ground-truth error and report provenance coverage across source class, authoring method, visibility tier, and authority tier.
- **Hidden holdout sealing**: hidden-holdout corpus/query/judgment manifests stay sealed by `visibility_tier="hidden_holdout"`; development reports expose only sealed counts and audit summaries, never the hidden asset manifests themselves.

This means the visible `regression`, `public_anchor`, and `snowiki_shaped` suites are useful for iteration, but they must not also serve as the only final proof set.

### GitHub Manual Workflow

For shared, reproducible benchmark runs without turning benchmarks into a default PR hard gate, use the GitHub Actions workflow:

- Workflow: `benchmark-manual`
- Trigger: `workflow_dispatch`
- Inputs: `preset` (`core`, `retrieval`, `full`)

The workflow uploads the generated JSON report as an artifact so the result can be reviewed without relying on a local machine.

## Pass/Fail Semantics

The benchmark command evaluates three primary gates. A failure in any blocking gate results in a non-zero exit code.

1.  **Structural Gate (Blocking)**: Verifies workspace integrity and lint health. Any `ERROR` level issue fails this gate.
2.  **Retrieval Gate (Blocking)**: Compares retrieval metrics against frozen regression-tier thresholds.
    -   **Overall Thresholds**: Recall@k >= 0.72, MRR >= 0.70, nDCG@k >= 0.67.
    -   **Slice Thresholds**: Specific targets for `known-item`, `topical`, and `temporal` slices.
3.  **Performance Gate (Blocking)**: Verifies latency for `ingest`, `rebuild`, and `query`.
    -   **Thresholds**: P50 <= 5950ms, P95 <= 6300ms.

### Unified Verdict
The final line of the benchmark output provides a unified verdict:
`Unified benchmark verdict: PASS/FAIL (blocking_stage=..., exit_code=...)`

## Report Output

The benchmark produces two types of output:
1.  **Human-readable summary**: Printed to stdout, including per-baseline metrics, threshold deltas, and the unified verdict.
2.  **Machine-readable JSON**: Written to the path specified by `--output`. This report includes detailed metrics, threshold policies, structural validation results, multi-k metric maps, and subset slices when available.

The stdout summary is intended to be concise and benchmark-focused. Backend library progress bars should not obscure the final structural, performance, retrieval, and unified verdict sections.

## GitHub Actions Workflows

Three workflows support the official benchmark system:

| Workflow | Trigger | Purpose |
| :--- | :--- | :--- |
| `benchmark-official-pr` | PR paths + manual | Runs the fixed 6-dataset ko/en official suite at quick volume (150-query cap) |
| `benchmark-official-scheduled` | Weekday-nightly cron + manual | Runs the same 6-dataset ko/en official suite at standard volume (500-query cap) |
| `benchmark-manual` | Manual only | Ad-hoc benchmark runs for any preset |

All workflows support offline preflight. If a dataset is not cached, the run is recorded as `infra_skipped` and the workflow continues.

## Dashboard Decision Matrix

The following directions were evaluated for richer benchmark visualization:

| Direction | Mainstream Adoption | Production Fit | Maintenance Cost | Integration Complexity | Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Richer static pipeline | Medium | High | Low | Low | **Recommended for next step** |
| Interactive portal | High | Medium | High | High | Deferred |
| Report-store integration | Medium | High | Medium | Medium | Deferred |

**Decision**: Ship artifact-first tables and static plots now. Evaluate interactive portal options after the official benchmark system is stable.

## Next Steps

1. **Threshold calibration for official datasets**: Layer-specific thresholds need calibration against external baselines.
2. **Real hidden holdout sealing**: Establish a genuine held-out set for release proof.
3. **Interactive dashboard**: Evaluate portal options after benchmark system stabilizes.
4. **Benchmark asset update policy**: Define PR checklist for adding/modifying datasets.

## Verification

- Ensure `uv run pytest` passes for all benchmark-related tests.
- Verify that machine-readable JSON reports are generated in the specified output path.
- Review the `Unified benchmark verdict` for a `PASS` status.
