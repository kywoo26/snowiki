from __future__ import annotations

import io
import json
import tempfile
import zipfile
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

import bm25s

from .kiwi_tokenizer import (
    KIWI_LEXICAL_CANDIDATE_MODES,
    KiwiLexicalCandidateMode,
)
from .registry import SearchTokenizer, create, default, get
from .subword_tokenizer import WordPieceSearchTokenizer
from .tokenizer_compat import (
    normalize_stored_tokenizer_name,
    require_tokenizer_compatibility,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime


@dataclass(frozen=True)
class BM25SearchDocument:
    id: str
    path: str
    kind: str
    title: str
    content: str
    summary: str = ""
    aliases: tuple[str, ...] = ()
    recorded_at: datetime | None = None
    source_type: str = ""


@dataclass(frozen=True)
class BM25SearchHit:
    document: BM25SearchDocument
    score: float
    matched_terms: tuple[str, ...]


class BM25SearchIndex:
    """BM25 search index using bm25s library with Kiwi tokenization.

    This index supports multiple BM25 variants:
    - "robertson": Robertson et al. (standard Okapi BM25)
    - "atire": ATIRE variant
    - "bm25l": BM25L (length-normalized)
    - "bm25+": BM25+ (improved version)
    - "lucene": Lucene variant

    Args:
        documents: Iterable of documents to index
        method: BM25 variant to use (default: "lucene")
        k1: Term frequency saturation parameter (default: 1.5)
        b: Document length normalization (default: 0.75)
        delta: BM25+ delta parameter (default: 0.5)
    """

    BM25_METHODS: frozenset[str] = frozenset(
        ["robertson", "atire", "bm25l", "bm25+", "lucene"]
    )
    DEFAULT_KIWI_LEXICAL_CANDIDATE_MODE: KiwiLexicalCandidateMode = "morphology"
    _METADATA_SUFFIX = ".snowiki_meta.json"
    _INDEX_FORMAT_VERSION = "bm25s-v1"
    _WORDPIECE_VOCAB_SUFFIX = ".wordpiece-vocab.txt"
    _SHOW_PROGRESS = False
    _LEAVE_PROGRESS = False
    _TOKENIZER_NAMES: frozenset[str] = frozenset(
        [
            "regex_v1",
            "kiwi_morphology_v1",
            "kiwi_nouns_v1",
            "mecab_morphology_v1",
            "hf_wordpiece_v1",
        ]
    )

    def __init__(
        self,
        documents: Iterable[BM25SearchDocument],
        method: str = "lucene",
        k1: float = 1.5,
        b: float = 0.75,
        delta: float = 0.5,
        tokenizer_name: str | None = None,
        tokenizer: SearchTokenizer | None = None,
        use_kiwi_tokenizer: bool = True,
        kiwi_lexical_candidate_mode: KiwiLexicalCandidateMode = DEFAULT_KIWI_LEXICAL_CANDIDATE_MODE,
    ) -> None:
        if method not in self.BM25_METHODS:
            raise ValueError(
                f"Invalid method: {method}. Must be one of {self.BM25_METHODS}"
            )
        if kiwi_lexical_candidate_mode not in KIWI_LEXICAL_CANDIDATE_MODES:
            raise ValueError(
                "Invalid Kiwi lexical candidate mode: "
                + f"{kiwi_lexical_candidate_mode}. Must be one of "
                + f"{sorted(KIWI_LEXICAL_CANDIDATE_MODES)}"
            )

        resolved_tokenizer_name = (
            tokenizer_name or default().name
            if tokenizer is not None
            else self._resolve_tokenizer_name(
                tokenizer_name=tokenizer_name,
                use_kiwi_tokenizer=use_kiwi_tokenizer,
                kiwi_lexical_candidate_mode=kiwi_lexical_candidate_mode,
            )
        )
        legacy_flags = self._legacy_tokenizer_flags(resolved_tokenizer_name)

        self.documents: list[BM25SearchDocument] = list(documents)
        self.method: str = method
        self.k1: float = k1
        self.b: float = b
        self.delta: float = delta
        self.tokenizer_name: str = resolved_tokenizer_name
        self.use_kiwi_tokenizer = legacy_flags[0]
        self.kiwi_lexical_candidate_mode = legacy_flags[1]

        self.tokenizer: SearchTokenizer | None = tokenizer or (
            create(resolved_tokenizer_name)
            if self.use_kiwi_tokenizer or resolved_tokenizer_name == "regex_v1"
            else None
        )
        self._separate_field_tokenization = tokenizer is not None
        self.corpus_tokens: list[list[str]] = []
        self.bm25: Any
        self._build_index()

    @classmethod
    def _metadata_path(cls, path: str) -> Path:
        return Path(f"{path}{cls._METADATA_SUFFIX}")

    def _metadata_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "method": self.method,
            "k1": self.k1,
            "b": self.b,
            "delta": self.delta,
            "tokenizer_name": self.tokenizer_name,
            "use_kiwi_tokenizer": self.use_kiwi_tokenizer,
            "kiwi_lexical_candidate_mode": self.kiwi_lexical_candidate_mode,
            "bm25s_version": self._bm25s_version(),
            "index_format_version": self._INDEX_FORMAT_VERSION,
        }
        if isinstance(self.tokenizer, WordPieceSearchTokenizer) and self.tokenizer.is_fitted:
            payload["tokenizer_artifact"] = {
                "type": "bert_wordpiece_vocab",
                "path": self._wordpiece_vocab_path_name(),
                "vocab_size": self.tokenizer.vocab_size,
                "min_frequency": self.tokenizer.min_frequency,
                "lowercase": self.tokenizer.lowercase,
            }
        return payload

    @classmethod
    def _wordpiece_vocab_path(cls, path: str) -> Path:
        index_path = Path(path)
        return index_path.with_name(f"{index_path.name}{cls._WORDPIECE_VOCAB_SUFFIX}")

    def _wordpiece_vocab_path_name(self) -> str:
        return self._wordpiece_vocab_path("index").name

    @staticmethod
    def _bm25s_version() -> str:
        try:
            return version("bm25s")
        except PackageNotFoundError:
            return "unknown"

    @classmethod
    def _resolve_tokenizer_name(
        cls,
        *,
        tokenizer_name: str | None,
        use_kiwi_tokenizer: bool,
        kiwi_lexical_candidate_mode: KiwiLexicalCandidateMode,
    ) -> str:
        resolved = tokenizer_name or cls._resolve_tokenizer_name_from_flags(
            use_kiwi_tokenizer=use_kiwi_tokenizer,
            kiwi_lexical_candidate_mode=kiwi_lexical_candidate_mode,
        )

        spec = get(resolved)
        if resolved not in cls._TOKENIZER_NAMES:
            supported = ", ".join(sorted(cls._TOKENIZER_NAMES))
            raise ValueError(
                f"Invalid BM25 tokenizer: {resolved}. Must be one of {supported}"
            )
        return spec.name

    @classmethod
    def _resolve_tokenizer_name_from_flags(
        cls,
        *,
        use_kiwi_tokenizer: bool,
        kiwi_lexical_candidate_mode: KiwiLexicalCandidateMode,
    ) -> str:
        if use_kiwi_tokenizer is False:
            return default().name
        if kiwi_lexical_candidate_mode == "nouns":
            return "kiwi_nouns_v1"
        return "kiwi_morphology_v1"

    @classmethod
    def _legacy_tokenizer_flags(
        cls, tokenizer_name: str
    ) -> tuple[bool, KiwiLexicalCandidateMode]:
        if tokenizer_name == "regex_v1":
            return False, cls.DEFAULT_KIWI_LEXICAL_CANDIDATE_MODE
        if tokenizer_name == "kiwi_nouns_v1":
            return True, "nouns"
        if tokenizer_name == "mecab_morphology_v1":
            return True, "morphology"
        if tokenizer_name == "hf_wordpiece_v1":
            return True, "morphology"
        return True, "morphology"

    @staticmethod
    def _metadata_float(metadata: dict[str, object], key: str, default: float) -> float:
        value = metadata.get(key, default)
        return float(cast(float | int | str, value))

    def _build_index(self) -> None:
        """Build BM25 index from documents."""
        if not self.documents:
            self.corpus_tokens = []
            self.bm25 = bm25s.BM25(method=self.method)
            return

        self.corpus_tokens = self._tokenize_documents(fit_tokenizer=True)
        self.bm25 = bm25s.BM25(method=self.method, k1=self.k1, b=self.b)
        self.bm25.index(
            self.corpus_tokens,
            show_progress=self._SHOW_PROGRESS,
            leave_progress=self._LEAVE_PROGRESS,
        )

    def _tokenize_documents(self, *, fit_tokenizer: bool) -> list[list[str]]:
        corpus = [
            f"{doc.title}\n{doc.content}\n{doc.summary}" for doc in self.documents
        ]
        if self.tokenizer is not None:
            fit = getattr(self.tokenizer, "fit_corpus", None)
            if fit_tokenizer and callable(fit):
                fit(corpus)
            if self._separate_field_tokenization:
                return [
                    list(
                        self.tokenizer.tokenize(doc.title)
                        + self.tokenizer.tokenize(doc.path)
                        + self.tokenizer.tokenize(doc.content)
                        + self.tokenizer.tokenize(doc.summary)
                        + self.tokenizer.tokenize(" ".join(doc.aliases))
                    )
                    for doc in self.documents
                ]
            return [list(self.tokenizer.tokenize(text)) for text in corpus]
        return cast(
            list[list[str]],
            bm25s.tokenize(
                corpus,
                stopwords="en",
                return_ids=False,
                show_progress=self._SHOW_PROGRESS,
                leave=self._LEAVE_PROGRESS,
            ),
        )

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[BM25SearchHit]:
        """Search documents using BM25 scoring."""
        if not self.documents:
            return []

        query_tokens = self.tokenize_query(query)

        if not query_tokens:
            return []

        results = self.bm25.retrieve(
            [list(query_tokens)],
            k=min(limit, len(self.documents)),
            show_progress=self._SHOW_PROGRESS,
            leave_progress=self._LEAVE_PROGRESS,
        )

        hits = []
        doc_indices = results[0].flatten()
        scores = results[1].flatten()
        for i in range(len(doc_indices)):
            doc_idx = int(doc_indices[i])
            score = float(scores[i])
            doc = self.documents[doc_idx]
            hits.append(
                BM25SearchHit(
                    document=doc,
                    score=score,
                    matched_terms=(
                        self._matched_query_terms(query_tokens, self.corpus_tokens[doc_idx])
                        if self.corpus_tokens
                        else ()
                    ),
                )
            )

        return hits

    def tokenize_query(self, query: str) -> tuple[str, ...]:
        """Tokenize a query with the index tokenizer for diagnostics and search."""
        if self.tokenizer is not None:
            return tuple(self.tokenizer.tokenize(query))
        tokenized = cast(
            list[list[str]],
            bm25s.tokenize(
                query,
                stopwords="en",
                return_ids=False,
                show_progress=self._SHOW_PROGRESS,
                leave=self._LEAVE_PROGRESS,
            ),
        )
        return tuple(tokenized[0])

    def tokens_for_document(self, document_id: str) -> tuple[str, ...]:
        """Return indexed tokens for one document ID for diagnostics."""
        if not self.corpus_tokens:
            raise RuntimeError("BM25 document tokens are not loaded for diagnostics.")
        for index, document in enumerate(self.documents):
            if document.id == document_id:
                return tuple(self.corpus_tokens[index])
        raise KeyError(f"Unknown BM25 document ID: {document_id}")

    @staticmethod
    def _matched_query_terms(
        query_tokens: tuple[str, ...],
        document_tokens: list[str],
    ) -> tuple[str, ...]:
        document_token_set = set(document_tokens)
        matched_terms: list[str] = []
        seen: set[str] = set()
        for token in query_tokens:
            if token in document_token_set and token not in seen:
                matched_terms.append(token)
                seen.add(token)
        return tuple(matched_terms)

    def save(self, path: str) -> None:
        """Save index to disk."""
        self.bm25.save(path)
        if isinstance(self.tokenizer, WordPieceSearchTokenizer):
            _ = self.tokenizer.save_vocab(
                self._wordpiece_vocab_path(path).parent,
                prefix="index.wordpiece",
            )
        _ = self._metadata_path(path).write_text(
            json.dumps(self._metadata_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def to_cache_bytes(self) -> bytes:
        """Serialize the BM25 index directory and Snowiki metadata as one artifact."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            index_path = temp_root / "index"
            self.save(index_path.as_posix())
            buffer = io.BytesIO()
            with zipfile.ZipFile(
                buffer,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for path in sorted(temp_root.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(temp_root).as_posix())
            return buffer.getvalue()

    @classmethod
    def load_cache_artifact(
        cls,
        path: Path,
        documents: Iterable[BM25SearchDocument],
        *,
        expected_tokenizer_name: str | None = None,
        load_corpus_tokens: bool = False,
    ) -> BM25SearchIndex:
        """Load a single-file benchmark cache artifact produced by to_cache_bytes."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            with zipfile.ZipFile(path) as archive:
                cls._extract_cache_archive(archive=archive, destination=temp_root)
            return cls.load(
                (temp_root / "index").as_posix(),
                documents,
                expected_tokenizer_name=expected_tokenizer_name,
                load_corpus_tokens=load_corpus_tokens,
            )

    @staticmethod
    def _extract_cache_archive(
        *,
        archive: zipfile.ZipFile,
        destination: Path,
    ) -> None:
        for member in archive.infolist():
            member_path = PurePosixPath(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe BM25 cache artifact member: {member.filename}")
            if member.is_dir():
                continue
            target_path = destination / member_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(archive.read(member))

    @classmethod
    def load(
        cls,
        path: str,
        documents: Iterable[BM25SearchDocument],
        *,
        expected_tokenizer_name: str | None = None,
        load_corpus_tokens: bool = True,
    ) -> BM25SearchIndex:
        """Load index from disk."""
        metadata_path = cls._metadata_path(path)
        metadata: dict[str, object] = {}
        if metadata_path.exists():
            metadata = cast(dict[str, object], json.loads(metadata_path.read_text()))

        requested_tokenizer_name = (
            expected_tokenizer_name
            or normalize_stored_tokenizer_name(metadata)
            or default().name
        )
        tokenizer_name = require_tokenizer_compatibility(
            artifact_path=metadata_path,
            requested_tokenizer_name=requested_tokenizer_name,
            metadata=metadata,
        )

        instance = cls.__new__(cls)
        instance.documents = list(documents)
        instance.method = cast(str, metadata.get("method", "lucene"))
        instance.k1 = cls._metadata_float(metadata, "k1", 1.5)
        instance.b = cls._metadata_float(metadata, "b", 0.75)
        instance.delta = cls._metadata_float(metadata, "delta", 0.5)
        instance.tokenizer_name = tokenizer_name
        instance.use_kiwi_tokenizer, instance.kiwi_lexical_candidate_mode = (
            cls._legacy_tokenizer_flags(instance.tokenizer_name)
        )
        instance.tokenizer = cls._load_tokenizer(
            tokenizer_name=instance.tokenizer_name,
            metadata=metadata,
            metadata_path=metadata_path,
        )
        instance._separate_field_tokenization = False
        instance.corpus_tokens = (
            instance._tokenize_documents(fit_tokenizer=False)
            if load_corpus_tokens
            else []
        )
        instance.bm25 = bm25s.BM25.load(path, load_corpus=True)
        return instance

    @classmethod
    def _load_tokenizer(
        cls,
        *,
        tokenizer_name: str,
        metadata: dict[str, object],
        metadata_path: Path,
    ) -> SearchTokenizer | None:
        if tokenizer_name == "hf_wordpiece_v1":
            artifact = metadata.get("tokenizer_artifact")
            if isinstance(artifact, dict):
                artifact_payload = cast("Mapping[str, object]", artifact)
                artifact_type = artifact_payload.get("type")
                raw_path = artifact_payload.get("path")
                vocab_size = artifact_payload.get("vocab_size", 2000)
                min_frequency = artifact_payload.get("min_frequency", 1)
                lowercase = artifact_payload.get("lowercase", True)
            else:
                artifact_type = None
                raw_path = None
                vocab_size = 2000
                min_frequency = 1
                lowercase = True
            if artifact_type == "bert_wordpiece_vocab" and isinstance(raw_path, str) and raw_path:
                vocab_path = cls._safe_tokenizer_artifact_path(
                    metadata_path=metadata_path,
                    artifact_path=raw_path,
                )
                if not vocab_path.is_file():
                    raise ValueError(
                        f"Missing BM25 tokenizer artifact: {vocab_path.as_posix()}"
                    )
                return WordPieceSearchTokenizer.from_vocab_file(
                    vocab_path,
                    vocab_size=int(cast(int | str, vocab_size)),
                    min_frequency=int(cast(int | str, min_frequency)),
                    lowercase=bool(lowercase),
                )
        if tokenizer_name == "regex_v1" or cls._legacy_tokenizer_flags(tokenizer_name)[0]:
            return create(tokenizer_name)
        return None

    @staticmethod
    def _safe_tokenizer_artifact_path(
        *,
        metadata_path: Path,
        artifact_path: str,
    ) -> Path:
        member_path = PurePosixPath(artifact_path)
        if member_path.is_absolute() or ".." in member_path.parts:
            raise ValueError(f"Unsafe BM25 tokenizer artifact path: {artifact_path}")
        return metadata_path.parent / member_path
