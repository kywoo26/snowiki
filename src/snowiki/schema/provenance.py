from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from snowiki.schema.versioning import CURRENT_SCHEMA_VERSION, SchemaVersion


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: SchemaVersion = Field(default=CURRENT_SCHEMA_VERSION)
    id: str
    source: str
    identity_keys: tuple[str, ...] = Field(min_length=1)
    raw_uri: str
    raw_id: str
    raw_kind: str
    captured_at: datetime
    locator: dict[str, Any] = Field(default_factory=dict)
    checksum_sha256: str | None = None
    source_metadata: dict[str, Any] | None = None
