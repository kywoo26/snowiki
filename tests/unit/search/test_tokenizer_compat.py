from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.search.tokenizer_compat import (
    StaleTokenizerArtifactError,
    normalize_stored_tokenizer_name,
    require_tokenizer_compatibility,
)


class TestNormalizeStoredTokenizerName:
    def test_canonical_name_passthrough(self) -> None:
        assert normalize_stored_tokenizer_name({"tokenizer_name": "regex_v1"}) == "regex_v1"
        assert (
            normalize_stored_tokenizer_name({"tokenizer_name": "kiwi_morphology_v1"})
            == "kiwi_morphology_v1"
        )
        assert (
            normalize_stored_tokenizer_name({"tokenizer_name": "kiwi_nouns_v1"})
            == "kiwi_nouns_v1"
        )
        assert (
            normalize_stored_tokenizer_name({"tokenizer_name": "mecab_morphology_v1"})
            == "mecab_morphology_v1"
        )
        assert (
            normalize_stored_tokenizer_name({"tokenizer_name": "hf_wordpiece_v1"})
            == "hf_wordpiece_v1"
        )

    def test_unknown_canonical_name_returns_none(self) -> None:
        assert normalize_stored_tokenizer_name({"tokenizer_name": "unknown_v99"}) is None

    def test_empty_or_whitespace_tokenizer_name_returns_none(self) -> None:
        assert normalize_stored_tokenizer_name({"tokenizer_name": ""}) is None
        assert normalize_stored_tokenizer_name({"tokenizer_name": "   "}) is None

    def test_typed_manifest_identity_name_passthrough(self) -> None:
        assert (
            normalize_stored_tokenizer_name(
                {"identity": {"retrieval": {"name": "kiwi_morphology_v1"}}}
            )
            == "kiwi_morphology_v1"
        )

    def test_no_metadata_returns_none(self) -> None:
        assert normalize_stored_tokenizer_name({}) is None
        assert normalize_stored_tokenizer_name({"other_key": "value"}) is None

    def test_legacy_use_kiwi_tokenizer_false_maps_to_regex(self) -> None:
        assert (
            normalize_stored_tokenizer_name({"use_kiwi_tokenizer": False})
            == "regex_v1"
        )

    def test_legacy_use_kiwi_tokenizer_true_defaults_to_morphology(self) -> None:
        assert (
            normalize_stored_tokenizer_name({"use_kiwi_tokenizer": True})
            == "kiwi_morphology_v1"
        )

    def test_legacy_kiwi_lexical_candidate_mode_nouns_maps_to_kiwi_nouns(self) -> None:
        assert (
            normalize_stored_tokenizer_name(
                {"use_kiwi_tokenizer": True, "kiwi_lexical_candidate_mode": "nouns"}
            )
            == "kiwi_nouns_v1"
        )

    def test_legacy_kiwi_lexical_candidate_mode_morphology_maps_to_kiwi_morphology(
        self,
    ) -> None:
        assert (
            normalize_stored_tokenizer_name(
                {
                    "use_kiwi_tokenizer": True,
                    "kiwi_lexical_candidate_mode": "morphology",
                }
            )
            == "kiwi_morphology_v1"
        )

    def test_legacy_only_kiwi_lexical_candidate_mode_string_defaults_to_kiwi_true(
        self,
    ) -> None:
        assert (
            normalize_stored_tokenizer_name({"kiwi_lexical_candidate_mode": "nouns"})
            == "kiwi_nouns_v1"
        )
        assert (
            normalize_stored_tokenizer_name(
                {"kiwi_lexical_candidate_mode": "morphology"}
            )
            == "kiwi_morphology_v1"
        )

    def test_legacy_unset_flags_default_to_current_default(self) -> None:
        result = normalize_stored_tokenizer_name({"use_kiwi_tokenizer": None})
        assert result == "kiwi_morphology_v1"


class TestRequireTokenizerCompatibility:
    def test_matching_identity_returns_stored_name(self) -> None:
        path = Path("/fake/index")
        result = require_tokenizer_compatibility(
            artifact_path=path,
            requested_tokenizer_name="kiwi_morphology_v1",
            metadata={"tokenizer_name": "kiwi_morphology_v1"},
        )
        assert result == "kiwi_morphology_v1"

    def test_missing_identity_raises_stale_error(self) -> None:
        path = Path("/fake/index")
        with pytest.raises(StaleTokenizerArtifactError, match="missing tokenizer identity") as excinfo:
            require_tokenizer_compatibility(
                artifact_path=path,
                requested_tokenizer_name="kiwi_morphology_v1",
                metadata={},
            )
        assert excinfo.value.details["stored_tokenizer_name"] is None
        assert excinfo.value.details["reason"] == "missing tokenizer identity"
        assert excinfo.value.details["rebuild_required"] is True

    def test_mismatched_identity_raises_stale_error(self) -> None:
        path = Path("/fake/index")
        with pytest.raises(
            StaleTokenizerArtifactError, match="tokenizer identity mismatch"
        ) as excinfo:
            require_tokenizer_compatibility(
                artifact_path=path,
                requested_tokenizer_name="kiwi_morphology_v1",
                metadata={"tokenizer_name": "regex_v1"},
            )
        assert excinfo.value.details["stored_tokenizer_name"] == "regex_v1"
        assert excinfo.value.details["reason"] == "tokenizer identity mismatch"
        assert excinfo.value.details["rebuild_required"] is True

    def test_legacy_metadata_normalized_before_comparison(self) -> None:
        path = Path("/fake/index")
        result = require_tokenizer_compatibility(
            artifact_path=path,
            requested_tokenizer_name="kiwi_nouns_v1",
            metadata={
                "use_kiwi_tokenizer": True,
                "kiwi_lexical_candidate_mode": "nouns",
            },
        )
        assert result == "kiwi_nouns_v1"

    def test_legacy_false_metadata_compared_as_regex(self) -> None:
        path = Path("/fake/index")
        result = require_tokenizer_compatibility(
            artifact_path=path,
            requested_tokenizer_name="regex_v1",
            metadata={"use_kiwi_tokenizer": False},
        )
        assert result == "regex_v1"

    def test_legacy_false_metadata_mismatch_raises(self) -> None:
        path = Path("/fake/index")
        with pytest.raises(StaleTokenizerArtifactError, match="tokenizer identity mismatch"):
            require_tokenizer_compatibility(
                artifact_path=path,
                requested_tokenizer_name="kiwi_morphology_v1",
                metadata={"use_kiwi_tokenizer": False},
            )
