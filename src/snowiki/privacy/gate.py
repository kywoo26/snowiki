from __future__ import annotations

from pathlib import Path
from typing import Any

from .exclusions import explain_exclusion
from .redaction import redact_secrets


class PrivacyGate:
    def redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return redact_secrets(payload)

    def exclusion_reason(self, source_path: str | Path) -> str | None:
        return explain_exclusion(source_path)

    def ensure_allowed_source(self, source_path: str | Path) -> None:
        reason = self.exclusion_reason(source_path)
        if reason is not None:
            raise ValueError(reason)

    def prepare_payload(
        self,
        payload: dict[str, Any],
        *,
        source_path: str | Path | None = None,
    ) -> dict[str, Any]:
        if source_path is not None:
            self.ensure_allowed_source(source_path)
        return self.redact_payload(payload)
