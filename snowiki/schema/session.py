from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from snowiki.schema.provenance import Provenance
from snowiki.schema.versioning import CURRENT_SCHEMA_VERSION, SchemaVersion


class SessionStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    INCOMPLETE = "incomplete"
    ARCHIVED = "archived"


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: SchemaVersion = Field(default=CURRENT_SCHEMA_VERSION)
    id: str
    source: str
    identity_keys: tuple[str, ...] = Field(min_length=1)
    started_at: datetime
    updated_at: datetime
    ended_at: datetime | None = None
    metadata: dict[str, Any]
    status: SessionStatus
    provenance: Provenance
    source_metadata: dict[str, Any] | None = None
