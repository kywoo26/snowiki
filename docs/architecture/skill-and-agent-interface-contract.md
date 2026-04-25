# Skill and Agent Interface Contract

This document is the **canonical contract owner** for the interface between agents (LLMs, automated tools) and the Snowiki system. It defines the normative vocabulary, artifact classes, and governance rules for all agent-facing surfaces.

## 1. Normative vs. Informative Surfaces

To maintain a single source of truth, Snowiki distinguishes between normative (authoritative) and informative (reference) surfaces.

### 1.1 Normative Surfaces (The Truth)
- **This Document**: The single normative owner of the interface contract and vocabulary.
- **`snowiki` CLI**: The authoritative runtime contract. The behavior of the installed CLI defines the current system capabilities.
- **CLI JSON Output**: The machine-readable contract for tool integration (`--output json`).
- **`docs/architecture/source-vault-compiled-taxonomy.md`**: The canonical layer taxonomy for source roots, raw provenance, normalized records, compiled pages, indexes, and queues.

### 1.2 Informative Surfaces (The Mirrors)
- **`README.md`**: High-level overview and quick start. Mirrors runtime truth for human consumption.
- **`skill/SKILL.md`**: Workflow layer and tool definitions for specific agent platforms (e.g., Claude Code). It is a reference layer, not a runtime contract.
- **`skill/references/wiki-workflow.md`**: Detailed wiki skill intent mapping. This is informative and must stay verified against the CLI.

> **Governance Rule**: Any change to a normative fact must be updated in the canonical owner first. Mirror surfaces must be updated in the same PR to prevent drift.

## 2. Artifact Classes

Snowiki defines four distinct classes of artifacts that agents interact with.

### 2.1 Command
An atomic unit of execution provided by the `snowiki` CLI. Commands are the primary mechanism for mutation and retrieval.
- **Examples**: `ingest`, `rebuild`, `query`, `recall`, `lint`, `status`, `prune`, `export`, `fileback`, `benchmark`, `benchmark-fetch`, `daemon`, `mcp`.
- **Contract**: Commands must provide deterministic behavior and, where applicable, machine-readable JSON output.

### 2.2 Skill
A higher-level orchestration layer that bundles multiple commands and logic into a cohesive workflow for an agent.
- **Examples**: The `wiki` skill, the `recall` skill.
- **Contract**: Skills are consumers of the CLI contract. They may not silently redefine system capabilities or bypass CLI-level validations.

### 2.3 Memory
The persistent state of the Snowiki system, including raw sources, normalized records, compiled wiki pages, index snapshots, and session history.
- **Examples**: `raw/`, `normalized/`, `compiled/`, `index/`, session records.
- **Contract**: Memory is the accepted runtime state for retrieval once data has entered Snowiki's storage pipeline. Source roots and raw provenance remain evidence; compiled pages are derived wiki memory. Agents interact with memory primarily through CLI commands or read-only MCP surfaces.

### 2.4 Control-Plane Queue
A durable runtime artifact for pending mutation intent that has not entered accepted memory.
- **Example**: `$SNOWIKI_ROOT/queue/proposals/pending/<proposal_id>.json`.
- **Contract**: Queue artifacts are inspectable proposal state, not source truth, compiler input, compiled output, or index content. They must not affect rebuild/query results until an approved CLI apply path succeeds.

## 3. Vocabulary

The following terms have exact meanings within the Snowiki ecosystem.

### 3.1 Policy
The Snowiki-owned declaration of contract intent and minimum requirements for agent behavior, data access, mutation rights, and approval posture.

Policy is defined by this contract and repo governance surfaces such as `AGENTS.md`. It tells hosts and skills what Snowiki means by visibility, mutation, and approval.

Snowiki owns the intent; the runtime and host harness remain the final enforcers. A host may enforce the same policy more strictly, but must not treat unsupported or disallowed capabilities as implicitly allowed.

### 3.2 Visibility
The scope of data accessible to an agent at a given time.

Snowiki visibility is declared per artifact zone:
- **Source Visibility**: Access to external `source_root`/`source_path` material or Snowiki-managed `raw/` provenance snapshots.
- **Compiled Visibility**: Access to `compiled/` pages (generated wiki memory).
- **Session Visibility**: Access to the `sessions/` zone (active or frozen session logs).

Each zone uses the same minimum visibility states:
- **Hidden**: The host does not expose the zone to the agent.
- **Metadata-Only**: The host may expose identifiers, titles, paths, or summaries, but not full contents.
- **Read**: The host may expose contents for retrieval and reasoning.
- **Propose-Mutate**: The agent may prepare or request a mutation through an approved runtime path, but the mutation is not effective until host/runtime approval is satisfied.

Snowiki declares these states so skills and agents can reason about access consistently. Hosts may collapse states into a stricter subset, but must not invent broader effective access than the runtime actually provides.

The current shipped runtime does not require a root-internal `sources/` authoring directory. Durable source material may live in external project docs, Obsidian vaults, session-note directories, or other filesystem roots recorded as source provenance. See `docs/architecture/source-vault-compiled-taxonomy.md` for the normative layer taxonomy.

### 3.3 Approval
A gate on whether a requested mutation may become effective.

Snowiki approval semantics are intentionally minimal:
- **Not Required**: The action is allowed without an additional approval gate.
- **Required**: The action may be proposed, but a human or host-controlled approval step must occur before it is applied.
- **Denied**: The action must not be applied through the current interface.

Snowiki assumes a human-in-the-loop posture for operations that modify durable knowledge unless the authoritative runtime explicitly defines a narrower or broader allowed path. In the current verified contract, mutation remains CLI-mediated and the MCP surface remains read-only.

For autonomous operation, approval must not be confused with interrupting the agent's primary task. A review-required proposal may be accepted into a control-plane queue as a successful, non-blocking outcome while remaining unapplied. The queue records mutation intent; approval controls whether that intent becomes durable knowledge.

Approval semantics describe contract intent, not a full approval engine. Hosts may implement stricter gates or broader review workflows, but they should map those workflows back to Snowiki's minimum semantics rather than redefine them.

### 3.4 Checkpoint
A checkpoint is a coarse-grained, point-in-time identity for resumable continuity state. It is a contract concept for naming and validating an interruption boundary, not a promise of runtime rollback, replay, or scheduled continuation.

Minimum checkpoint identity fields are:
- **`checkpoint_id`**: a host- or runtime-assigned opaque identifier unique within its scope
- **`session_id`**: the session whose continuity state is being described
- **`created_at`**: the timestamp when the checkpoint was emitted
- **`scope`**: either `session` or `artifact`, depending on what the host/runtime can safely name

A checkpoint may refer to:
- a full session continuity point
- a partial artifact continuity point
- an interruption boundary emitted before a host stops, compacts, or archives active work

Checkpoint identity is intentionally coarse. It exists so agents, skills, and hosts can refer to continuity state consistently without implying a workflow engine or durable rollback implementation.

### 3.5 Resumable State Envelope
A resumable state envelope is the machine-readable payload that describes whether a previously interrupted session may be continued.

The envelope follows Snowiki's existing coarse JSON-envelope style: it is a descriptive payload for interoperability, not an execution protocol.

Minimum envelope fields are:
- **`envelope_version`**: contract version for the resumable envelope format
- **`checkpoint_id`**: the referenced checkpoint identity
- **`session_id`**: the continuity target session
- **`session_status`**: coarse session state using runtime-aligned vocabulary such as `active`, `closed`, `incomplete`, or `archived`
- **`interruption_reason`**: a coarse reason such as host stop, compaction, export boundary, or unsupported continuation
- **`resume_from`**: optional continuity metadata naming the prior session or continuity anchor when one exists
- **`host_capabilities`**: the effective host/runtime capability summary relevant to resumption
- **`invalidated`**: whether the envelope is known to be unusable
- **`invalidation_reason`**: why the envelope is unusable, if known

The envelope may include host-specific metadata, but those extensions must not change the meaning of the minimum fields above.

### 3.6 Resume
Resume is the contract-level act of attempting to continue from a resumable state envelope or checkpoint identity.

Within Snowiki's current verified contract, `resume` means only that continuity metadata can be named and reasoned about. It does **not** imply any of the following shipped runtime features:
- a `snowiki resume` CLI command
- a scheduler or background job runner
- automatic retries
- transcript replay
- workflow rehydration beyond what the host/runtime explicitly supports today

Resume is therefore a visibility and compatibility concept first. A host or workflow may expose continuity affordances, but it must not claim that Snowiki itself ships a general resume engine unless the authoritative runtime contract adds one.

### 3.7 Invalidation and Versioning
Resumable state is only usable when the envelope and its referenced continuity target are still compatible.

Minimum rules:
- **Version match required**: `envelope_version` must be understood by the consuming host/runtime. Unknown major versions are invalid.
- **Checkpoint identity must resolve**: if `checkpoint_id` or `session_id` cannot be resolved, the envelope is invalid.
- **Session terminal states win**: envelopes for sessions that are conclusively `closed` or otherwise finalized must be treated as non-resumable unless the authoritative runtime defines a narrower exception.
- **Compaction/archive boundaries may invalidate detail**: if a host compacts, freezes, archives, or exports a session in a way that discards required continuation detail, the envelope must be marked invalid rather than heuristically replayed.
- **Host/runtime drift invalidates**: if the current host capability set is narrower than the one required to honor the envelope, the envelope is invalid for that host.
- **No silent downgrade to execution**: an invalid or stale envelope may still be surfaced as metadata, but it must not be treated as runnable continuation state.

Versioning and invalidation rules exist to make stale continuity state explicitly unusable rather than ambiguously "best effort."

### 3.8 Host Capability Mapping
Snowiki policy intent must map onto concrete host/runtime capabilities without changing the meaning of the policy itself.

Minimum mappings:
- **Read capability**: May be satisfied by CLI JSON output or the read-only MCP surface.
- **Mutation capability**: Must flow through the authoritative CLI/runtime path, not through MCP.
- **Approval capability**: May be implemented by the host harness, a human reviewer, or a runtime-controlled confirmation step.
- **Visibility capability**: May be narrowed by the host per zone, but not broadened beyond what the runtime actually exposes.

This keeps Snowiki as the owner of policy vocabulary while acknowledging that hosts differ in what they can actually enforce or expose.

### 3.9 Unsupported Host
A host is unsupported for a given policy state when it cannot faithfully express or enforce Snowiki's minimum contract requirements.

When that happens, Snowiki's required behavior is:
- unsupported capabilities are treated as unavailable, not silently approximated
- the effective policy must degrade to the safest supported mode
- mutation must remain on the CLI-authoritative path
- MCP remains read-only
- resumable state envelopes may be exposed as metadata-only continuity records, but must be marked unusable when the host cannot honor their version or required capabilities

Example: if a host cannot represent `Propose-Mutate` plus `Required` approval, it must fall back to read-only behavior or deny the action rather than granting unchecked writes.

## 4. Current CLI-to-MCP Bridge Contract

The current CLI↔MCP seam is intentionally thin.

- **CLI bridge entrypoint**: `snowiki mcp serve --stdio` is the only supported CLI shape for the MCP bridge.
- **Bridge responsibility**: `src/snowiki/cli/commands/mcp.py` only parses that command, creates the server, and hands stdio streams to the MCP transport.
- **Behavior owner**: the read-only MCP behavior itself lives in `src/snowiki/mcp/server.py`, not in the CLI parser layer.

This means the bridge is a transport shim, not a shared execution adapter. The CLI command does not translate MCP tool calls into `snowiki query`, `snowiki recall`, or other CLI subcommands.

It also does **not** hydrate project-root state by itself. Running `snowiki mcp serve --stdio` against a populated Snowiki root still creates an empty read-only facade unless session records and compiled page data are injected by the host/runtime. In the current verified contract, non-empty MCP search, recall, topic, session, and graph results therefore depend on explicit host/runtime seeding rather than implicit CLI root loading.

### 4.1 Verified MCP tool and resource surface

The current MCP server exposes only these read-only tools:

- `search`
- `recall`
- `get_page`
- `resolve_links`

The current MCP server exposes only these read-only resource families:

- `graph://current`
- `topic://<slug>`
- `session://<session-id>`

Write-oriented names such as `edit`, `ingest`, `merge`, `sync`, `status`, and `write` are not exposed as MCP tools. If called through the MCP tool dispatch path, they must be rejected as read-only violations rather than approximated.

### 4.2 Overlapping CLI and MCP semantics

Some concepts overlap across the CLI and MCP surfaces, but the shipped contract does not currently normalize them into one identical interface family.

- **CLI `query`** is the authoritative machine-facing retrieval command for local runtime use and emits the CLI JSON envelope (`ok`, `command`, `result`).
- **MCP `search`** and **MCP `recall`** expose read-only retrieval through JSON-RPC tool calls and return MCP-shaped `structuredContent` plus text content.
- **CLI `recall`** and **MCP `recall`** overlap conceptually, but MCP routing still terminates inside the read-only facade instead of invoking the CLI command implementation.
- **CLI-only commands** such as `fileback`, `benchmark`, `daemon`, `status`, and `export` have no MCP equivalent. They are runtime-only surfaces and do not flow through the MCP bridge.

This difference is intentional in the current verified contract and must be documented explicitly rather than hidden behind “shared adapter” language.

### 4.3 Hydration and payload expectations

Current hydration expectations are intentionally narrow:

- **Tool calls** return structured JSON payloads encoded both as MCP `structuredContent` and as a JSON text block in `content`.
- **Resource reads** return a `contents` array with `application/json` payload text and the originating resource `uri`.
- **Bridge startup** does not automatically load data from `SNOWIKI_ROOT` or another project root; an unseeded bridge may legitimately return zero hits and an empty graph while still exposing the full read-only tool/resource surface.
- **Topic resources** hydrate summary metadata (`path`, `slug`, `summary`, `title`), not full page bodies.
- **Session resources** hydrate the normalized session payload by id or path.
- **Graph resources** hydrate node/edge summaries for the current read-only wiki graph.

Unknown tools, invalid arguments, or unsupported resource URIs must fail explicitly inside the read-only facade contract; they must not silently widen capabilities or fall through to mutation paths.

## 5. Governance and Evolution

- **CLI-First**: The CLI remains the final arbiter of what is possible.
- **Read-Only MCP**: The MCP surface is strictly read-only for search and retrieval. Mutation must flow through the CLI.
- **No Silent Redefinition**: Skills and workflows must not redefine core Snowiki concepts or behaviors.
- **Policy Intent vs. Host Enforcement**: Snowiki defines policy semantics and minimum requirements; host harnesses and runtimes enforce the effective behavior and may be stricter.
- **Unsupported Means Unavailable**: If a host cannot honor a declared policy state, the capability must be denied or degraded to a safer supported mode.
