# Maintenance Loop and Deferred Workflows

## Purpose

Define the canonical Step 3 maintenance-loop model and the exact boundary between **shipped runtime anchors** and **deferred workflow ideas** so agents can maintain Snowiki without hallucinating unshipped capabilities.

This document owns the workflow layer only. It does **not** redefine route taxonomy from [01: Wiki Route Contract](01-wiki-route-contract.md), schema/provenance truth from [02: Schema and Provenance Contract](02-schema-and-provenance-contract.md), or mirror-governance ownership from [03: Governance and Mirror Alignment](03-governance-and-mirror-alignment.md).

## In Scope

- The maintenance-loop model: `ingest -> absorb -> lint/cleanup -> query`
- The exact boundary between shipped runtime anchors and deferred workflow ideas
- Reviewable mutation posture for agent-mediated maintenance behavior
- Agent heuristics and guardrails for maintenance-oriented reasoning

## Out of Scope

- Route taxonomy or route names
- Schema definitions and provenance/display contract details
- Governance implementation details and mirror-sync rules
- Runtime backend redesign or new storage engines
- Benchmark hardening, tokenizer evaluation, benchmark methodology, or runtime promotion
- Re-implementation of `fileback` or `lint` logic

## Owns

- The maintenance-loop model as a workflow abstraction
- Deferred workflow boundaries and unsupported-status language
- Reviewable mutation posture for maintenance-oriented agent behavior
- Agent heuristics and guardrails for choosing between shipped runtime anchors and deferred ideas

## Does Not Own

- Route taxonomy
- Schema definitions
- Governance rules
- Runtime command implementation

## Current Shipped Maintenance Anchors

The current shipped runtime provides these anchors for maintenance behavior:

- `snowiki ingest` — authoritative ingest entrypoint
- `snowiki query` — authoritative read/query entrypoint
- `snowiki recall` — authoritative temporal/session recall entrypoint
- `snowiki status` — authoritative health/status entrypoint
- `snowiki lint` — authoritative integrity/health check entrypoint
- `snowiki fileback preview` / `snowiki fileback apply` — authoritative reviewed-write entrypoints
- `snowiki daemon` — optional read optimization for repeated query/recall paths
- `snowiki rebuild` — shipped CLI support for rebuilding derived search/index state, but not itself a primary `/wiki` route

These are the only shipped anchors this maintenance layer may treat as current runtime truth.

## Maintenance Loop Model

Snowiki’s maintenance loop is a **workflow model**, not a statement that every loop stage already exists as a dedicated CLI command.

Canonical model:

1. **Ingest** — bring new source material into Snowiki through `snowiki ingest`
2. **Absorb** — synthesize or file useful takeaways into durable knowledge surfaces through reviewed, explicit mutation paths
3. **Lint/Cleanup** — inspect health, drift, or stale pages using `snowiki lint` plus review-oriented cleanup decisions
4. **Query** — read, inspect, and validate what the current knowledge surface now says via `snowiki query`, `snowiki recall`, and related read paths

The important boundary is:
- **Ingest**, **Lint**, and **Query** have shipped runtime anchors.
- **Absorb** and **Cleanup** are currently **workflow concepts** layered on top of shipped commands, not standalone shipped CLI commands.

## Deferred Workflow Boundaries

The following remain **deferred or unsupported today**:

- `absorb` as a dedicated CLI command
- `cleanup` as a dedicated CLI command
- `sync`
- `edit`
- `merge`
- graph-oriented workflows

Fail-closed rule:
- These may be discussed as future workflow ideas or orchestration patterns.
- They must **not** be described as shipped runtime behavior.
- They must **not** be treated as silently available through MCP, daemon, or any hidden wrapper.

When these concepts appear in skill or docs surfaces, they must be marked as:
- deferred
- unsupported today
- future workflow concepts rather than current commands

## Reviewable Mutation Posture

Maintenance-oriented writes must remain **reviewable**.

Current shipped write posture:

- `fileback preview` is non-mutating and produces a reviewable proposal
- `fileback apply` requires a reviewed proposal file and is the canonical mutation path for this class of workflow
- MCP is not a mutation path

This means 04 owns the workflow posture, but not the payload contract details:

- 04: when to use reviewed mutation in the loop
- 02: what the proposal/apply payloads must look like

Practical consequence:
- if a maintenance workflow requires changing durable knowledge, it must route through reviewed CLI-mediated mutation rather than implicit file edits or MCP writes

## Agent Heuristics and Guardrails

Agents operating this workflow should follow these guardrails:

1. **Prefer shipped anchors first**
   - Use current commands before reasoning about deferred workflows.

2. **Treat daemon as optimization only**
   - Daemon-backed reads are optimization only for repeated query/recall paths.
   - They do not define a second runtime truth.

3. **Do not invent absorb/cleanup commands**
   - If a workflow needs “absorb” or “cleanup,” express it as an orchestrated pattern over shipped commands and reviewed writes.

4. **Keep deferred workflows explicit**
   - `sync`, `edit`, `merge`, and graph-oriented workflows must stay visibly deferred until promoted by the canonical route contract.

5. **Preserve reviewability**
   - Any write-like maintenance behavior must remain preview-first and approval-aware.

6. **Use read paths to validate effects**
   - After maintenance-oriented actions, use `query`, `recall`, `status`, and `lint` to verify the resulting state instead of assuming success.

## Related Documents

- [Step 3 Roadmap](roadmap.md)
- [Step 3 Analysis](analysis.md)
- [Wiki Route Contract](01-wiki-route-contract.md)
- [Schema and Provenance Contract](02-schema-and-provenance-contract.md)
- [Governance and Mirror Alignment](03-governance-and-mirror-alignment.md)

## Reference Reading

- **Maintenance Loop**: `docs/reference/research/claude-skill-authoring-guide.md` and `docs/roadmap/external/claude-skills/reference-implementations-notes.md` for ingest/absorb/cleanup/query pattern references
- **Reviewable Writes**: `skill/workflows/wiki.md` and `docs/architecture/skill-and-agent-interface-contract.md` for current reviewed-mutation posture
- **Runtime anchors**: `README.md` and `docs/reference/claude-code-wiki-quickstart.md` for shipped runtime read/write posture and daemon optimization framing

## Helper Questions for Future Deep Planning

- If an agent wants to “absorb” knowledge, which shipped commands and reviewed write path does that actually compose today?
- Which parts of cleanup are already supported by `lint`, and which parts remain agent-side reasoning only?
- What exact unsupported/deferred wording should mirrors use so they never imply silent write capability?

## Deferred / Open Questions

- Should `absorb` remain a pure workflow concept long-term, or eventually become a CLI surface?
- What threshold should define a “stale” page for cleanup decisions?
- Which maintenance-loop heuristics belong in docs only, and which eventually deserve governance tests?
