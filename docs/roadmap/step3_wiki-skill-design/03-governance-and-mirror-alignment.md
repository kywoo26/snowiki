# Governance and Mirror Alignment

## Purpose

This document is the canonical owner of Step 3 governance for canonical-vs-mirror alignment. It defines how Snowiki prevents documentation drift across the current CLI-first `/wiki` contract, which surfaces must move together in the same PR, and which anti-drift tests enforce those rules.

This document does **not** redefine route taxonomy, schema definitions, maintenance loop design, benchmark methodology, or runtime promotion. Those phrases stay here intentionally because this lane must keep those neighboring ownership boundaries explicit.

## In Scope

- Canonical-vs-informative ownership for Step 3 contract surfaces.
- Same-PR mirror-sync rules for direct mirrors of current runtime truth.
- Drift-risk inventory for help output, deferred routes, MCP write-blocklist claims, and version/help references.
- Governance test ownership for mirror alignment and fail-closed support-surface checks.

## Out of Scope

- Changing route names, route buckets, route semantics, or route taxonomy from `01-wiki-route-contract.md`.
- Rewriting schema or provenance truth already owned by `02-schema-and-provenance-contract.md`.
- Defining maintenance loop design or deferred-workflow choreography owned by `04-maintenance-loop-and-deferred-workflows.md`.
- Benchmark methodology, tokenizer selection, or runtime promotion work.
- Implementing or redefining the runtime commands themselves.

## Owns

- Governance rules for canonical owners vs mirrors.
- Same-PR mirror-sync expectations.
- Anti-drift test ownership for Step 3 mirror alignment.
- Help-output parity ownership and deferred-route / MCP write-blocklist consistency ownership.

## Does Not Own

- Route taxonomy.
- Schema definitions.
- Maintenance loop design.
- Runtime command behavior.

## Canonical Owners vs Mirrors

Step 3 uses a strict owner/mirror split. A canonical owner defines the truth for its concern. A mirror may restate that truth for usability, but it must point back to the owner and may not silently widen or reinterpret it.

| Surface | Role in Step 3 | Canonical owner for facts carried there | Governance expectation |
| :--- | :--- | :--- | :--- |
| `docs/architecture/skill-and-agent-interface-contract.md` | Canonical owner for interface vocabulary, normative-vs-informative policy, CLI-first posture, and read-only MCP policy language | Itself | Update this first when interface-governance vocabulary changes, then sync mirrors in the same PR. |
| `01-wiki-route-contract.md` | Canonical owner for current route taxonomy, route buckets, route-to-runtime mapping, and deferred-route status | Itself | This document may reference route-governance consequences, but it must not redefine route taxonomy. |
| `02-schema-and-provenance-contract.md` | Canonical owner for schema, provenance, display, error-envelope, and reviewed-write payload truth | Itself | This document may govern sync rules for schema mirrors, but it must not redefine schema definitions. |
| `README.md` | Direct mirror for human-facing quick start and shipped CLI surface summary | `snowiki --help` for top-level command-list facts, `docs/architecture/skill-and-agent-interface-contract.md` for interface posture, and `01-wiki-route-contract.md` for route-status facts | Must mirror current commands, current `/wiki` routes, deferred routes, and read-only MCP posture without inventing independent product truth. |
| `skill/SKILL.md` | Direct mirror for distributable skill metadata and current workflow posture | `snowiki --help` for top-level command-list facts, plus `docs/architecture/skill-and-agent-interface-contract.md`, `01-wiki-route-contract.md`, and `02-schema-and-provenance-contract.md` as applicable | Must present the skill as an informative workflow layer over the installed CLI and must not redefine runtime capability. |
| `skill/workflows/wiki.md` | Direct mirror for step-by-step orchestration guidance | `snowiki --help` for top-level command-list facts, `docs/architecture/skill-and-agent-interface-contract.md` for CLI-first and read-only MCP posture, `01-wiki-route-contract.md` for route status and mapping, and `02-schema-and-provenance-contract.md` for reviewed-write and transport boundaries | Must keep deferred workflows clearly marked deferred and keep current-command help references aligned with shipped CLI truth. |
| `docs/reference/claude-code-wiki-quickstart.md` | Direct mirror for shortest truthful onboarding path | `docs/architecture/skill-and-agent-interface-contract.md`, `01-wiki-route-contract.md`, and `02-schema-and-provenance-contract.md` as applicable | Must stay concise, current, and fail closed on deferred routes or MCP write claims. |
| `analysis.md` | Informative synthesis and handoff surface, not a canonical contract owner | The numbered Step 3 documents | May explain why the contract is split the way it is, but must defer current truth to `01`, `02`, `03`, and `04`. |

Governance boundary: this document owns the anti-drift rules for those surfaces, not the runtime commands themselves. Runtime behavior remains owned by the CLI and implementation files, while route and schema truth remain owned by `01` and `02`.

## Drift Risks to Prevent

- **Canonical-owner bypass**: a mirror is edited first and the canonical owner is left stale.
- **Support-surface widening**: `README.md`, `skill/SKILL.md`, `skill/workflows/wiki.md`, or the quickstart implies routes or write paths that the shipped CLI does not provide.
- **Deferred-route drift**: mirrors stop agreeing on which routes are deferred or describe deferred routes as partially shipped.
- **Help-surface drift**: top-level command lists in the mirrors that restate them stop matching `snowiki --help`.
- **Version/help drift**: mirrors mention `snowiki --version` or an independently versioned skill contract before the shipped runtime exposes that entrypoint.
- **Read-only MCP drift**: support surfaces imply MCP mutation or fail to keep the MCP write-blocklist consistent with deferred write-like routes.
- **Ownership overlap drift**: this document starts duplicating route taxonomy, schema definitions, or maintenance loop design instead of governing how their mirrors stay aligned.
- **Synthesis-surface drift**: `analysis.md` or other background documents stop behaving like subordinate explanatory surfaces and begin competing with canonical owners.

## Mirror Sync Rules

1. **Canonical first**: change the canonical owner before changing any mirror that repeats the fact.
2. **Same-PR sync required**: any PR that changes a normative Step 3 fact must update every direct mirror that repeats that fact in the same PR.
3. **No silent widening**: if a mirror cannot yet be updated precisely, it must remove or narrow the claim rather than speculate.
4. **Explicit handoff links**: every direct mirror should point readers back to the canonical owner for the current truth it is repeating.
5. **Non-overlapping ownership**: `03` governs sync and drift prevention; `01` governs route taxonomy; `02` governs schema/provenance truth; `04` governs maintenance-loop and deferred-workflow semantics.
6. **Fail-closed deferred routes**: deferred routes must stay clearly labeled unavailable today across mirrors until the canonical route owner changes that status.
7. **Read-only MCP consistency**: mirrors must describe MCP as read-only and must not imply that deferred write-like routes are available through MCP.

### Same-PR surface groups

- **Route-status changes from `01`** must sync `README.md`, `skill/SKILL.md`, `skill/workflows/wiki.md`, and `docs/reference/claude-code-wiki-quickstart.md`. Any explanatory Step 3 summary text in `analysis.md` may be updated when needed, but it is not a primary direct-mirror parity surface.
- **Schema/provenance changes from `02`** must sync any direct mirror that restates reviewed-write, error-envelope, provenance, or transport-boundary facts.
- **Interface-governance vocabulary changes from `docs/architecture/skill-and-agent-interface-contract.md`** must sync all mirrors that restate CLI-first, informative-surface, approval, or read-only MCP posture.
- **Governance-rule changes from `03`** must sync the support surfaces only where they explicitly mention mirror status, canonical ownership, or same-PR alignment expectations.

## Governance Test Surface

This document owns the governance expectations enforced by the Step 3 anti-drift test suite. It does not own runtime behavior; it owns the checks that verify mirrors still describe the runtime and canonical contracts accurately.

| Test surface | Governance purpose |
| :--- | :--- |
| `tests/governance/test_step3_mirror_alignment.py` | Primary anti-drift suite for direct mirrors. Verifies `snowiki --help` parity across the mirrors that restate the top-level command list, parity for mirrored deferred write-like route summaries, help/version entrypoint alignment, and MCP write-blocklist coverage for mirrored deferred write-like routes. |
| `tests/governance/test_wiki_route_contract_docs.py` | Guards that route mirrors stay aligned with the canonical route contract and that read-only MCP / deferred-route claims remain fail-closed across support surfaces. |
| `tests/governance/test_skill_contract_alignment.py` | Guards that `skill/SKILL.md` and `skill/workflows/wiki.md` keep treating the CLI as authoritative runtime truth and the skill as an informative layer. |

Governance ownership rule: these tests enforce mirror alignment, parity, and fail-closed posture. They do **not** redefine the commands, route taxonomy, or schema/provenance content they verify.

## Version and Help Alignment

The installed `snowiki` CLI owns the actual help surface. Direct mirrors may summarize that help surface, but they must stay aligned with the shipped top-level command list exposed by `snowiki --help`.

- `snowiki --help` is the canonical help-output reference for top-level command discovery.
- `README.md`, `skill/SKILL.md`, and `skill/workflows/wiki.md` are direct mirrors of that top-level command list and should be updated in the same PR when the help surface changes.
- `docs/reference/claude-code-wiki-quickstart.md` should keep `snowiki --help` as the recommended discovery entrypoint instead of restating an independent command taxonomy.
- Mirrors must not document `snowiki --version` as a shipped entrypoint until the CLI actually exposes it.
- If the skill package, README, or quickstart needs to mention version compatibility, it must describe compatibility with the shipped CLI/runtime contract rather than implying an independently authoritative skill version.

Help/version governance boundary: `03` owns the parity rule and the tests that guard it, not the actual existence of help flags or version flags.

## MCP Write-Blocklist and Deferred-Route Consistency

The canonical fact that MCP is read-only comes from the interface contract and runtime implementation. The canonical fact of which routes are deferred comes from `01-wiki-route-contract.md`. This document owns the governance rule that those two truths must remain consistent anywhere they are mirrored together.

- Deferred write-like routes such as `sync`, `edit`, and `merge` must remain unavailable today across all direct mirrors until `01` changes that status.
- The MCP write-operation blocklist must remain a superset of deferred write-like routes so the read-only boundary fails closed instead of drifting into implied mutation support.
- Mirrors must not claim direct MCP writes, implicit MCP mutation fallback, or “softly available” deferred write behavior.
- If a future PR promotes a deferred write-like route, it must update the canonical route owner, the direct mirrors, and the relevant governance tests together so the policy and runtime posture remain coherent.

## Related Documents

- [Wiki Route Contract](01-wiki-route-contract.md)
- [Schema and Provenance Contract](02-schema-and-provenance-contract.md)
- [Step 3 Analysis](analysis.md)
- [Skill and Agent Interface Contract](../../architecture/skill-and-agent-interface-contract.md)

## Reference Reading

- `docs/architecture/current-retrieval-architecture.md` for supporting runtime terminology used by the canonical contracts.
- `docs/roadmap/external/claude-skills/official-guidance-notes.md` for supporting skill-authoring guidance.

## Helper Questions for Future Deep Planning

- If a canonical owner changes, which direct mirrors repeat that exact fact and therefore must move in the same PR?
- Does the proposed change alter help-output parity, deferred-route status, or MCP write-blocklist expectations that the governance tests should catch?
- Is a support surface still acting as a mirror, or has it started competing with a canonical owner?
