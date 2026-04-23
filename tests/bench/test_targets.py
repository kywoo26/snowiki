from __future__ import annotations

from collections.abc import Mapping

import pytest

from snowiki.bench.specs import BenchmarkTargetSpec, DatasetManifest, LevelConfig
from snowiki.bench.targets import (
    BUILTIN_TARGETS,
    DEFAULT_TARGET_REGISTRY,
    TargetRegistry,
)


class _Adapter:
    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
    ) -> Mapping[str, object]:
        del manifest, level
        return {}


def test_builtin_targets_are_discoverable() -> None:
    expected_ids = {
        "lexical_regex_v1",
        "bm25_regex_v1",
        "bm25_kiwi_morphology_v1",
        "bm25_kiwi_nouns_v1",
        "bm25_mecab_morphology_v1",
        "bm25_hf_wordpiece_v1",
    }

    assert len(BUILTIN_TARGETS) == 6
    assert {spec.target_id for spec in BUILTIN_TARGETS} == expected_ids
    assert {spec.target_id for spec in DEFAULT_TARGET_REGISTRY.list_targets()} == expected_ids


def test_unknown_target_raises_clear_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown benchmark target: missing_target"):
        DEFAULT_TARGET_REGISTRY.get_target("missing_target")


def test_duplicate_registration_raises_value_error() -> None:
    registry = TargetRegistry()
    spec = BenchmarkTargetSpec(target_id="duplicate_target")
    adapter = _Adapter()

    registry.register_target(spec, adapter)

    with pytest.raises(ValueError, match="Target already registered: duplicate_target"):
        registry.register_target(spec, adapter)
