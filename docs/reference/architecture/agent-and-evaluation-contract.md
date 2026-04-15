# Agent and Evaluation Contract

## Purpose

This document defines two things that Snowiki must keep explicit:

1. how the system should be evaluated
2. what agents may safely depend on as stable contracts today

The goal is to keep evaluation and agent-facing ergonomics first-class, without mixing them into vague product promises.

## Evaluation axes

Snowiki should evaluate different concerns separately rather than collapsing them into one notion of “quality.”

### 1. Retrieval quality
This is about whether the system finds the right material.

Current useful metrics:
- Recall@k
- MRR
- nDCG@k

### 2. Latency
This is about whether ingest, rebuild, and query are fast enough for real use.

Current benchmark posture already includes:
- P50 latency
- P95 latency

### 3. Structural integrity
This is about whether the workspace is internally sound.

Examples:
- path / index consistency
- lint health
- broken links
- orphan pages
- stale artifacts

### 4. Provenance quality
This is about whether claims and compiled artifacts can be traced back to sources.

This is broader than retrieval quality and should stay a separate axis.

### 5. Answer quality
This is about final synthesis or response usefulness.

This is **not** the same as retrieval quality and should only be treated as such if explicitly justified.

## Current verified agent-facing contracts

These are the interfaces Snowiki can honestly present today.

### CLI JSON contract
Current runtime truth:
- the installed `snowiki` CLI is authoritative
- machine-readable output exists where commands support `--output json`

Safe current examples:
- `snowiki query ... --output json`
- `snowiki recall ... --output json`
- `snowiki export ... --output json`

### MCP contract
Snowiki ships a read-only MCP surface.

Safe current expectations:
- read-oriented search/retrieval
- no mutation through MCP
- deterministic enough retrieval primitives for agent loops

### Skill/workflow role
The skill layer should be treated as a workflow layer around the shipped runtime, not as a separate source of runtime truth.

That means:
- the CLI remains authoritative
- the skill may orchestrate
- the skill may not silently redefine what Snowiki “is” or “can do”

## What agents should not assume yet

Agents should **not** assume the following are current stable runtime guarantees:
- semantic retrieval as the default path
- hybrid mode as a mature shipped behavior
- reranking in the default path
- edit/sync/merge style broad workflow actions as stable runtime features
- model-backed retrieval availability

## Design rule

When Snowiki grows, new retrieval or workflow layers must preserve:
- stable machine-readable contracts
- deterministic enough behavior for automation
- explicit failure semantics
- separation between retrieval quality and answer quality

If a proposed change cannot explain how those contracts remain valid, it is not ready.
