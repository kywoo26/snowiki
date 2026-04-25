# Claude Code `/wiki` Quickstart

This guide is the shortest truthful path to using Snowiki’s current parity-plus `/wiki` workflow. For the authoritative mapping of skill routes to runtime commands, see the [Wiki Route Contract](../roadmap/step3_wiki-skill-design/01-wiki-route-contract.md).

The runtime truth is still the installed `snowiki` CLI. The Claude Code `/wiki` skill should mirror these commands and behaviors rather than invent a separate backend.

## 1. Install from a checkout

```bash
uv tool install --from . snowiki
snowiki --help
```

If you also want the Claude Code `/wiki` skill installed locally, place this repo's packaged skill at `~/.claude/skills/wiki/` so Claude Code can load `skill/SKILL.md` from that install path.

If you are iterating from the repository checkout instead of a tool install, use `uv run snowiki ...` in the same examples below.

## 2. Optional: start the daemon for faster repeated reads

The daemon is an optimization for `query` and `recall`, not a separate runtime truth and not a correctness requirement.

```bash
snowiki daemon start
snowiki daemon status
```

If the daemon is already reachable, the `/wiki` read path can prefer warm daemon-backed reads. If not, Snowiki falls back to the canonical CLI read path.

## 3. First useful commands

### Ingest

```bash
snowiki ingest /path/to/note.md --output json
snowiki ingest /path/to/docs/ --rebuild --output json
```

Markdown files and directories are the primary ingest surface. Convert Claude/OpenCode session exports into Markdown notes before ingesting them.

### Query

```bash
snowiki query "What do I know about the fileback flow?" --output json
```

### Recall

```bash
snowiki recall yesterday --output json
```

### Status

```bash
snowiki status --output json
```

### Lint

```bash
snowiki lint --output json
```

`status` gives source freshness summary counts. `lint --output json` gives actionable source findings such as `source.modified`, `source.missing`, `source.untracked`, `source.invalid_metadata`, and agent-readable `source.rename_candidate` diagnostics when a missing source has an exact-hash untracked rename candidate.

### Source prune

Source prune is dry-run-first and handles missing-source normalized Markdown records plus raw snapshots that become unreferenced.

```bash
snowiki prune sources --dry-run --output json
snowiki prune sources --delete --yes --all-candidates --output json
```

Review the dry-run candidates before deletion. Do not treat source prune as source rename repair, dead-wikilink cleanup, or multi-source cascade gardening.

## 4. Reviewable file-back flow

`fileback` is current shipped behavior. It is CLI-only, reviewable, and derived: preview first, then apply a reviewed proposal.

### Preview a filed-back answer

```bash
snowiki fileback preview \
  "What did we ship?" \
  --answer-markdown "We shipped the reviewable fileback flow." \
  --summary "Reviewed answer for the current shipped behavior." \
  --evidence-path compiled/summaries/example.md \
  --output json > /tmp/fileback-preview.json
```

Review the JSON proposal before applying it, or queue it when autonomous work should continue without applying immediately.

### Queue a pending proposal

```bash
snowiki fileback preview \
  "What did we ship?" \
  --answer-markdown "We shipped the reviewable fileback flow." \
  --summary "Reviewed answer for the current shipped behavior." \
  --evidence-path compiled/summaries/example.md \
  --queue \
  --output json
```

Queued proposals are written under the active Snowiki root as `queue/proposals/pending/*.json`. They are control-plane proposal artifacts, not applied writes.

### Inspect queued proposals

```bash
snowiki fileback queue list --output json
snowiki fileback queue list --status applied --output json
snowiki fileback queue show fileback-proposal-0123456789abcdef --output json
snowiki fileback queue show fileback-proposal-0123456789abcdef --verbose --output json
```

### Apply or reject a queued proposal

```bash
snowiki fileback queue apply fileback-proposal-0123456789abcdef --output json
snowiki fileback queue reject fileback-proposal-0123456789abcdef \
  --reason "Needs stronger evidence" \
  --output json
```

Queue apply uses the same reviewed raw/normalized/rebuild path as file-based apply. Successful applies move the envelope to `queue/proposals/applied/`; failed applies move it to `queue/proposals/failed/`; rejected proposals move to `queue/proposals/rejected/`.

### Prune terminal queue artifacts

```bash
snowiki fileback queue prune --status applied --keep 50 --output json
snowiki fileback queue prune --status rejected --older-than 30d --delete --yes --output json
```

Prune is dry-run by default. Actual deletion requires `--delete --yes`, and the default bounded retention policy is count-based rather than a hidden age TTL.

### Auto-apply only runtime-proven low-risk proposals

```bash
snowiki fileback preview \
  "What did we ship?" \
  --answer-markdown "We shipped the reviewable fileback flow." \
  --summary "Reviewed answer for the current shipped behavior." \
  --evidence-path compiled/summaries/example.md \
  --queue \
  --auto-apply-low-risk \
  --output json
```

This still queues first and only applies if deterministic runtime policy checks prove the proposal is a new low-risk manual question record with in-root evidence and non-colliding write paths.

### Apply a reviewed proposal file

```bash
snowiki fileback apply \
  --proposal-file /tmp/fileback-preview.json \
  --output json
```

This writes through Snowiki’s reviewed raw/normalized flow and rebuilds the generated compiled question page. Queueing a proposal does not do this unless queue apply or runtime low-risk auto-apply succeeds. Fileback does not grant MCP write support.

## 5. What is deferred

These remain deferred workflow ideas, not shipped runtime behavior:

- `sync`
- standalone `edit`
- standalone `merge`
- graph-oriented workflows

Phase 5 planning may use narrow edit/merge semantics only when they are part of reviewed source-gardening proposals such as rename assistance, dead-wikilink cleanup, or cascade cleanup. Do not treat those broader workflows as shipped runtime commands until the CLI exposes them.

Do not document or rely on them as if they already ship.

## 6. Current `/wiki` mental model

- use `ingest`, `query`, `recall`, `status`, `lint`, `prune sources`, and `fileback` today
- prefer daemon-backed reads only when a daemon is already available
- use CLI JSON output for automation and reliable machine-readable contracts
- treat the read-only MCP surface as retrieval-only
