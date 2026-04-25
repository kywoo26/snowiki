# snowiki ❄️

A personal wiki that compounds knowledge like a snowball.

Snowiki’s current shipped runtime is **CLI-first**. The installed `snowiki` command is the authoritative runtime contract; the Claude Code `/wiki` skill is a workflow layer that should mirror the CLI rather than redefine it.

## Quick Start

This README is an **informative mirror** of the canonical contract at `docs/architecture/skill-and-agent-interface-contract.md` and the [Wiki Route Contract](docs/roadmap/step3_wiki-skill-design/01-wiki-route-contract.md).

```bash
# 1. Install Snowiki from a checkout
uv tool install --from . snowiki

# 2. Inspect the shipped command surface
snowiki --help

# 3. Use the current runtime directly
snowiki ingest /path/to/README.md --output json
snowiki ingest /path/to/docs/ --output json
snowiki ingest /path/to/docs/ --rebuild --output json
snowiki rebuild
snowiki query "What do I know about X?" --output json
snowiki recall yesterday --output json
snowiki status --output json
snowiki lint --output json
snowiki prune sources --dry-run --output json
```

Markdown files and directories are the primary ingest surface. Claude/OpenCode session exports should be converted into Markdown notes by an agent or skill workflow, then ingested with `snowiki ingest <note-or-directory>`.

For the Claude Code `/wiki` workflow, use this README as the short entrypoint and follow the dedicated guide at [`docs/reference/claude-code-wiki-quickstart.md`](docs/reference/claude-code-wiki-quickstart.md). It covers install-from-checkout, optional daemon startup for faster reads, and the current `fileback preview/queue/apply` flow.

If you are working from a development checkout instead of a tool install, run the same commands as `uv run snowiki ...`.

## Current shipped CLI surface

The current runtime exposes these top-level commands:

### Primary Current Routes
- `snowiki ingest`
- `snowiki query`
- `snowiki recall`
- `snowiki status`
- `snowiki lint`
- `snowiki prune`
- `snowiki fileback`

### Advanced Passthrough
- `snowiki export`
- `snowiki benchmark`
- `snowiki daemon`
- `snowiki mcp`

### Shipped CLI Support
- `snowiki rebuild` (not a primary `/wiki` route)

## Claude Code `/wiki` status

The `/wiki` skill should currently mirror this shipped surface for everyday use:

- current: `ingest`, `query`, `recall`, `status`, `lint`, `prune sources --dry-run`, `prune sources --delete --yes --all-candidates`, `fileback preview`, `fileback preview --queue`, `fileback preview --queue --auto-apply-low-risk`, `fileback queue list`, `fileback queue show`, `fileback queue apply`, `fileback queue reject`, `fileback queue prune`, `fileback apply`
- optimization, not separate runtime truth: daemon-backed warm reads for query/recall when a daemon is already reachable
- Phase 6 planning: Claude/OpenCode/OMO agent workflows over the shipped CLI truth, including lifecycle skill routes such as `/wiki-start`, `/wiki-progress`, `/wiki-finish`, and `/wiki-health` that expand to current CLI sequences rather than new runtime commands
- deferred unless explicitly accepted by runtime spec: standalone `sync`, standalone `edit`, standalone `merge`, graph-oriented workflows

Do not treat daemon-backed reads, qmd lineage, or older vault-layout docs as a separate product contract.

## Machine-usable surfaces today

- CLI JSON output via `snowiki ... --output json`
- read-only MCP via `snowiki mcp`

Mutation remains CLI-mediated. MCP write support is not shipped. Source cleanup is report-first through `status`/`lint` and dry-run-first through `snowiki prune sources`; destructive source pruning requires `--delete --yes --all-candidates`. `lint --output json` may include agent-readable source gardening diagnostics such as exact-hash rename candidates before a missing source is pruned. Autonomous writeback queues are control-plane proposal artifacts until applied through a documented CLI path. The CLI queue lifecycle supports pending/applied/rejected/failed proposal states, dry-run-first terminal pruning, and runtime-owned low-risk auto-apply policy before any broader mutation surface is considered.

## Design Principles

1. **CLI truth first** — docs and skills mirror the installed runtime instead of inventing a parallel `/wiki` backend
2. **Compilation, not ad-hoc mutation** — durable knowledge flows through Snowiki storage and rebuild paths
3. **Reviewable writes** — `fileback apply` requires a reviewed proposal from `fileback preview`
4. **Search-strategic** — lexical-first retrieval is shipped now; hybrid/semantic work remains deferred
5. **Performance where it matters** — warm daemon reads are an optimization for repeated read paths, not a requirement for correctness

## Related

- `docs/architecture/skill-and-agent-interface-contract.md` — canonical agent/runtime contract
- `docs/reference/claude-code-wiki-quickstart.md` — step-by-step Claude Code `/wiki` adoption guide
- [qmd](https://github.com/tobi/qmd) — lineage/reference material, not the current Snowiki runtime
