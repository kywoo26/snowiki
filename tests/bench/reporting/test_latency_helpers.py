from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pytest


def test_latency_helper_branches_are_covered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    latency_module = import_module("snowiki.bench.validation.latency")
    presets = import_module("snowiki.bench.contract.presets")
    preset = presets.get_preset("retrieval")

    rows: list[dict[str, object]] = [
        {
            "id": "q1",
            "text": "alpha",
            "kind": "known-item",
            "group": "ko",
            "tags": ["keep", ""],
        },
        {"id": "q2", "text": " ", "kind": "known-item"},
        {"id": "q3", "text": "skip", "kind": "temporal"},
    ]
    query_specs = latency_module._query_specs_from_rows(rows, preset=preset)
    assert query_specs == ({"text": "alpha", "kind": "known-item", "id": "q1", "group": "ko", "tags": ["keep"]},)

    payload_path = tmp_path / "queries.json"
    payload_path.write_text('{"queries": []}', encoding="utf-8")
    assert latency_module._load_json(payload_path) == {"queries": []}

    monkeypatch.setattr(latency_module, "_load_json", lambda path: {"queries": rows})
    loaded_specs = latency_module._load_query_specs_for_preset(preset)
    assert loaded_specs == query_specs

    assert latency_module._requested_latency_policy(
        "official_suite",
        query_count=60,
        latency_sample="fixed_sample",
    ).mode == "fixed_sample"
    assert latency_module._requested_latency_policy(
        "official_suite",
        query_count=60,
        latency_sample="stratified",
    ).mode == "stratified"
    assert latency_module._requested_latency_policy(
        "official_suite",
        query_count=60,
        latency_sample="exhaustive",
    ).mode == "exhaustive"

    assert latency_module._derive_latency_strata(
        (
            {"text": "alpha", "kind": "known-item", "group": "shared"},
            {"text": "beta", "kind": "topical", "group": "shared"},
        )
    ) == ["known-item", "topical"]
    assert latency_module._derive_latency_strata(
        ({"text": "alpha", "kind": "", "group": ""},)
    ) == ["all"]

    materialized = latency_module._materialize_latency_policy(
        latency_module.LatencySamplingPolicy(mode="stratified"),
        queries=(
            {"text": "alpha", "kind": "known-item", "group": "shared"},
            {"text": "beta", "kind": "topical", "group": "shared"},
        ),
    )
    assert materialized.strata == ["known-item", "topical"]
    assert latency_module._materialize_latency_policy(
        latency_module.LatencySamplingPolicy(mode="stratified", strata=["preset"]),
        queries=query_specs,
    ).strata == ["preset"]

    assert latency_module._evenly_spaced_positions(0, 3) == []
    assert latency_module._evenly_spaced_positions(3, 5) == [0, 1, 2]
    assert latency_module._fixed_sample_query_positions(3, 5) == [0, 1, 2]
    assert latency_module._stratified_sample_query_positions((), strata=["ko"]) == []
    assert latency_module._stratified_sample_query_positions(query_specs, strata=[]) == [0]
    assert latency_module._stratified_sample_query_positions(
        query_specs,
        strata=["missing"],
    ) == [0]

    mixed_queries = cast(
        tuple[object, ...],
        tuple(
            {
                "text": f"q{index}",
                "kind": "known-item",
                "group": "ko" if index == 0 else "other",
            }
            for index in range(5)
        ),
    )
    assert latency_module._stratified_sample_query_positions(
        cast(Any, mixed_queries),
        strata=["ko"],
    ) == [0, 1, 2, 3, 4]

