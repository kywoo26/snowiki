from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

load_opencode_session = importlib.import_module(
    "snowiki.adapters.opencode"
).load_opencode_session


def test_opencode_adapter_fails_safely_on_locked_source(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "opencode.db"
    db_path.write_bytes(b"sqlite placeholder")

    def _raise_locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(sqlite3, "connect", _raise_locked)

    result = load_opencode_session("ses-locked", db_path=db_path)

    assert result.session is None
    assert result.messages == ()
    assert result.events == ()
    assert result.ingest_status.state.value == "failed"
    assert result.error is not None
    assert "locked" in result.error.lower()


def test_opencode_adapter_quarantines_partial_source(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    sqlite3.connect(db_path).close()

    result = load_opencode_session("ses-partial", db_path=db_path)

    assert result.session is None
    assert result.ingest_status.state.value == "quarantined"
    assert result.error is not None
    assert "missing required sqlite tables" in result.error.lower()
