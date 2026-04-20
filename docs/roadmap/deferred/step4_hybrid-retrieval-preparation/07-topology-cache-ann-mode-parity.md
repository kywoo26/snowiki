# Topology, Cache, ANN, and Mode Parity Policy

## Purpose

Define the unresolved runtime-topology questions that sit between a promising hybrid design and a safe implementation plan.

This document exists because the skeptical audit showed that Step 4 still hides several hard boundaries behind broad words like “plumbing” and “fallback”:
- where vector state lives
- when exact scan stops being acceptable
- who owns model/query/rerank caches
- how CLI, daemon, MCP, and benchmark surfaces stay mode-consistent

## Scope

This sub-step covers:
- vector/index topology choices
- ANN transition criteria versus exact-scan-only PoC posture
- cache ownership boundaries
- cross-surface mode parity requirements

Out of scope:
- implementing ANN immediately
- choosing the final ANN library now
- detailed reranker math

## Topology questions that must be closed

### 1. Storage topology
-Step 4 must explicitly decide whether vector state lives:
- inside the same local index surface as the lexical branch
- in a sidecar artifact keyed by compatibility identity
- or behind a runtime-owned cache layer

### 2. Snapshot topology
Hybrid work must define how vector/BM25 state integrates with:
- retrieval snapshots
- daemon warm state
- invalidation identities
- benchmark fixtures and reports

### 3. Compatibility identity
Model/version identity must be strong enough to prevent mixing incompatible vector rows, stale rerank cache entries, or invalid daemon warm state.

## ANN transition gate

Step 4 may begin with exact scan for the PoC, but it may not leave the ANN question as pure hand-waving.

This document must define:
- what corpus/chunk scale still counts as acceptable for exact scan
- what latency threshold triggers ANN investigation
- what benchmark artifact proves exact scan is no longer sufficient

If those thresholds are absent, “ANN later” is not a real plan.

## Cache ownership map

Step 4 must distinguish at least four cache/state owners:
1. warm lexical / retrieval snapshot state
2. embedder model process-local state
3. rerank score cache
4. optional vector-query cache

For each owner, planning must define:
- who creates it
- what invalidates it
- whether it is daemon-only or also used in CLI/MCP paths
- what diagnostics or benchmark artifacts expose its behavior

## Mode parity policy

Hybrid mode must not exist in one surface as a “real mode” and in another as a compatibility no-op for longer than the exploratory phase.

Before execution-plan promotion, Step 4 must define parity expectations for:
- CLI
- daemon
- MCP
- benchmark harness

That includes:
- the shared mode vocabulary
- degraded-mode behavior when dense resources are unavailable
- reportable diagnostics that explain fallback or shortcut behavior

## Deliverables

1. a storage/snapshot topology policy
2. an ANN transition gate definition
3. a cache ownership table
4. a mode-parity contract across runtime surfaces

## Acceptance criteria

- exact scan is not left as an unbounded placeholder
- cache ownership is explicit enough to guide invalidation and diagnostics design
- CLI / daemon / MCP / benchmark parity is treated as a first-class governance concern
- the document can serve as a prerequisite for future schema ADRs or `.sisyphus/plans/` work
