# Session Note Example

Use this shape when filing a Claude/OpenCode session as durable Markdown before ingest.

```markdown
---
title: "Agent workflow refinement"
date: "2026-04-25"
tags:
  - snowiki
  - agent-workflow
confidence: medium
source: "agent session summary"
---

# Agent workflow refinement

## Durable decisions

- Snowiki skill intents are workflow labels, not `snowiki` subcommands or independent slash commands.
- Raw session exports are summarized into Markdown before ingest.

## Evidence

- `skill/SKILL.md`
- `skill/references/wiki-workflow.md`

## Open questions

- Which deferred workflow should become a runtime spec first?

## Follow-ups

- Run `snowiki ingest path/to/this-note.md --rebuild --output json`.
```
