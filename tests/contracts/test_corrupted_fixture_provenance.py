"""Contract tests for corrupted fixture provenance metadata."""

from __future__ import annotations

import json
from pathlib import Path


class TestCorruptedFixtureProvenance:
    """Tests for corrupted fixture provenance files."""

    def test_locked_provenance_exists(
        self, corrupted_opencode_fixtures_dir: Path
    ) -> None:
        provenance_path = corrupted_opencode_fixtures_dir / "locked.provenance.json"
        assert provenance_path.exists()

    def test_locked_provenance_valid_json(
        self, corrupted_opencode_fixtures_dir: Path
    ) -> None:
        provenance_path = corrupted_opencode_fixtures_dir / "locked.provenance.json"
        data = json.loads(provenance_path.read_text())
        assert "fixture_id" in data
        assert "description" in data

    def test_schema_mismatch_provenance_exists(
        self, corrupted_opencode_fixtures_dir: Path
    ) -> None:
        provenance_path = (
            corrupted_opencode_fixtures_dir / "schema_mismatch.provenance.json"
        )
        assert provenance_path.exists()

    def test_partial_rows_provenance_exists(
        self, corrupted_opencode_fixtures_dir: Path
    ) -> None:
        provenance_path = (
            corrupted_opencode_fixtures_dir / "partial_rows.provenance.json"
        )
        assert provenance_path.exists()

    def test_corrupted_fixtures_have_matching_db_files(
        self, corrupted_opencode_fixtures_dir: Path
    ) -> None:
        json_files = list(corrupted_opencode_fixtures_dir.glob("*.provenance.json"))

        for json_file in json_files:
            all_db_files = list(
                corrupted_opencode_fixtures_dir.parents[2].rglob("*.db")
            )
            fixture_name = json_file.name.replace(".provenance.json", "")
            matching_dbs = [db for db in all_db_files if fixture_name in db.name]
            assert matching_dbs, f"No matching .db file for {json_file.name}"
