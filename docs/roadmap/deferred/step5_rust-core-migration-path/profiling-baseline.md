# Profiling Baseline

## Status

**Planned evidence artifact** — profiling data not yet collected.

This file exists so Step 5 has an explicit place to accumulate the evidence required before any Rust spike is approved.

---

## Purpose

Before Snowiki moves any component into Rust, it must show:

1. the hotspot is real,
2. the hotspot is persistent under realistic workloads,
3. Python-level improvements are insufficient, and
4. the boundary around the hotspot is stable enough to accelerate safely.

---

## Evidence to collect

### 1. Workloads

The profiling set should include at least:

- small local corpus
- medium mixed-language corpus
- retrieval-focused benchmark corpus
- cold start and warm start runs where relevant

### 2. Operations

Profile at minimum:

- `snowiki query`
- `snowiki recall`
- `snowiki rebuild`
- benchmark retrieval preset

### 3. Candidate regions to measure

- tokenization / preprocessing
- index construction
- lexical search / ranking
- chunk materialization
- hybrid fusion seam (if present during experiments)

---

## Required outputs

For each workload, record:

- command and dataset description
- total runtime
- top CPU consumers
- cumulative time share by function/module
- cold vs warm behavior where meaningful
- whether the hotspot appears stable across repeated runs

---

## Acceptance threshold for Step 5 promotion

Rust/native work may proceed only when all are true:

1. one hotspot is repeatedly dominant,
2. the hotspot survives Python-level cleanup,
3. the hotspot boundary is contract-stable,
4. the expected win justifies packaging/debug complexity.

---

## Initial hypothesis

Based on current external evidence, the leading candidates are:

1. tokenizer / preprocessing
2. index construction
3. lexical search kernel

This is only a hypothesis until profiling confirms it.

---

## To fill in later

### Benchmark run log

- _Pending_

### Hot-path ranking from measured data

- _Pending_

### Python-level optimization attempts

- _Pending_

### Recommendation

- _Pending_
