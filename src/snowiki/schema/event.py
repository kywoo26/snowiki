from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from snowiki.schema.content import Message
from snowiki.schema.provenance import Provenance
from snowiki.schema.versioning import CURRENT_SCHEMA_VERSION, SchemaVersion


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: SchemaVersion = Field(default=CURRENT_SCHEMA_VERSION)
    id: str
    session_id: str
    source: str
    identity_keys: tuple[str, ...] = Field(min_length=1)
    type: str
    timestamp: datetime
    content: Message | None
    provenance: Provenance
    parent_event_id: str | None = None
    artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    source_metadata: dict[str, Any] | None = None
