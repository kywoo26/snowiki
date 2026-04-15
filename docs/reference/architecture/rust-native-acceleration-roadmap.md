# Rust and Native Acceleration Roadmap

## Purpose

This document explains how Snowiki should think about Rust/native acceleration over time.

It exists to prevent two common mistakes:
- treating native acceleration as an immediate solution before profiling
- speaking vaguely about “Rust later” without defining what would justify it

## Current posture

Snowiki should remain a Python-first system for now.

Why:
- the current retrieval and workflow layers are still being stabilized
- the strongest current gains are still available through Python-level architecture and contract cleanup
- the public/runtime contract should stay stable while the system is still defining its core retrieval and agent-facing surfaces

## What should stay in Python for now

These areas should remain Python-first until there is strong evidence otherwise:
- CLI orchestration
- MCP/read-facing integration
- workflow/skill orchestration
- provenance handling
- benchmark/evaluation integration
- rebuild/compilation orchestration

## Likely future candidates for native acceleration

If native acceleration becomes justified, the most plausible targets are:
- lexical search hot paths
- indexing/tokenization hot paths
- rerank kernels if they become dominant and stable
- large corpus transforms that remain CPU-bound after Python optimization

These are candidates, not commitments.

## Promotion gates for native work

Rust/native work should only move from roadmap idea to implementation when all of the following are true:

### 1. Measured hotspot persistence
The bottleneck remains after:
- retrieval contract hardening
- lexical/tokenization cleanup
- Python-level architecture optimization

### 2. Stable contract boundary
The accelerated component has a stable enough interface that replacing its implementation will not destabilize:
- CLI contracts
- MCP contracts
- benchmark/evaluation posture
- provenance expectations

### 3. Operational fit
The migration can explain:
- packaging/build impact
- local development cost
- debugging cost
- platform constraints
- whether the gain is worth the complexity

### 4. Clear win profile
The target is not just “hot” but one of the following:
- repeatedly dominant in profiling
- resistant to Python-level wins
- likely to gain materially from lower-level implementation

## What should not happen too early

Do **not**:
- move orchestration layers to Rust first
- use native acceleration to avoid doing measurement
- swap backends and rewrite retrieval strategy in one step
- let packaging complexity outrun actual performance need

## Relationship to backend evolution

Rust/native acceleration and backend evolution are related but not identical.

- A backend swap (for example to Tantivy or another engine) is a product/architecture choice.
- Native acceleration of an existing hotspot is an implementation/performance choice.

Those should not be conflated.

## Bottom line

Snowiki should keep Rust/native acceleration as a serious long-term option, but only after the system can name:
- the exact hotspot
- the exact boundary
- the exact gain expected
- the exact operational cost

Until then, Python-level architectural hardening and measured optimization are the right moves.
