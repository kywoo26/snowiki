"""Contract tests for corrupted fixture provenance metadata."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


class TestCorruptedFixtureProvenance:
    """Tests for corrupted fixture provenance files."""

    def test_locked_provenance_exists(self) -> None:
        provenance_path = (
            FIXTURES_DIR / "corrupted" / "opencode" / "locked.provenance.json"
        )
        assert provenance_path.exists()

    def test_locked_provenance_valid_json(self) -> None:
        provenance_path = (
            FIXTURES_DIR / "corrupted" / "opencode" / "locked.provenance.json"
        )
        data = json.loads(provenance_path.read_text())
        assert "fixture_id" in data
        assert "description" in data

    def test_schema_mismatch_provenance_exists(self) -> None:
        provenance_path = (
            FIXTURES_DIR / "corrupted" / "opencode" / "schema_mismatch.provenance.json"
        )
        assert provenance_path.exists()

    def test_partial_rows_provenance_exists(self) -> None:
        provenance_path = (
            FIXTURES_DIR / "corrupted" / "opencode" / "partial_rows.provenance.json"
        )
        assert provenance_path.exists()

    def test_corrupted_fixtures_have_matching_db_files(self) -> None:
        corrupted_dir = FIXTURES_DIR / "corrupted" / "opencode"
        json_files = list(corrupted_dir.glob("*.provenance.json"))

        for json_file in json_files:
            all_db_files = list(FIXTURES_DIR.rglob("*.db"))
            fixture_name = json_file.name.replace(".provenance.json", "")
            matching_dbs = [db for db in all_db_files if fixture_name in db.name]
            assert matching_dbs, f"No matching .db file for {json_file.name}"
