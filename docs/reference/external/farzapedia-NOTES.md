# Farzapedia — Snowiki Analysis Notes

## Public artifacts
- Strongest artifact: https://gist.github.com/farzaa/c35ac0cfbeb957788650e36aabea836d
- Adjacent public site: https://farza.com/knowledge
- Repository exists but is not the strongest durable source: https://github.com/andepants/farzapedia

## What this is
An explicit derivative of the personal/wiki-for-agents pattern, with a richer `/wiki` command family and a more operationally explicit maintenance workflow.

## Key patterns to preserve for Snowiki

### Expanded `/wiki` workflow family
- `/wiki ingest`
- `/wiki absorb`
- `/wiki query`
- `/wiki cleanup`
- `/wiki breakdown`
- `/wiki reorganize`
- `/wiki status`

This is valuable as a **future-facing workflow surface**, especially for Step 3's maintenance-loop thinking.

### Maintenance-loop seriousness
- absorb/cleanup/breakdown are treated as explicit operations rather than implicit agent behavior.
- quality control is part of ongoing wiki upkeep.

### Artifact organization
- `_index.md`
- backlink/state files
- absorb/audit logs

These are useful references for how an agent-maintained wiki can stay inspectable over time.

## What Snowiki should not copy literally
- The taxonomy is more opinionated and voice-heavy than Snowiki's current contract needs.
- It is stronger as a workflow/UX reference than as a canonical runtime-contract source.

## Relevance to Snowiki steps
- Step 3: Wiki skill design

## Concrete Snowiki takeaways

1. Treat absorb/cleanup as named workflow ideas even if they remain deferred from the shipped CLI.
2. Preserve inspectable maintenance artifacts.
3. Keep `/wiki query` reading compiled knowledge first, not raw source by default.
