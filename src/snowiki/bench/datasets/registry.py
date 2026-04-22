from __future__ import annotations

from typing import Final, cast

from .specs import (
    BenchmarkDatasetId,
    BenchmarkDatasetSourceSpec,
    BenchmarkDatasetSpec,
)

BENCHMARK_DATASET_REGISTRY: Final[dict[BenchmarkDatasetId, BenchmarkDatasetSpec]] = {
    "ms_marco_passage": BenchmarkDatasetSpec(
        dataset_id="ms_marco_passage",
        language="en",
        tier="official_suite",
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
    "trec_dl_2020_passage": BenchmarkDatasetSpec(
        dataset_id="trec_dl_2020_passage",
        language="en",
        tier="official_suite",
        citation="Craswell et al. TREC Deep Learning Track 2020.",
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
        tier="official_suite",
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
    "beir_nq": BenchmarkDatasetSpec(
        dataset_id="beir_nq",
        language="en",
        tier="official_suite",
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
    "miracl_ko": BenchmarkDatasetSpec(
        dataset_id="miracl_ko",
        language="ko",
        tier="official_suite",
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
    "beir_scifact": BenchmarkDatasetSpec(
        dataset_id="beir_scifact",
        language="en",
        tier="official_suite",
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
}
BENCHMARK_DATASET_IDS: Final[tuple[BenchmarkDatasetId, ...]] = tuple(
    BENCHMARK_DATASET_REGISTRY
)


def get_benchmark_dataset_spec(dataset_id: BenchmarkDatasetId) -> BenchmarkDatasetSpec:
    """Return the registry entry for a benchmark dataset."""

    return BENCHMARK_DATASET_REGISTRY[dataset_id]


def normalize_dataset_id(dataset_id: str) -> BenchmarkDatasetId:
    """Normalize a CLI dataset identifier into the registry literal type."""

    normalized = dataset_id.strip().lower()
    if normalized not in BENCHMARK_DATASET_REGISTRY:
        raise ValueError(f"unsupported benchmark dataset: {dataset_id}")
    return cast(BenchmarkDatasetId, normalized)


__all__ = [
    "BENCHMARK_DATASET_IDS",
    "BENCHMARK_DATASET_REGISTRY",
    "BenchmarkDatasetId",
    "BenchmarkDatasetSpec",
    "get_benchmark_dataset_spec",
    "normalize_dataset_id",
]
