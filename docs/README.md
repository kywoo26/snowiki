# Docs Structure

This docs tree is intentionally split into a small **key path** and a larger **reference/archive** surface so future work does not get lost in legacy or supporting material.

## Key path (start here)

If you need current truth and next action, read only these first:

1. `docs/roadmap/STATUS.md`
2. `docs/roadmap/main-roadmap.md`
3. the relevant `docs/roadmap/step*/roadmap.md`
4. `docs/architecture/current-retrieval-architecture.md`
5. `docs/architecture/skill-and-agent-interface-contract.md`

Everything else is supporting rationale, evidence, or archive.

## Directory roles

### `docs/roadmap/`

This is the **canonical planning and analysis surface** for the current research and roadmap program.

Use it for:
- active track status
- step-by-step analysis
- step roadmaps and non-goals
- promotion criteria for later execution planning
- roadmap-owned external notes used by those steps

If a planning decision changes, update `docs/roadmap/` first.

### `docs/architecture/`

This is the **contract layer**.

Use it for:
- current runtime truth
- architecture constraints
- stable interface contracts that future work must obey

This directory should stay small. If a doc is mostly rationale, comparison, translation, or assessment, it belongs in `docs/reference/` instead.

### `docs/reference/`

This is the **supporting/reference layer**.

Use it for:
- explanatory architecture rationale beyond the key contracts
- external system comparisons
- lineage studies
- design-oriented research syntheses
- product-direction context
- isolated translation mirrors

These docs support decisions; they do not own current planning state.

### `docs/roadmap/external/`

This is the **roadmap-owned external evidence layer**.

Use it for:
- deep notes on external repos, systems, and references that directly feed the active roadmap steps
- reference extraction work that belongs to the current roadmap program

These notes support the roadmap, but they are not part of the default key path unless a step explicitly sends you there.

### `docs/roadmap/archive/`

This is the **superseded lineage layer**.

Use it for:
- historical planning artifacts that are no longer active
- predecessor programs kept temporarily for traceability

These files should not be treated as active roadmap truth.

### `docs/archive/`

This is the **historical non-roadmap lineage layer**.

Use it for:
- former root-level strategy/design documents
- superseded design syntheses
- historical material kept for traceability but no longer canonical

## Practical reading order

For current planning work, follow the key path above first. Use `docs/reference/` only after that.

## What does not belong here

Branch-local control notes, temporary review checklists, or one-off working-session management files should not live under `docs/`.

Only durable documentation that should survive commit history as part of the repo’s long-term knowledge surface belongs here.
