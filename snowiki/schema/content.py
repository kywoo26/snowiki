from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from snowiki.schema.provenance import Provenance
from snowiki.schema.versioning import CURRENT_SCHEMA_VERSION, SchemaVersion


class Part(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: SchemaVersion = Field(default=CURRENT_SCHEMA_VERSION)
    id: str
    message_id: str
    source: str
    identity_keys: tuple[str, ...] = Field(min_length=1)
    type: str
    index: int = Field(ge=0)
    text: str | None = None
    data: dict[str, Any] | None = None
    artifact_id: str | None = None
    mime_type: str | None = None
    provenance: Provenance
    source_metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_payload_reference(self) -> Part:
        if self.text is None and self.data is None and self.artifact_id is None:
            raise ValueError("part requires text, data, or artifact_id")
        return self


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: SchemaVersion = Field(default=CURRENT_SCHEMA_VERSION)
    id: str
    session_id: str
    source: str
    identity_keys: tuple[str, ...] = Field(min_length=1)
    role: str
    created_at: datetime
    parts: tuple[Part, ...] = Field(min_length=1)
    provenance: Provenance
    source_metadata: dict[str, Any] | None = None
