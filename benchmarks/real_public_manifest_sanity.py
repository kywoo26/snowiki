from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from snowiki.bench.anchors.public_cached import (
    PublicAnchorSampleMode,
    load_beir_nfcorpus_cached_manifest,
    load_beir_scifact_cached_manifest,
    load_miracl_ko_cached_manifest,
    load_mr_tydi_ko_cached_manifest,
)
from snowiki.bench.corpus import BenchmarkCorpusManifest

_EXPECTED_COUNTS: Final[dict[str, tuple[int, int, int]]] = {
    "MIRACL KO": (200, 213, 213),
    "Mr. TyDi KO": (200, 303, 303),
    "BEIR SciFact": (200, 300, 300),
    "BEIR NFCorpus": (200, 323, 323),
}
_MODES: Final[tuple[PublicAnchorSampleMode, ...]] = ("quick", "standard", "full")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify real cached public-anchor benchmark manifest counts for "
            "quick, standard, and full sample modes."
        )
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Optional benchmark data root override.",
    )
    return parser.parse_args()


def _selected_query_count(manifest: BenchmarkCorpusManifest) -> int:
    return len(manifest.queries or [])


def _verify_manifest(
    *,
    label: str,
    manifest: BenchmarkCorpusManifest,
    mode: PublicAnchorSampleMode,
    expected_selected: int,
    expected_available: int,
) -> int:
    if manifest.dataset_metadata is None:
        raise ValueError(f"{label} {mode} manifest is missing dataset metadata")
    selected_count = _selected_query_count(manifest)
    if selected_count != expected_selected:
        raise ValueError(
            f"{label} {mode} selected {selected_count} queries; expected {expected_selected}"
        )
    if manifest.dataset_metadata.get("sample_mode") != mode:
        raise ValueError(
            f"{label} {mode} reported sample_mode={manifest.dataset_metadata.get('sample_mode')!r}"
        )
    if manifest.dataset_metadata.get("sample_size") != expected_selected:
        raise ValueError(
            f"{label} {mode} reported sample_size={manifest.dataset_metadata.get('sample_size')!r}"
        )
    if manifest.dataset_metadata.get("queries_available") != expected_available:
        raise ValueError(
            f"{label} {mode} reported queries_available={manifest.dataset_metadata.get('queries_available')!r}"
        )
    return selected_count


def main() -> int:
    args = _parse_args()
    data_root = args.data_root
    datasets = (
        ("MIRACL KO", load_miracl_ko_cached_manifest),
        ("Mr. TyDi KO", load_mr_tydi_ko_cached_manifest),
        ("BEIR SciFact", load_beir_scifact_cached_manifest),
        ("BEIR NFCorpus", load_beir_nfcorpus_cached_manifest),
    )

    for label, loader in datasets:
        expected_counts = _EXPECTED_COUNTS[label]
        expected_available = expected_counts[2]
        actual_counts = tuple(
            _verify_manifest(
                label=label,
                manifest=loader(sample_mode=mode, data_root=data_root),
                mode=mode,
                expected_selected=expected_selected,
                expected_available=expected_available,
            )
            for mode, expected_selected in zip(_MODES, expected_counts, strict=True)
        )
        sys.stdout.write(f"{label}: {actual_counts[0]} / {actual_counts[1]} / {actual_counts[2]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
