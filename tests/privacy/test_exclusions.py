from __future__ import annotations

from pathlib import Path

import pytest
from snowiki.privacy.exclusions import explain_exclusion, is_excluded_path
from snowiki.privacy.gate import PrivacyGate


def test_opencode_auth_path_is_excluded() -> None:
    path = Path("~/.local/share/opencode/auth.json")

    assert is_excluded_path(path) is True
    assert explain_exclusion(path) is not None


def test_privacy_gate_blocks_sensitive_ingest_sources() -> None:
    gate = PrivacyGate()

    with pytest.raises(ValueError, match="sensitive path excluded"):
        gate.ensure_allowed_source(Path("~/.local/share/opencode/auth.json"))
