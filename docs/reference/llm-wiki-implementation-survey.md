# LLM Wiki Implementation Survey

This survey records the reference research behind Snowiki's Markdown-first ingest redesign. It is supporting material for `docs/architecture/llm-wiki-ingest-redesign.md`.

## Canonical Pattern

Karpathy's LLM Wiki pattern describes a persistent, LLM-maintained Markdown wiki that sits between the user and raw sources. The key distinction from classic RAG is that knowledge is compiled into durable pages once, then queried and maintained over time.

Common structure:

```text
raw/        immutable sources
wiki/       generated or maintained Markdown pages
schema      agent-readable operating rules
index.md    content catalog and navigation entry
log.md      chronological operation record
```

Common operations:

- ingest: read a new source and integrate it into the wiki.
- query: answer from compiled wiki pages, not only raw chunks.
- lint: detect broken links, stale claims, contradictions, missing pages, and orphan pages.
- writeback: save durable answers or decisions back into the wiki.

## Surveyed Implementations

### nashsu/llm_wiki

Repository: `https://github.com/nashsu/llm_wiki`

High-prominence desktop implementation. It keeps the Karpathy raw/wiki/schema model but expands it into a Tauri app with persistent queueing, graph views, review, web clipping, and optional vector retrieval.

Transferable patterns:

- Two-step ingest: analysis first, generation second.
- SHA256 ingest cache that verifies previously written files still exist before declaring a cache hit.
- Persistent ingest queue with retry and crash recovery.
- Recursive folder import preserving directory context.
- Source traceability via `sources[]` frontmatter.
- Merge existing and incoming `sources[]` on re-ingest instead of clobbering provenance.
- Structural wikilink cleanup instead of substring cleanup.

Use for Snowiki: strong secondary implementation reference for operational mechanics. Do not copy the full desktop/graph/research product scope into the first Snowiki ingest PR.

### atomicmemory/llm-wiki-compiler

Repository: `https://github.com/atomicmemory/llm-wiki-compiler`

CLI-oriented knowledge compiler. It is one of the closest references for Snowiki's desired CLI shape.

Transferable patterns:

- `ingest` copies/fetches sources into a source directory.
- `compile` performs incremental two-phase compilation.
- Changed-source detection is hash based.
- Generated pages use YAML frontmatter and `[[wikilinks]]`.
- Candidate review queue can keep generated pages out of `wiki/` until approved.
- Query answers can be saved back as wiki pages.
- MCP server is layered on top of CLI-like operations.

Use for Snowiki: strong reference for CLI command boundaries, review queues, provenance, and delayed MCP integration.

### SamurAIGPT/llm-wiki-agent

Repository: `https://github.com/SamurAIGPT/llm-wiki-agent`

Agent-skill implementation for Claude Code, Codex, Gemini CLI, and similar tools.

Transferable patterns:

- Agent-readable `AGENTS.md` / `CLAUDE.md` schema.
- Natural-language triggers for ingest/query/lint/graph.
- `raw/` source documents and `wiki/` maintained Markdown pages.
- `index.md`, `log.md`, `overview.md`, `sources/`, `entities/`, `concepts/`, and `syntheses/` layout.
- Graph artifacts cached separately from Markdown pages.

Use for Snowiki: reference for skill UX and natural-language workflows over deterministic file/CLI operations.

### Ar9av/obsidian-wiki

Repository: `https://github.com/Ar9av/obsidian-wiki`

Obsidian-oriented agent wiki framework.

Transferable patterns:

- Vault-native Markdown workflow.
- `_raw/` staging and manifest tracking.
- Multi-agent compatibility.
- Optional QMD search.
- Explicit ingest/extract/resolve/schema workflow.

Use for Snowiki: reference for Obsidian-compatible frontmatter, vault organization, and skill instructions.

### Pratiyush/llm-wiki

Repository: `https://github.com/Pratiyush/llm-wiki`

Productionized CLI/static-site/MCP-oriented project with session-ingest lineage.

Transferable patterns:

- Session exports converted into Markdown artifacts.
- `sync`, `build`, `serve`, and `lint` command surface.
- AI-readable siblings such as text and JSON artifacts.
- Governance around publishing and documentation.

Use for Snowiki: useful reference for keeping session-export ingestion above or alongside Markdown output instead of making chat exports the core source model.

### xoai/sage-wiki

Repository: `https://github.com/xoai/sage-wiki`

Scale-oriented wiki implementation with hybrid retrieval and MCP integration.

Transferable patterns:

- Multi-format source support.
- Obsidian vault overlay.
- Tiered compilation.
- Compile-on-demand through agent tooling.
- Hybrid BM25/vector retrieval and graph expansion.

Use for Snowiki: later-stage reference for scale, not Phase 1 scope.

### lucasastorian/llmwiki

Repository: `https://github.com/lucasastorian/llmwiki`

Hosted/MCP implementation. Users upload documents, connect Claude through MCP, and let Claude write the wiki.

Transferable patterns:

- MCP tools expose `search`, `read`, `write`, and `delete` over a knowledge vault.
- Raw uploaded documents and wiki pages are distinct layers.
- Server handles storage/search while Claude handles synthesis and maintenance.

Use for Snowiki: external reference only. Snowiki does not ship MCP write support, and MCP write/delete is not part of Phase 3 CLI queue hardening.

### obsidian-llm-wiki-local variants

Repositories include `kytmanov/obsidian-llm-wiki-local` and related forks.

Transferable patterns:

- Fully local pipeline.
- Markdown notes in `raw/`.
- Draft review before publish.
- Manual edit protection.
- File watcher as optional automation.
- No-vector default in some variants; `index.md` is sufficient at small scale.

Use for Snowiki: reference for local-first review loops and avoiding vector-first complexity.

### doum1004/llmwiki-cli

Repository: `https://github.com/doum1004/llmwiki-cli`

Small storage-first CLI.

Transferable patterns:

- Explicit `init`, `write`, `index`, `log`, `search`, `lint`, `backlinks`, and `orphans` commands.
- Pure filesystem/git backend.
- Graph visualization as derived output.

Use for Snowiki: reference for small, composable CLI subcommands.

## Adjacent Knowledge Tools

### Obsidian, Foam, Dendron, Logseq

These tools reinforce that Markdown identity, links, frontmatter, backlinks, and rename behavior should be treated as first-class data rather than incidental text.

Implications for Snowiki:

- Parse frontmatter during ingest.
- Treat `[[wikilinks]]` as graph edges.
- Avoid substring-based link cleanup.
- Keep file identity and display title separate.
- Be careful with rename/move semantics.

### Khoj, AnythingLLM, DocsGPT, Open WebUI Knowledge

These are stronger references for document ingestion and RAG than for Karpathy-style compiled wikis.

Implications for Snowiki:

- Useful for connector ideas and document parsing boundaries.
- Do not make vector DBs the source of truth.
- Treat semantic retrieval as an optional acceleration layer over durable Markdown/provenance.

## Snowiki-Specific Conclusions

Snowiki's strongest path is not to become a desktop clone or a hosted RAG system. It should become a deterministic CLI substrate for LLM-maintained Markdown knowledge.

Core product direction:

- CLI is runtime truth.
- Skills and MCP mirror CLI contracts.
- Markdown ingest is first-class.
- Raw/source provenance is explicit.
- Compiled/search artifacts are derived and rebuildable.
- Lexical-first query is shipped before semantic/graph expansion.
- LLM synthesis belongs in skills/workflows unless and until the deterministic core contract is stable.

## Recommended First PR Boundary

Include:

- Markdown file/directory ingest.
- Safe recursive Markdown discovery.
- Source root + relative path identity.
- Content hash upsert.
- Frontmatter preservation/promotion.
- `--rebuild` option.
- JSON output with `rebuild_required`.
- Tests and docs.

Defer:

- Graph extraction.
- Vector search.
- MCP writes.
- Watchers/daemon automation.
- LLM compilation/generation inside core ingest.
- Review queue.
- Deep research.
- Pruning deleted files unless explicitly requested through a separate command or flag.
