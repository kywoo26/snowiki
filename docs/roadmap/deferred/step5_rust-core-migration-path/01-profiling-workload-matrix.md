# Profiling Workload Matrix

## Purpose

Define the exact workloads, commands, and profiling method Snowiki must use before any Rust spike is approved. This sub-step exists to turn Step 5's "collect profiling evidence" requirement into a reproducible execution unit rather than a vague placeholder.

## Why this is separate

Step 5 is currently blocked because profiling evidence is still planned rather than collected. Keeping workload design in its own document prevents boundary design and packaging policy from moving ahead on unproven assumptions.

## Scope

In scope:
- define the benchmark datasets and workload categories
- define the exact commands to run for each workload
- define how to capture cold-start and warm-start measurements
- define how CPU profiling output is collected, repeated, and summarized
- define the acceptance bar for declaring a single dominant hotspot

Out of scope:
- implementing a Rust prototype
- changing retrieval algorithms
- optimizing Python code yet
- deciding packaging or boundary API details beyond what is needed to measure current Python behavior

## Non-goals

- Do not leave evidence collection as "run a profiler sometime later."
- Do not use toy workloads that hide indexing or query costs.
- Do not declare a hotspot from a single noisy run.
- Do not mix wall-clock regressions with CPU hotspot identification without recording both separately.

## Workload matrix

### 1. Small local corpus

Purpose:
- represent the current fast-path local workflow where startup overhead can dominate

Minimum shape:
- a small corpus that fits normal local development usage
- enough documents to exercise ingest, rebuild, query, and recall without turning every run into a batch benchmark

Required operations:
- `uv run snowiki rebuild`
- `uv run snowiki query "<representative query>" --output json`
- `uv run snowiki recall yesterday --output json`

Why it matters:
- confirms whether the dominant cost is startup, tokenization, lexical retrieval, or orchestration on realistic small installs

### 2. Medium mixed-language corpus

Purpose:
- stress tokenizer, preprocessing, and indexing on a corpus with multiple language or syntax shapes rather than a uniform text set

Minimum shape:
- markdown, code, and prose mixed together
- enough scale that rebuild and query work produce stable CPU profiles rather than startup-only traces

Required operations:
- `uv run snowiki rebuild`
- `uv run snowiki query "<representative query>" --output json`

Why it matters:
- this is the most likely workload to expose tokenizer/preprocessing or indexing hot paths that are hidden on a tiny corpus

### 3. Retrieval benchmark preset

Purpose:
- use the repository's explicit benchmark path as the canonical repeatable performance workload

Required operation:
- `uv run snowiki benchmark --preset retrieval --output reports/retrieval.json`

Why it matters:
- this is already named in Step 5's verification plan and gives the project a shared benchmark surface for repeated comparison

### 4. Cold vs warm runs

For every workload above, collect both:

- **Cold run**: first execution after clearing any relevant process-level warm state so startup, import, and first-load behavior are visible
- **Warm run**: repeated execution against the same prepared corpus so steady-state CPU costs are visible

The report must keep cold and warm results separate. A hotspot that appears only on cold start is operationally relevant, but it should not be confused with the steady-state hot loop that might justify Rust.

## Profiling methodology

### Commands to collect evidence

For each operation in the workload matrix:

1. run one unprofiled pass to confirm the command succeeds and the corpus is prepared
2. run one cold profiled pass
3. run at least three warm profiled passes
4. record wall-clock duration and profiler output for each run

### Profiler requirements

Each profiled run must capture:
- total runtime
- top functions by cumulative CPU time
- top functions by self CPU time when available
- call counts for the dominant functions when available
- enough module/function detail to distinguish tokenizer, indexing, search, chunking, and orchestration work

### Reproducibility requirements

- use the same command line and corpus for all repeated runs in a workload
- record whether the run is cold or warm
- record the environment details needed to repeat the result later
- summarize results by workload, not by ad hoc notes

## Required report structure

The profiling report produced from this sub-step must include, for each workload:

1. corpus description
2. command executed
3. cold-run runtime and top CPU consumers
4. warm-run runtime range across repeated runs
5. dominant function or module by cumulative CPU share
6. short interpretation of why that hotspot is likely stable or not stable

It must also end with a single ranked hot-path table across all workloads.

## Deliverables

1. A completed profiling report linked from `profiling-baseline.md`
2. A workload matrix table listing dataset, operation, cold/warm status, repetition count, and profiler artifact location
3. A ranked list of candidate hot paths with measured CPU share and run-to-run variance notes
4. An explicit recommendation naming the single best first Rust candidate, or a decision that Step 5 should not advance yet

## Acceptance criteria

This sub-step is complete only when all are true:

1. small corpus, medium mixed-language corpus, retrieval benchmark, and cold vs warm runs are all covered
2. each workload includes exact commands and repeated profiled runs, not placeholders
3. the resulting report identifies one dominant CPU hotspot rather than a vague set of possibilities
4. the hotspot is supported by reproducible numbers across repeated warm runs
5. the report clearly distinguishes CPU-bound hot-loop work from startup-only overhead

## Exit condition for the next sub-step

The boundary API sketch may use this result only after the profiling report identifies the single dominant CPU hotspot with reproducible numbers.
