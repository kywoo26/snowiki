from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from snowiki.schema.provenance import Provenance
from snowiki.schema.versioning import CURRENT_SCHEMA_VERSION, SchemaVersion


class IngestState(StrEnum):
    PENDING = "pending"
    NORMALIZED = "normalized"
    DUPLICATE = "duplicate"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class IngestStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: SchemaVersion = Field(default=CURRENT_SCHEMA_VERSION)
    id: str
    source: str
    identity_keys: tuple[str, ...] = Field(min_length=1)
    record_type: str
    record_id: str
    state: IngestState
    first_seen_at: datetime
    last_seen_at: datetime
    attempts: int = Field(default=1, ge=1)
    duplicate_of: str | None = None
    error: str | None = None
    provenance: Provenance
    source_metadata: dict[str, Any] | None = None
