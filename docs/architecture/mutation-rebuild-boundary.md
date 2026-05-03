# Mutation and Rebuild Boundary

## Purpose

Phase 6 moves mutation orchestration behind a dedicated application boundary without changing shipped CLI contracts or storage layout. The new boundary separates accepted knowledge mutations from rebuild finalization so raw and normalized writes are not coupled to ad hoc cache and manifest updates.

## Target modules

| Module | Owns | Explicit exclusions |
| :--- | :--- | :--- |
| `snowiki.mutation.domain` | Mutation variants, mutation outcomes, rebuild outcomes, and failure values. | No filesystem mutation, no CLI formatting, no storage layout decisions. |
| `snowiki.mutation.service` | Application lifecycle ordering: parse, validate, write raw, write normalized, then request finalization when needed. | No Click imports, no JSON envelope formatting, no global service container, no compiler page rendering. |
| `snowiki.mutation.finalizer` | Rebuild finalization order: compiled pages, query-cache clear, retrieval snapshot, content-identity compare, and manifest write last. | No raw or normalized writes, no source parsing, no CLI command behavior. |
| `snowiki.mutation.adapters` | Concrete adapters over existing storage, compiler, retrieval, and manifest primitives. | No abstract framework ceremony, no dependency registry, no storage schema ownership. |

## Ownership ledger

| Concern | Owner | Notes |
| :--- | :--- | :--- |
| Mutation lifecycle | `snowiki.mutation.service` | The service owns the sequence `parse -> validate -> write_raw -> write_normalized -> compile -> clear_cache -> write_manifest`. |
| Raw layout | `snowiki.storage.raw` and `snowiki.storage.zones` | Mutation code may call adapters but must not derive raw paths directly. |
| Normalized layout | `snowiki.storage.normalized` and provenance helpers | Mutation code supplies payloads and provenance; storage owns paths, atomic writes, and record shape persistence. |
| Compiled page generation | `snowiki.compiler.engine` and compiler generators | The compiler turns normalized records into pages only; it does not write manifests or clear search caches. |
| Rebuild finalization | `snowiki.mutation.finalizer` | Finalization owns cache invalidation, retrieval snapshot construction, identity comparison, and manifest persistence. |
| Index manifest schema | `snowiki.storage.index_manifest` | The finalizer writes manifests through storage-owned schema helpers and writes the manifest last. |
| Queue proposal lifecycle | Fileback queue modules until routed through service | Queue apply must delete pending proposals only after mutation service success. |
| CLI JSON envelope and exit behavior | `snowiki.cli` | CLI modules stay wrappers around application services and must not be imported by `snowiki.mutation`. |

## Mutation variants

The domain boundary accepts four explicit mutation requests:

1. `IngestMutation` for Markdown source ingestion.
2. `ReviewedFilebackMutation` for reviewed fileback proposals.
3. `SourcePruneMutation` for missing-source cleanup after explicit confirmation.
4. `RebuildMutation` for operator- or mutation-triggered rebuild finalization.

Every mutation returns a `MutationOutcome`. Failures are represented by `MutationFailure`, and rebuild finalization returns `RebuildOutcome` when it succeeds.

## Finalization invariant

The finalizer must preserve this order:

1. Rebuild compiled pages from normalized records.
2. Clear the query search index cache.
3. Build a retrieval snapshot.
4. Compare the snapshot identity against the current content identity.
5. Write `index/manifest.json` last.

Writing the manifest last prevents stale compiled or index state from being marked current when a cache, snapshot, or identity step fails.

## Explicit non-goals

- Do not implement an old-wrapper-only service around `run_rebuild_with_integrity`.
- Do not create a service container, global dependency registry, or runtime DI framework.
- Do not import `snowiki.cli` from the mutation package.
- Do not move storage layout ownership into mutation modules.
- Do not change raw, normalized, compiled, queue, or index artifact compatibility in this skeleton task.
- Do not make compiler generators responsible for cache invalidation or manifest writes.

## Migration direction

Existing flows can be routed incrementally: Markdown ingest, reviewed fileback apply, queued fileback apply, source prune, and rebuild should eventually construct domain mutations and call `MutationService`. Legacy internal tests may change during the refactor, but external CLI arguments, JSON envelopes, exit codes, storage compatibility, and destructive safety confirmations remain the preserved contracts.
