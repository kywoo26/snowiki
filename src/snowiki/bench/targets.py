from __future__ import annotations

from snowiki.benchmark_targets import (
    BM25_HF_WORDPIECE_TARGET_ADAPTER,
    BM25_KIWI_MORPHOLOGY_TARGET_ADAPTER,
    BM25_KIWI_NOUNS_TARGET_ADAPTER,
    BM25_MECAB_MORPHOLOGY_TARGET_ADAPTER,
    BM25_REGEX_TARGET_ADAPTER,
    LEXICAL_REGEX_TARGET_ADAPTER,
    SNOWIKI_QUERY_RUNTIME_TARGET_ADAPTER,
)

from .specs import (
    BenchmarkTargetSpec,
    RetrievalTargetAdapter,
)


class TargetRegistry:
    """Registry for retrieval target adapters."""

    def __init__(self) -> None:
        self._specs: dict[str, BenchmarkTargetSpec] = {}
        self._adapters: dict[str, RetrievalTargetAdapter] = {}

    def register_target(
        self,
        spec: BenchmarkTargetSpec,
        adapter: RetrievalTargetAdapter,
    ) -> None:
        if spec.target_id in self._specs:
            raise ValueError(f"Target already registered: {spec.target_id}")
        self._specs[spec.target_id] = spec
        self._adapters[spec.target_id] = adapter

    def get_target(self, target_id: str) -> RetrievalTargetAdapter:
        try:
            return self._adapters[target_id]
        except KeyError as exc:
            raise KeyError(f"Unknown benchmark target: {target_id}") from exc

    def list_targets(self) -> tuple[BenchmarkTargetSpec, ...]:
        return tuple(self._specs.values())


OFFICIAL_DATASET_IDS: tuple[str, ...] = (
    "beir_nq",
    "beir_scifact",
    "trec_dl_2020_passage",
    "miracl_ko",
)
LEXICAL_REGEX_V1 = BenchmarkTargetSpec(
    target_id="lexical_regex_v1",
    description="Lexical retrieval target using the runtime regex tokenizer.",
    supported_datasets=OFFICIAL_DATASET_IDS,
)
BM25_REGEX_V1 = BenchmarkTargetSpec(
    target_id="bm25_regex_v1",
    description="BM25 retrieval target using the regex tokenizer.",
    supported_datasets=OFFICIAL_DATASET_IDS,
)
SNOWIKI_QUERY_RUNTIME_V1 = BenchmarkTargetSpec(
    target_id="snowiki_query_runtime_v1",
    description="Snowiki topical query runtime policy over benchmark corpora.",
    supported_datasets=OFFICIAL_DATASET_IDS,
)
BM25_KIWI_MORPHOLOGY_V1 = BenchmarkTargetSpec(
    target_id="bm25_kiwi_morphology_v1",
    description="BM25 retrieval target using Kiwi morphology tokenization.",
    supported_datasets=OFFICIAL_DATASET_IDS,
)
BM25_KIWI_NOUNS_V1 = BenchmarkTargetSpec(
    target_id="bm25_kiwi_nouns_v1",
    description="BM25 retrieval target using Kiwi noun-only tokenization.",
    supported_datasets=OFFICIAL_DATASET_IDS,
)
BM25_MECAB_MORPHOLOGY_V1 = BenchmarkTargetSpec(
    target_id="bm25_mecab_morphology_v1",
    description="BM25 retrieval target using MeCab morphology tokenization.",
    supported_datasets=OFFICIAL_DATASET_IDS,
)
BM25_HF_WORDPIECE_V1 = BenchmarkTargetSpec(
    target_id="bm25_hf_wordpiece_v1",
    description="BM25 retrieval target using Hugging Face WordPiece tokenization.",
    supported_datasets=OFFICIAL_DATASET_IDS,
)


BUILTIN_TARGETS: tuple[BenchmarkTargetSpec, ...] = (
    LEXICAL_REGEX_V1,
    SNOWIKI_QUERY_RUNTIME_V1,
    BM25_REGEX_V1,
    BM25_KIWI_MORPHOLOGY_V1,
    BM25_KIWI_NOUNS_V1,
    BM25_MECAB_MORPHOLOGY_V1,
    BM25_HF_WORDPIECE_V1,
)
DEFAULT_TARGET_REGISTRY = TargetRegistry()
DEFAULT_TARGET_REGISTRY.register_target(
    LEXICAL_REGEX_V1,
    LEXICAL_REGEX_TARGET_ADAPTER,
)
DEFAULT_TARGET_REGISTRY.register_target(
    SNOWIKI_QUERY_RUNTIME_V1,
    SNOWIKI_QUERY_RUNTIME_TARGET_ADAPTER,
)
DEFAULT_TARGET_REGISTRY.register_target(
    BM25_REGEX_V1,
    BM25_REGEX_TARGET_ADAPTER,
)
DEFAULT_TARGET_REGISTRY.register_target(
    BM25_KIWI_MORPHOLOGY_V1,
    BM25_KIWI_MORPHOLOGY_TARGET_ADAPTER,
)
DEFAULT_TARGET_REGISTRY.register_target(
    BM25_KIWI_NOUNS_V1,
    BM25_KIWI_NOUNS_TARGET_ADAPTER,
)
DEFAULT_TARGET_REGISTRY.register_target(
    BM25_MECAB_MORPHOLOGY_V1,
    BM25_MECAB_MORPHOLOGY_TARGET_ADAPTER,
)
DEFAULT_TARGET_REGISTRY.register_target(
    BM25_HF_WORDPIECE_V1,
    BM25_HF_WORDPIECE_TARGET_ADAPTER,
)


def register_target(spec: BenchmarkTargetSpec, adapter: RetrievalTargetAdapter) -> None:
    """Register one retrieval target on the default registry."""

    DEFAULT_TARGET_REGISTRY.register_target(spec, adapter)


def get_target(target_id: str) -> RetrievalTargetAdapter:
    """Return one retrieval target adapter from the default registry."""

    return DEFAULT_TARGET_REGISTRY.get_target(target_id)
