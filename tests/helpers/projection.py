from __future__ import annotations

from collections.abc import Sequence

from snowiki.schema.projection import (
    CompilerProjection,
    ProjectionSection,
    SourceIdentity,
    make_compiler_projection,
)


def compiler_projection(
    title: str,
    summary: str = "",
    *,
    body: str | None = None,
    tags: Sequence[str] = (),
    source_identity: SourceIdentity | None = None,
    sections: Sequence[ProjectionSection] = (),
    concepts: Sequence[object] = (),
    entities: Sequence[object] = (),
    topics: Sequence[object] = (),
    questions: Sequence[object] = (),
    projects: Sequence[object] = (),
    decisions: Sequence[object] = (),
) -> CompilerProjection:
    """Build the strict normalized compiler projection used by tests."""
    return make_compiler_projection(
        title=title,
        summary=summary,
        body=body,
        tags=tags,
        source_identity=source_identity,
        sections=sections,
        taxonomy={
            "concepts": list(concepts),
            "entities": list(entities),
            "topics": list(topics),
            "questions": list(questions),
            "projects": list(projects),
            "decisions": list(decisions),
        },
    )
