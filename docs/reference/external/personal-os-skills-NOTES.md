# personal-os-skills — Snowiki Analysis Notes

## Repository
- https://github.com/ArtemXTech/personal-os-skills
- Setup doc: https://github.com/ArtemXTech/personal-os-skills/blob/main/docs/memory-skills-setup.md

## What this is
The strongest public example of installable skill packaging and workflow-backed memory operations for a local agent environment.

## Key patterns to preserve for Snowiki

### Installable skill packaging
- explicit skill bundle structure
- documented installation/setup
- reusable workflow scripts

### Schema-backed and frontmatter-aware behavior
- metadata discipline is part of the workflow, not a hidden implementation detail.

### Multiple retrieval modes
- temporal / topic / graph-style routes are separated rather than collapsed into one opaque command.

### Vault-first operational posture
- local files remain the source of truth.
- sync/index refresh hooks exist to keep derived artifacts fresh.

## What Snowiki should not copy literally
- Obsidian-specific operational assumptions should remain implementation examples, not core Snowiki product truth.

## Relevance to Snowiki steps
- Step 3: Wiki skill design

## Concrete Snowiki takeaways

1. Skill bundles should remain explicit, inspectable, and installable.
2. Schema files and workflow docs are worth preserving as first-class artifacts.
3. Topic/temporal/graph separations are useful for agent ergonomics but should remain subordinate to Snowiki's canonical CLI contract.
