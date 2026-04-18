# Hybrid Evaluation + Mode Plumbing

## Purpose

Define how Step 4 hybrid retrieval is exposed for evaluation without becoming the default runtime path, and specify the benchmark slices and ablations required before any promotion decision.

## Scope

This sub-step covers:
- benchmark integration for hybrid variants
- mode-gated API plumbing across CLI, MCP, and daemon surfaces
- degraded-mode integration behavior
- the evaluation slices and ablations required before runtime promotion

## Decisions

### 1. Runtime mode policy

Add explicit retrieval modes:
- `lexical` — default shipped behavior
- `hybrid` — BM25 + vector + fusion + optional rerank + shortcut
- `vector` — diagnostic and benchmark-only dense retrieval mode

`lexical` remains the default everywhere. `hybrid` exists as an opt-in mode only.

### 2. Surface plumbing

#### CLI

Expose `--mode` on:
- `snowiki query`
- `snowiki recall`
- `snowiki benchmark --preset retrieval`

#### MCP

Expose an optional `mode` argument on the existing search/recall tools with the same enum values.

#### Daemon

Accept mode per request while reusing a snapshot that may contain lexical, BM25, and vector indexes when available.

### 3. Integration fallback behavior

If hybrid or vector mode is requested but embeddings are unavailable:
- complete the request successfully
- return BM25/lexical results instead of failing
- report a structured fallback reason

If reranking is unavailable:
- return fused or BM25 results unchanged
- report reranker fallback separately from embedder fallback

### 4. Required benchmark slices

Hybrid benchmarking must include these slices before runtime promotion is considered:

1. **exact-match / known-item**
2. **paraphrase / semantic**
3. **mixed-language**
4. **fallback / degraded-mode**

These slices are mandatory, not optional reporting extras.

### 5. Required comparison variants

The benchmark harness must compare at least:

1. lexical baseline
2. BM25-only runtime candidate
3. hybrid with RRF only
4. hybrid with shortcut enabled
5. hybrid with rerank enabled

### 6. Required ablations before promotion

Run all of the following before hybrid is allowed to move toward runtime promotion:

1. shortcut on vs off
2. RRF with vs without position bonus
3. diversity cap on vs off
4. rerank on vs off
5. mixed-language tokenizer/back-end comparisons tied to Step 2 sparse decisions

### 6.1 Required report artifacts

Every hybrid benchmark run should save machine-readable outputs that let Snowiki compare runs over time.

Minimum durable artifacts:
- slice metrics JSON
- ablation summary JSON
- fallback / shortcut event counts
- latency distribution summary
- short human-readable summary suitable for roadmap closeout notes

### 7. Promotion gate posture

`--mode hybrid` may ship as an opt-in capability before promotion, but hybrid must **not** become default until all Step 4 evaluation gates are met:
- semantic recall lift
- exact-match preservation
- latency envelope
- shortcut usefulness
- fallback correctness
- provenance integrity

## Non-goals

- enabling hybrid as the default CLI or MCP behavior
- collapsing benchmark and runtime code paths into one opaque surface
- treating benchmark wins as automatic permission to flip the default

## Deliverables

1. a closed `--mode` contract for CLI, MCP, and daemon surfaces
2. integration-test requirements for degraded hybrid requests
3. a benchmark matrix covering slices, variants, and ablations
4. a promotion rule that keeps hybrid opt-in until evidence is complete

## Implementation planning notes

### Primary Snowiki files likely involved later
- `src/snowiki/cli/commands/query.py`
- `src/snowiki/cli/commands/recall.py`
- `src/snowiki/cli/commands/benchmark.py`
- `src/snowiki/mcp/server.py`
- `src/snowiki/daemon/server.py`
- `src/snowiki/bench/contract.py`
- `src/snowiki/bench/presets.py`
- `src/snowiki/bench/models.py`

### Required new tests before runtime-default discussion
1. `tests/search/test_semantic_abstraction.py`
2. integration tests for hybrid-requested-but-embedder-unavailable fallback
3. governance tests for mode parity across CLI / MCP / daemon
4. benchmark artifact tests ensuring new hybrid reports remain machine-readable and stable

### Key Step 4 discipline
This substep is where Snowiki should deliberately exceed seCall's evaluation posture.

The benchmark/evaluation layer is not a late polish step. It is the thing that makes hybrid promotion believable.

## Acceptance criteria

- `--mode hybrid` is explicitly documented as existing but **not** being the default
- CLI, MCP, and daemon mode plumbing are concrete enough that implementation can begin without reopening API-surface questions
- the required evaluation slices and ablations are documented as pre-promotion work
- fallback behavior is specified strongly enough to support integration tests for hybrid-requested-but-unavailable scenarios
