# Chunker + Vector Schema

## Purpose

Define the canonical chunk format, provenance rules, and vector-store schema for Step 4 so dense retrieval can be added without breaking Snowiki's provenance contract.

## Scope

This sub-step covers:
- chunk boundary policy for compiled pages and normalized records
- chunk handling for markdown, code blocks, tables, and image-derived text
- deterministic provenance fields carried from compiler output into vector storage
- the storage backend and schema for persisted embeddings

## Decisions

### 1. Chunk source boundaries

- `CompiledPage.sections` is the primary boundary for wiki pages.
- `NormalizedRecord.content` is the primary boundary for sessions and other non-page records.
- Chunking starts from those natural boundaries and only subdivides when a section or record slice is too large for embedding.

### 2. Canonical chunk format

```python
@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_path: str
    section_index: int | None
    char_offset: int
    text: str
```

Required semantics:
- `chunk_id` is deterministic from content identity plus provenance fields.
- `doc_path` is the canonical retrieval identity used to rejoin lexical and vector hits.
- `section_index` is required for compiled pages and `None` only for record-style content without section structure.
- `char_offset` is the byte/character start offset of the chunk inside the source section or record slice.
- `text` is the exact embedded payload after chunk assembly.

### 3. Boundary policy by content type

- **Markdown prose**: preserve section boundaries first; when a section is too large, split within the section using paragraph and sentence boundaries before any hard cap split.
- **Code blocks**: keep the full fenced block intact when it fits; if oversized, split on blank lines and then line ranges while keeping original order.
- **Tables**: preserve the header row in every derived chunk; split oversized tables by row groups rather than flattening cells into unrelated prose.
- **Images**: do not embed binary image content; embed only adjacent alt text, caption text, or extracted OCR text already present in the compiled representation.

### 4. Provenance rules

- Every stored vector row must include `doc_path`, `section_index`, and `char_offset`.
- These fields are mandatory even when retrieval later collapses results back to document-level ranking.
- Dense retrieval must never emit a final hit that cannot be traced back to a source location.
- Any chunk transform that would discard source offsets is invalid.

### 5. Storage backend decision

Use **SQLite co-located with the lexical index database** as the canonical vector backend.

Why:
- matches Snowiki's existing local-first storage posture
- avoids introducing a second operational dependency for Step 4
- keeps rebuild, invalidation, backup, and per-vault portability aligned with the lexical index lifecycle
- is sufficient for exact cosine scan on Snowiki's current expected corpus sizes

ANN indexes remain explicitly out of scope for this sub-step.

### 6. Vector schema

```sql
CREATE TABLE vector_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_path TEXT NOT NULL,
    section_index INTEGER,
    char_offset INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding BLOB NOT NULL,
    model_version TEXT NOT NULL
);

CREATE INDEX idx_vector_doc ON vector_chunks(doc_path);
CREATE INDEX idx_vector_model ON vector_chunks(model_version);
```

Schema rules:
- `embedding` stores the serialized float vector for the active local model.
- `model_version` is part of staleness detection and rebuild invalidation.
- a model-version mismatch marks rows stale; rows are not mixed across model versions during retrieval.

## Non-goals

- implementing the embedder lifecycle
- choosing ANN or external vector-database infrastructure
- shipping runtime dense retrieval
- designing rerank or fusion behavior

## Deliverables

1. a documented `Chunk` contract with required provenance fields
2. a written boundary policy for markdown, code, tables, and image-derived text
3. a finalized SQLite vector schema and backend decision
4. a rebuild/invalidation note tying vector freshness to content identity plus `model_version`

## Acceptance criteria

- the chunker contract specifies how markdown, code, tables, and images are handled without dropping provenance
- every chunk and every dense candidate preserves `doc_path`, `section_index`, and `char_offset`
- the vector storage decision is closed: SQLite co-located with the lexical index is the canonical backend
- the schema is concrete enough that implementation can begin without reopening storage-shape questions
