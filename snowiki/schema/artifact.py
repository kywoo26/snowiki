from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from snowiki.schema.provenance import Provenance
from snowiki.schema.versioning import CURRENT_SCHEMA_VERSION, SchemaVersion


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: SchemaVersion = Field(default=CURRENT_SCHEMA_VERSION)
    id: str
    session_id: str
    source: str
    identity_keys: tuple[str, ...] = Field(min_length=1)
    type: str
    created_at: datetime
    uri: str
    provenance: Provenance
    mime_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    checksum_sha256: str | None = None
    source_metadata: dict[str, Any] | None = None
