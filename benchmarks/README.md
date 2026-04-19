# Benchmark & Quality Playbook

This playbook guides performance-sensitive changes and search quality verification in Snowiki. Use it when modifying search algorithms, indexing logic, or when `AGENTS.md` routes you here for performance verification.

## Benchmark Authority Model

Benchmarks in Snowiki are organized into four authority tiers. Each tier has a defined scope and determines what claims it can support.

| Tier | Scope | Gating Power |
| :--- | :--- | :--- |
| `regression` | Fast, deterministic checks run on every candidate change. | **Candidate-screening only.** A regression-tier pass is necessary but not sufficient for release-quality claims. |
| `public_anchor` | Public, reproducible datasets with community or third-party provenance. | **Release-quality claims.** Results on public anchors can be cited in release notes and compared externally. |
| `snowiki_shaped` | Internally curated datasets that reflect real Snowiki user queries and content shapes. | **Release-quality claims.** Used to validate that the engine works well on its actual target workload, complementing public anchors. |
| `hidden_holdout` | Held-out queries and judgments not visible during development. | **Final proof.** The only tier that can definitively confirm a claim is not overfit to known benchmarks. |

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

## Execution

Run benchmarks using the `snowiki benchmark` command. Always use `uv run` to ensure the correct environment.

When `--root` is omitted, the benchmark runs inside an isolated temporary Snowiki root that is seeded with the regression-tier fixtures. This prevents Phase 1 verification from reading or mutating the user's real `~/.snowiki` runtime tree.

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
# Fast regression check
uv run snowiki benchmark --preset core --output reports/core.json

# Retrieval quality check
uv run snowiki benchmark --preset retrieval --output reports/retrieval.json

# MIRACL Korean public-anchor sample
uv run snowiki benchmark --preset retrieval --dataset miracl_ko --output reports/miracl_ko.json

# Mr. TyDi Korean public-anchor sample
uv run snowiki benchmark --preset retrieval --dataset mr_tydi_ko --output reports/mr_tydi_ko.json

# BEIR SciFact English public-anchor sample
uv run snowiki benchmark --preset retrieval --dataset beir_scifact --output reports/beir_scifact.json

# BEIR NFCorpus English public-anchor sample
uv run snowiki benchmark --preset retrieval --dataset beir_nfcorpus --output reports/beir_nfcorpus.json

# Hidden holdout workflow facsimile (development-only, not release proof)
uv run snowiki benchmark --preset retrieval --dataset hidden_holdout --output reports/hidden_holdout.json

# Full benchmark run
uv run snowiki benchmark --preset full --output reports/full.json
```

### Dataset Selection

`snowiki benchmark` now accepts `--dataset regression|miracl_ko|mr_tydi_ko|beir_scifact|beir_nfcorpus|snowiki_shaped|hidden_holdout`.

- `regression` keeps using the deterministic Phase 1 local fixtures.
- `miracl_ko` loads a deterministic MIRACL Korean public-anchor sample with preserved stable IDs, inline qrels, and explicit provenance metadata.
- `mr_tydi_ko` loads a deterministic Mr. TyDi Korean calibration sample with preserved stable IDs, inline qrels, and explicit provenance metadata.
- `beir_scifact` loads a compact deterministic English factual public-anchor sample shaped after BEIR SciFact for fast local iteration.
- `beir_nfcorpus` loads a compact deterministic English topical public-anchor sample shaped after BEIR NFCorpus for long-tail flavored local iteration.
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

## Next Steps

The following items remain open for the benchmark program to reach a fully durable maintenance posture:

1. **Threshold calibration for public anchors**: The retrieval gate thresholds (Recall@k >= 0.72, MRR >= 0.70, nDCG@k >= 0.67) are frozen for the regression tier. Public-anchor and snowiki_shaped tiers need tier-specific or dataset-specific threshold policies so that release-quality claims are calibrated against external baselines, not the 90-query regression ceiling.
2. **Real hidden holdout sealing**: The current `hidden_holdout` dataset is a synthetic workflow facsimile. Establish a genuine held-out query/judgment set that is never visible during development and is only unsealed during release adjudication.
3. **Precision@K and P99 latency metrics**: These are excluded from Phase 1 and planned for future benchmark evolution once the tier model is stable.
4. **Benchmark asset update policy**: Define a lightweight PR checklist for adding or modifying benchmark manifests so that provenance, family dedupe, and tier isolation are maintained without regressing existing suites.

## Verification

- Ensure `uv run pytest` passes for all benchmark-related tests.
- Verify that machine-readable JSON reports are generated in the specified output path.
- Review the `Unified benchmark verdict` for a `PASS` status.
