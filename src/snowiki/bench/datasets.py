from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

from huggingface_hub import snapshot_download

from snowiki.config import get_benchmark_data_root
from snowiki.storage.zones import atomic_write_json, isoformat_utc, read_json

BenchmarkDatasetId = Literal[
    "ms_marco_passage",
    "trec_dl_2019_passage",
    "trec_dl_2020_passage",
    "miracl_ko",
    "miracl_en",
    "miracl_ja",
    "miracl_zh",
    "mr_tydi_ko",
    "beir_nq",
    "beir_scifact",
    "beir_fiqa_2018",
    "beir_arguana",
    "beir_nfcorpus",
]
RefreshMode = Literal["if-missing", "force"]


class BenchmarkDatasetCacheMissingError(RuntimeError):
    """Raised when a cached benchmark dataset cannot be reopened."""


@dataclass(frozen=True)
class BenchmarkDatasetSourceSpec:
    """Remote source needed to materialize a logical benchmark dataset."""

    label: str
    name: str
    repo_id: str
    repo_type: Literal["dataset"]
    default_revision: str
    allow_patterns: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkDatasetSpec:
    """Registry entry for a downloadable benchmark dataset."""

    dataset_id: BenchmarkDatasetId
    language: str
    tier: Literal["public_anchor"]
    citation: str
    license: str
    source_url: str
    sources: tuple[BenchmarkDatasetSourceSpec, ...]


@dataclass(frozen=True)
class BenchmarkDatasetSourceFetch:
    """Materialized fetch metadata for one source in a benchmark dataset."""

    label: str
    name: str
    repo_id: str
    repo_type: Literal["dataset"]
    requested_revision: str
    snapshot_path: Path
    allow_patterns: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkDatasetFetchResult:
    """Materialized fetch metadata for a benchmark dataset."""

    dataset_id: BenchmarkDatasetId
    benchmark_data_root: Path
    sources: tuple[BenchmarkDatasetSourceFetch, ...]
    lock_path: Path

    @property
    def snapshot_path(self) -> Path:
        """Return the first source snapshot path for legacy callers."""

        return self.sources[0].snapshot_path

    @property
    def requested_revision(self) -> str:
        """Return the first requested revision for legacy callers."""

        return self.sources[0].requested_revision


BENCHMARK_DATASET_REGISTRY: Final[dict[BenchmarkDatasetId, BenchmarkDatasetSpec]] = {
    "ms_marco_passage": BenchmarkDatasetSpec(
        dataset_id="ms_marco_passage",
        language="en",
        tier="public_anchor",
        citation=(
            "Nguyen et al. MS MARCO: A Human Generated MAchine Reading COmprehension Dataset."
        ),
        license="mit",
        source_url="https://huggingface.co/datasets/microsoft/ms_marco",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="MS MARCO passage corpus and queries",
                repo_id="microsoft/ms_marco",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "v1.1/*_passage*.parquet",
                    "v1.1/*_queries*.parquet",
                ),
            ),
        ),
    ),
    "trec_dl_2019_passage": BenchmarkDatasetSpec(
        dataset_id="trec_dl_2019_passage",
        language="en",
        tier="public_anchor",
        citation=(
            "Craswell et al. TREC Deep Learning Track 2019."
        ),
        license="mit",
        source_url="https://huggingface.co/datasets/microsoft/ms_marco",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="TREC DL 2019 passage corpus and queries",
                repo_id="microsoft/ms_marco",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "v2.1/*_passage*.parquet",
                    "v2.1/*_queries*.parquet",
                ),
            ),
        ),
    ),
    "trec_dl_2020_passage": BenchmarkDatasetSpec(
        dataset_id="trec_dl_2020_passage",
        language="en",
        tier="public_anchor",
        citation=(
            "Craswell et al. TREC Deep Learning Track 2020."
        ),
        license="mit",
        source_url="https://huggingface.co/datasets/microsoft/ms_marco",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="TREC DL 2020 passage corpus and queries",
                repo_id="microsoft/ms_marco",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "v2.1/*_passage*.parquet",
                    "v2.1/*_queries*.parquet",
                ),
            ),
        ),
    ),
    "miracl_en": BenchmarkDatasetSpec(
        dataset_id="miracl_en",
        language="en",
        tier="public_anchor",
        citation=(
            "Zhang et al. MIRACL: A Multilingual Retrieval Dataset Covering 18 "
            "Diverse Languages."
        ),
        license="cc-by-sa-4.0",
        source_url="https://huggingface.co/datasets/mteb/MIRACLRetrieval",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="dataset",
                name="MIRACL English parquet bundle",
                repo_id="mteb/MIRACLRetrieval",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "en-corpus/*.parquet",
                    "en-queries/*.parquet",
                    "en-qrels/*.parquet",
                ),
            ),
        ),
    ),
    "miracl_ja": BenchmarkDatasetSpec(
        dataset_id="miracl_ja",
        language="ja",
        tier="public_anchor",
        citation=(
            "Zhang et al. MIRACL: A Multilingual Retrieval Dataset Covering 18 "
            "Diverse Languages."
        ),
        license="cc-by-sa-4.0",
        source_url="https://huggingface.co/datasets/mteb/MIRACLRetrieval",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="dataset",
                name="MIRACL Japanese parquet bundle",
                repo_id="mteb/MIRACLRetrieval",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "ja-corpus/*.parquet",
                    "ja-queries/*.parquet",
                    "ja-qrels/*.parquet",
                ),
            ),
        ),
    ),
    "miracl_zh": BenchmarkDatasetSpec(
        dataset_id="miracl_zh",
        language="zh",
        tier="public_anchor",
        citation=(
            "Zhang et al. MIRACL: A Multilingual Retrieval Dataset Covering 18 "
            "Diverse Languages."
        ),
        license="cc-by-sa-4.0",
        source_url="https://huggingface.co/datasets/mteb/MIRACLRetrieval",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="dataset",
                name="MIRACL Chinese parquet bundle",
                repo_id="mteb/MIRACLRetrieval",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "zh-corpus/*.parquet",
                    "zh-queries/*.parquet",
                    "zh-qrels/*.parquet",
                ),
            ),
        ),
    ),
    "beir_nq": BenchmarkDatasetSpec(
        dataset_id="beir_nq",
        language="en",
        tier="public_anchor",
        citation=(
            "Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation "
            "of Information Retrieval Models."
        ),
        license="apache-2.0",
        source_url="https://huggingface.co/datasets/BeIR/nq",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="BEIR Natural Questions corpus and queries",
                repo_id="BeIR/nq",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("corpus/*.parquet", "queries/*.parquet"),
            ),
            BenchmarkDatasetSourceSpec(
                label="qrels",
                name="BEIR Natural Questions qrels",
                repo_id="BeIR/nq-qrels",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("test.tsv",),
            ),
        ),
    ),
    "beir_fiqa_2018": BenchmarkDatasetSpec(
        dataset_id="beir_fiqa_2018",
        language="en",
        tier="public_anchor",
        citation=(
            "Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation "
            "of Information Retrieval Models."
        ),
        license="cc-by-sa-4.0",
        source_url="https://huggingface.co/datasets/BeIR/fiqa",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="BEIR FiQA 2018 corpus and queries",
                repo_id="BeIR/fiqa",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("corpus/*.parquet", "queries/*.parquet"),
            ),
            BenchmarkDatasetSourceSpec(
                label="qrels",
                name="BEIR FiQA 2018 qrels",
                repo_id="BeIR/fiqa-qrels",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("test.tsv",),
            ),
        ),
    ),
    "beir_arguana": BenchmarkDatasetSpec(
        dataset_id="beir_arguana",
        language="en",
        tier="public_anchor",
        citation=(
            "Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation "
            "of Information Retrieval Models."
        ),
        license="cc-by-sa-4.0",
        source_url="https://huggingface.co/datasets/BeIR/arguana",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="BEIR ArguAna corpus and queries",
                repo_id="BeIR/arguana",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("corpus/*.parquet", "queries/*.parquet"),
            ),
            BenchmarkDatasetSourceSpec(
                label="qrels",
                name="BEIR ArguAna qrels",
                repo_id="BeIR/arguana-qrels",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("test.tsv",),
            ),
        ),
    ),
    "miracl_ko": BenchmarkDatasetSpec(
        dataset_id="miracl_ko",
        language="ko",
        tier="public_anchor",
        citation=(
            "Zhang et al. MIRACL: A Multilingual Retrieval Dataset Covering 18 "
            "Diverse Languages."
        ),
        license="cc-by-sa-4.0",
        source_url="https://huggingface.co/datasets/mteb/MIRACLRetrieval",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="dataset",
                name="MIRACL Korean parquet bundle",
                repo_id="mteb/MIRACLRetrieval",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "ko-corpus/*.parquet",
                    "ko-queries/*.parquet",
                    "ko-qrels/*.parquet",
                ),
            ),
        ),
    ),
    "mr_tydi_ko": BenchmarkDatasetSpec(
        dataset_id="mr_tydi_ko",
        language="ko",
        tier="public_anchor",
        citation=(
            "Zhang et al. Mr. TyDi: A Multi-lingual Benchmark for Dense Retrieval."
        ),
        license="apache-2.0",
        source_url="https://huggingface.co/datasets/castorini/mr-tydi",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="queries_qrels",
                name="Mr. TyDi Korean dev queries and qrels",
                repo_id="castorini/mr-tydi",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=(
                    "mrtydi-v1.1-korean/ir-format-data/topics.dev.txt",
                    "mrtydi-v1.1-korean/ir-format-data/qrels.dev.txt",
                ),
            ),
            BenchmarkDatasetSourceSpec(
                label="corpus",
                name="Mr. TyDi Korean corpus",
                repo_id="castorini/mr-tydi-corpus",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("mrtydi-v1.1-korean/corpus.jsonl.gz",),
            ),
        ),
    ),
    "beir_scifact": BenchmarkDatasetSpec(
        dataset_id="beir_scifact",
        language="en",
        tier="public_anchor",
        citation=(
            "Wadden et al. Fact or Fiction: Verifying Scientific Claims. EMNLP 2020."
        ),
        license="cc-by-4.0",
        source_url="https://huggingface.co/datasets/BeIR/scifact",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="BEIR SciFact corpus and queries",
                repo_id="BeIR/scifact",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("corpus/*.parquet", "queries/*.parquet"),
            ),
            BenchmarkDatasetSourceSpec(
                label="qrels",
                name="BEIR SciFact qrels",
                repo_id="BeIR/scifact-qrels",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("test.tsv",),
            ),
        ),
    ),
    "beir_nfcorpus": BenchmarkDatasetSpec(
        dataset_id="beir_nfcorpus",
        language="en",
        tier="public_anchor",
        citation=(
            "Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation "
            "of Information Retrieval Models."
        ),
        license="cc-by-sa-4.0",
        source_url="https://huggingface.co/datasets/BeIR/nfcorpus",
        sources=(
            BenchmarkDatasetSourceSpec(
                label="corpus_queries",
                name="BEIR NFCorpus corpus and queries",
                repo_id="BeIR/nfcorpus",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("corpus/*.parquet", "queries/*.parquet"),
            ),
            BenchmarkDatasetSourceSpec(
                label="qrels",
                name="BEIR NFCorpus qrels",
                repo_id="BeIR/nfcorpus-qrels",
                repo_type="dataset",
                default_revision="main",
                allow_patterns=("test.tsv",),
            ),
        ),
    ),
}
BENCHMARK_DATASET_IDS: Final[tuple[BenchmarkDatasetId, ...]] = tuple(
    BENCHMARK_DATASET_REGISTRY
)


def get_benchmark_dataset_spec(dataset_id: BenchmarkDatasetId) -> BenchmarkDatasetSpec:
    """Return the registry entry for a benchmark dataset.

    Args:
        dataset_id: Stable benchmark dataset identifier.

    Returns:
        The immutable dataset specification.
    """

    return BENCHMARK_DATASET_REGISTRY[dataset_id]


def get_benchmark_hf_cache_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned Hugging Face cache root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "hf")


def get_benchmark_locks_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned lock metadata root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "locks")


def get_benchmark_materialized_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned materialized data root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "materialized")


def get_benchmark_downloads_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned downloads root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "downloads")


def get_benchmark_dataset_lock_path(
    dataset_id: BenchmarkDatasetId, root: Path | None = None
) -> Path:
    """Return the lock metadata path for a benchmark dataset."""

    return get_benchmark_locks_root(root) / f"{dataset_id}.json"


def fetch_benchmark_dataset(
    dataset_id: BenchmarkDatasetId,
    *,
    data_root: Path | None = None,
    refresh: RefreshMode = "if-missing",
    local_files_only: bool = False,
    revision: str | None = None,
) -> BenchmarkDatasetFetchResult:
    """Fetch a benchmark dataset into the benchmark-owned cache.

    Args:
        dataset_id: Stable benchmark dataset identifier.
        data_root: Optional benchmark data root override.
        refresh: Whether to reuse existing lock metadata or force a refresh.
        local_files_only: If true, require the dataset to already exist locally.
        revision: Optional revision override applied to all sources.

    Returns:
        Fetch metadata describing the resolved snapshots and lock file.
    """

    benchmark_data_root = get_benchmark_data_root(data_root)
    spec = get_benchmark_dataset_spec(dataset_id)
    lock_path = get_benchmark_dataset_lock_path(dataset_id, benchmark_data_root)

    if refresh == "if-missing":
        cached_result = _reuse_cached_fetch(
            lock_path=lock_path,
            dataset_id=dataset_id,
            benchmark_data_root=benchmark_data_root,
            spec=spec,
            revision=revision,
        )
        if cached_result is not None:
            return cached_result

    cache_root = get_benchmark_hf_cache_root(benchmark_data_root)
    fetched_sources: list[BenchmarkDatasetSourceFetch] = []
    with _benchmark_hf_home(cache_root):
        for source in spec.sources:
            requested_revision = revision or source.default_revision
            snapshot_path = _download_snapshot(
                source=source,
                requested_revision=requested_revision,
                cache_root=cache_root,
                local_files_only=local_files_only,
                refresh=refresh,
            )
            fetched_sources.append(
                BenchmarkDatasetSourceFetch(
                    label=source.label,
                    name=source.name,
                    repo_id=source.repo_id,
                    repo_type=source.repo_type,
                    requested_revision=requested_revision,
                    snapshot_path=snapshot_path,
                    allow_patterns=source.allow_patterns,
                )
            )

    _ = _write_lock(lock_path=lock_path, spec=spec, fetched_sources=tuple(fetched_sources))
    return BenchmarkDatasetFetchResult(
        dataset_id=dataset_id,
        benchmark_data_root=benchmark_data_root,
        sources=tuple(fetched_sources),
        lock_path=lock_path,
    )


def resolve_cached_benchmark_dataset(
    dataset_id: BenchmarkDatasetId, *, data_root: Path | None = None
) -> BenchmarkDatasetFetchResult:
    """Reopen a previously fetched benchmark dataset from lock metadata."""

    benchmark_data_root = get_benchmark_data_root(data_root)
    spec = get_benchmark_dataset_spec(dataset_id)
    lock_path = get_benchmark_dataset_lock_path(dataset_id, benchmark_data_root)
    cached_result = _load_cached_fetch(
        lock_path=lock_path,
        dataset_id=dataset_id,
        benchmark_data_root=benchmark_data_root,
        spec=spec,
    )
    if cached_result is None:
        raise BenchmarkDatasetCacheMissingError(
            _missing_cache_message(dataset_id=dataset_id, benchmark_data_root=benchmark_data_root)
        )
    return cached_result


def _missing_cache_message(
    *, dataset_id: BenchmarkDatasetId, benchmark_data_root: Path
) -> str:
    return (
        f"benchmark dataset '{dataset_id}' is not cached under "
        f"{benchmark_data_root.as_posix()}; run `uv run snowiki benchmark-fetch "
        f"--dataset {dataset_id}` first"
    )


def _ensure_subdirectory(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _reuse_cached_fetch(
    *,
    lock_path: Path,
    dataset_id: BenchmarkDatasetId,
    benchmark_data_root: Path,
    spec: BenchmarkDatasetSpec,
    revision: str | None,
) -> BenchmarkDatasetFetchResult | None:
    cached_result = _load_cached_fetch(
        lock_path=lock_path,
        dataset_id=dataset_id,
        benchmark_data_root=benchmark_data_root,
        spec=spec,
    )
    if cached_result is None:
        return None
    if revision is None:
        expected_revisions = tuple(source.default_revision for source in spec.sources)
    else:
        expected_revisions = tuple(revision for _ in spec.sources)
    actual_revisions = tuple(source.requested_revision for source in cached_result.sources)
    if actual_revisions != expected_revisions:
        return None
    return cached_result


def _load_cached_fetch(
    *,
    lock_path: Path,
    dataset_id: BenchmarkDatasetId,
    benchmark_data_root: Path,
    spec: BenchmarkDatasetSpec,
) -> BenchmarkDatasetFetchResult | None:
    payload_raw = cast(object, read_json(lock_path, None))
    if not isinstance(payload_raw, dict):
        return None
    payload = cast(dict[str, object], payload_raw)
    if payload.get("dataset_id") != dataset_id:
        return None
    fetched_sources = _load_locked_sources(payload, spec=spec)
    if fetched_sources is None:
        return None
    return BenchmarkDatasetFetchResult(
        dataset_id=dataset_id,
        benchmark_data_root=benchmark_data_root,
        sources=fetched_sources,
        lock_path=lock_path,
    )


def _load_locked_sources(
    payload: dict[str, object], *, spec: BenchmarkDatasetSpec
) -> tuple[BenchmarkDatasetSourceFetch, ...] | None:
    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, list) or len(sources_raw) != len(spec.sources):
        return None

    fetched_sources: list[BenchmarkDatasetSourceFetch] = []
    for expected_source, source_raw in zip(spec.sources, sources_raw, strict=True):
        if not isinstance(source_raw, dict):
            return None
        source_payload = cast(dict[str, object], source_raw)
        if not _locked_source_matches(source_payload, source=expected_source):
            return None
        requested_revision = source_payload.get("requested_revision")
        snapshot_value = source_payload.get("resolved_snapshot_path")
        if not isinstance(requested_revision, str) or not requested_revision.strip():
            return None
        if not isinstance(snapshot_value, str) or not snapshot_value.strip():
            return None
        snapshot_path = Path(snapshot_value)
        if not snapshot_path.exists():
            return None
        fetched_sources.append(
            BenchmarkDatasetSourceFetch(
                label=expected_source.label,
                name=expected_source.name,
                repo_id=expected_source.repo_id,
                repo_type=expected_source.repo_type,
                requested_revision=requested_revision,
                snapshot_path=snapshot_path,
                allow_patterns=expected_source.allow_patterns,
            )
        )
    return tuple(fetched_sources)


def _locked_source_matches(
    payload: dict[str, object], *, source: BenchmarkDatasetSourceSpec
) -> bool:
    return (
        payload.get("label") == source.label
        and payload.get("name") == source.name
        and payload.get("repo_id") == source.repo_id
        and payload.get("repo_type") == source.repo_type
        and payload.get("allow_patterns") == list(source.allow_patterns)
    )


def _write_lock(
    *,
    lock_path: Path,
    spec: BenchmarkDatasetSpec,
    fetched_sources: tuple[BenchmarkDatasetSourceFetch, ...],
) -> Path:
    payload = {
        "dataset_id": spec.dataset_id,
        "fetched_at": isoformat_utc(None),
        "language": spec.language,
        "tier": spec.tier,
        "source_url": spec.source_url,
        "citation": spec.citation,
        "license": spec.license,
        "sources": [
            {
                "label": source.label,
                "name": source.name,
                "repo_id": source.repo_id,
                "repo_type": source.repo_type,
                "requested_revision": source.requested_revision,
                "resolved_snapshot_path": source.snapshot_path.as_posix(),
                "allow_patterns": list(source.allow_patterns),
            }
            for source in fetched_sources
        ],
    }
    return atomic_write_json(lock_path, payload)


def _download_snapshot(
    *,
    source: BenchmarkDatasetSourceSpec,
    requested_revision: str,
    cache_root: Path,
    local_files_only: bool,
    refresh: RefreshMode,
) -> Path:
    snapshot_location = snapshot_download(
        repo_id=source.repo_id,
        repo_type=source.repo_type,
        revision=requested_revision,
        allow_patterns=list(source.allow_patterns),
        cache_dir=cache_root,
        local_files_only=local_files_only,
        force_download=refresh == "force",
    )
    snapshot_path = Path(snapshot_location).resolve()
    snapshot_path.mkdir(parents=True, exist_ok=True)
    return snapshot_path


@contextmanager
def _benchmark_hf_home(cache_root: Path) -> Iterator[None]:
    previous_hf_home = os.environ.get("HF_HOME")
    os.environ["HF_HOME"] = cache_root.as_posix()
    try:
        yield
    finally:
        if previous_hf_home is None:
            _ = os.environ.pop("HF_HOME", None)
        else:
            os.environ["HF_HOME"] = previous_hf_home


def normalize_dataset_id(dataset_id: str) -> BenchmarkDatasetId:
    """Normalize a CLI dataset identifier into the registry literal type."""

    normalized = dataset_id.strip().lower()
    if normalized not in BENCHMARK_DATASET_REGISTRY:
        raise ValueError(f"unsupported benchmark dataset: {dataset_id}")
    return cast(BenchmarkDatasetId, normalized)
