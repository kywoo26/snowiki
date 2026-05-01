from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from snowiki.search.bm25_index import BM25SearchIndex
from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.tokenizer_compat import StaleTokenizerArtifactError


class _Flattenable:
    def __init__(self, values: list[int] | list[float]) -> None:
        self._values = values

    def flatten(self) -> list[int] | list[float]:
        return self._values


@pytest.fixture
def fake_bm25_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, list[dict[str, object]]]:
    calls: dict[str, list[dict[str, object]]] = {
        "tokenize": [],
        "index": [],
        "retrieve": [],
        "registry": [],
        "save": [],
        "load": [],
    }

    class FakeTokenizer:
        def __init__(self, extract_nouns_only: bool = False) -> None:
            calls["registry"].append({"init_extract_nouns_only": extract_nouns_only})
            self.extract_nouns_only = extract_nouns_only

        def tokenize(self, text: str) -> tuple[str, ...]:
            calls["registry"].append(
                {
                    "text": text,
                    "extract_nouns_only": self.extract_nouns_only,
                }
            )
            tokens: list[str] = []
            if "Python" in text or "python" in text:
                tokens.append("python")
            if "README.md" in text or "readme.md" in text:
                tokens.extend(["readme", "md"])
            if "/src/app.py" in text or "/src/app.py" in text.casefold():
                tokens.extend(["src", "app", "py"])
            if "자연어" in text:
                tokens.append("자연어")
            if not self.extract_nouns_only and ("처리" in text):
                tokens.append("처리")
            if not self.extract_nouns_only and ("재미있" in text or "재미있는" in text):
                tokens.append("재미있")
            return tuple(tokens)

    class FakeBM25:
        def __init__(self, **kwargs: object) -> None:
            self._doc_count = 0
            self.kwargs = kwargs

        def index(self, corpus_tokens: list[list[str]], **kwargs: object) -> None:
            self._doc_count = len(corpus_tokens)
            calls["index"].append({"corpus_tokens": corpus_tokens, **kwargs})

        def retrieve(
            self, query_tokens: list[list[str]], **kwargs: object
        ) -> tuple[_Flattenable, _Flattenable]:
            calls["retrieve"].append({"query_tokens": query_tokens, **kwargs})
            limit = min(cast(int, kwargs["k"]), self._doc_count)
            return _Flattenable(list(range(limit))), _Flattenable([1.0] * limit)

        def save(self, path: str) -> None:
            calls["save"].append({"path": path})

        @classmethod
        def load(cls, path: str, **kwargs: object) -> FakeBM25:
            calls["load"].append({"path": path, **kwargs})
            return cls()

    def fake_tokenize(texts: str | list[str], **kwargs: object) -> list[list[str]]:
        calls["tokenize"].append({"texts": texts, **kwargs})
        values = [texts] if isinstance(texts, str) else texts
        return [str(text).lower().replace(".", "").split() for text in values]

    monkeypatch.setattr(
        "snowiki.search.bm25_index.bm25s",
        SimpleNamespace(BM25=FakeBM25, tokenize=fake_tokenize),
    )
    monkeypatch.setattr(
        "snowiki.search.bm25_index.get",
        lambda name: SimpleNamespace(name=name),
    )
    monkeypatch.setattr(
        "snowiki.search.bm25_index.create",
        lambda name: (
            calls["registry"].append({"create": name})
            or FakeTokenizer(extract_nouns_only=name == "kiwi_nouns_v1")
        ),
    )
    return calls


class TestBM25SearchIndex:
    """Test cases for BM25SearchIndex."""

    def test_init_empty(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        index = BM25SearchIndex([])
        assert index.documents == []
        assert index.method == "lucene"
        assert fake_bm25_backend["tokenize"] == []

    def test_init_with_documents(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Test Document",
                content="This is a test document about Python.",
            ),
            SearchDocument(
                id="doc2",
                path="test/doc2.md",
                kind="summary",
                title="Another Document",
                content="This document is about programming.",
            ),
        ]
        index = BM25SearchIndex(docs)
        assert len(index.documents) == 2
        assert index.method == "lucene"
        assert len(fake_bm25_backend["index"]) == 1

    def test_search_empty_index(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        index = BM25SearchIndex([])
        results = index.search("test")
        assert results == []
        assert fake_bm25_backend["retrieve"] == []

    def test_search_with_results(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python Programming",
                content="Python is a great language for programming.",
            ),
            SearchDocument(
                id="doc2",
                path="test/doc2.md",
                kind="summary",
                title="Java Programming",
                content="Java is another programming language.",
            ),
        ]
        index = BM25SearchIndex(docs)
        results = index.search("Python")
        assert len(results) > 0
        assert isinstance(results[0], SearchHit)
        assert results[0].score > 0
        assert results[0].matched_terms == ("python",)
        assert results[1].matched_terms == ()
        assert len(fake_bm25_backend["retrieve"]) == 1

    def test_search_can_skip_matched_terms(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python Programming",
                content="Python is a great language for programming.",
            )
        ]
        index = BM25SearchIndex(docs)

        results = index.search("Python", include_matched_terms=False)

        assert results[0].matched_terms == ()
        assert len(fake_bm25_backend["retrieve"]) == 1

    def test_search_korean_uses_tokenizer_output(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 처리",
                content="자연어 처리는 재미있는 분야입니다.",
            ),
            SearchDocument(
                id="doc2",
                path="test/doc2.md",
                kind="summary",
                title="컴퓨터 비전",
                content="컴퓨터 비전은 이미지를 분석합니다.",
            ),
        ]
        index = BM25SearchIndex(docs)
        results = index.search("자연어")
        assert len(results) > 0
        assert isinstance(results[0], SearchHit)
        assert any(
            call.get("text") == "자연어" for call in fake_bm25_backend["registry"]
        )

    def test_mixed_language_tokens_preserve_english_identifiers(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 Python 처리",
                content="README.md /src/app.py 를 참고하세요.",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="kiwi_morphology_v1")
        _ = index.search("Python README.md")

        first_index_call = cast(dict[str, Any], fake_bm25_backend["index"][0])
        first_retrieve_call = cast(dict[str, Any], fake_bm25_backend["retrieve"][0])

        assert first_index_call["corpus_tokens"][0] == [
            "python",
            "readme",
            "md",
            "src",
            "app",
            "py",
            "자연어",
            "처리",
        ]
        assert first_retrieve_call["query_tokens"] == [["python", "readme", "md"]]

    def test_index_build_batches_and_deduplicates_document_field_tokenization(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        class BatchTokenizer:
            def __init__(self) -> None:
                self.batch_calls: list[tuple[str, ...]] = []

            def tokenize(self, text: str) -> tuple[str, ...]:
                return (text.casefold().replace(" ", "_"),)

            def tokenize_many(
                self, texts: tuple[str, ...]
            ) -> tuple[tuple[str, ...], ...]:
                self.batch_calls.append(texts)
                return tuple(self.tokenize(text) for text in texts)

            def normalize(self, text: str) -> str:
                return text.casefold()

        tokenizer = BatchTokenizer()
        docs = [
            SearchDocument(
                id="doc1",
                path="shared/doc.md",
                kind="summary",
                title="shared/doc.md",
                content="Python content",
            )
        ]

        _ = BM25SearchIndex(docs, tokenizer_name="regex_v1", tokenizer=tokenizer)

        first_index_call = cast(dict[str, Any], fake_bm25_backend["index"][0])
        assert tokenizer.batch_calls == [("shared/doc.md", "Python content")]
        assert first_index_call["corpus_tokens"] == [
            ["shared/doc.md", "shared/doc.md", "python_content"]
        ]

    def test_index_tokenizes_searchable_fields_without_metadata(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        class BatchTokenizer:
            def __init__(self) -> None:
                self.batch_calls: list[tuple[str, ...]] = []

            def tokenize(self, text: str) -> tuple[str, ...]:
                return tuple(text.casefold().split())

            def tokenize_many(
                self, texts: tuple[str, ...]
            ) -> tuple[tuple[str, ...], ...]:
                self.batch_calls.append(texts)
                return tuple(self.tokenize(text) for text in texts)

            def normalize(self, text: str) -> str:
                return text.casefold()

        tokenizer = BatchTokenizer()
        docs = [
            SearchDocument(
                id="doc1",
                path="docs/path-field.md",
                kind="summary",
                title="Title Field",
                content="Content Field",
                summary="Summary Field",
                aliases=("Alias One", "Alias Two"),
                metadata={"hidden": "Metadata Field"},
            )
        ]

        _ = BM25SearchIndex(docs, tokenizer_name="regex_v1", tokenizer=tokenizer)

        first_index_call = cast(dict[str, Any], fake_bm25_backend["index"][0])
        assert tokenizer.batch_calls == [
            (
                "Title Field",
                "docs/path-field.md",
                "Summary Field",
                "Content Field",
                "Alias One Alias Two",
            )
        ]
        assert first_index_call["corpus_tokens"] == [
            [
                "title",
                "field",
                "docs/path-field.md",
                "summary",
                "field",
                "content",
                "field",
                "alias",
                "one",
                "alias",
                "two",
            ]
        ]

    def test_combined_corpus_uses_canonical_searchable_texts_only(
        self,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class CombinedCorpusTokenizer:
            def __init__(self) -> None:
                self.batch_calls: list[tuple[str, ...]] = []

            def tokenize(self, text: str) -> tuple[str, ...]:
                normalized = text.casefold().replace("\n", " ")
                tokens: list[str] = []
                if "docs/path-field.md" in normalized:
                    tokens.extend(["docs", "path", "field", "md"])
                if "alias one alias two" in normalized:
                    tokens.extend(["alias", "one", "alias", "two"])
                if "metadata field" in normalized:
                    tokens.extend(["metadata", "field"])
                if "title field" in normalized:
                    tokens.extend(["title", "field"])
                if "summary field" in normalized:
                    tokens.extend(["summary", "field"])
                if "content field" in normalized:
                    tokens.extend(["content", "field"])
                return tuple(tokens)

            def tokenize_many(
                self, texts: tuple[str, ...]
            ) -> tuple[tuple[str, ...], ...]:
                self.batch_calls.append(texts)
                return tuple(self.tokenize(text) for text in texts)

            def normalize(self, text: str) -> str:
                return text.casefold()

        tokenizer = CombinedCorpusTokenizer()
        monkeypatch.setattr(
            "snowiki.search.bm25_index.get",
            lambda name: SimpleNamespace(name=name),
        )
        monkeypatch.setattr(
            "snowiki.search.bm25_index.create",
            lambda name: tokenizer,
        )

        docs = [
            SearchDocument(
                id="doc1",
                path="docs/path-field.md",
                kind="summary",
                title="Title Field",
                content="Content Field",
                summary="Summary Field",
                aliases=("Alias One", "Alias Two"),
                metadata={"hidden": "Metadata Field"},
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="regex_v1")
        results = index.search(
            "Alias One Alias Two docs/path-field.md Metadata Field"
        )

        first_index_call = cast(dict[str, Any], fake_bm25_backend["index"][0])
        assert tokenizer.batch_calls == [
            (
                "Title Field\ndocs/path-field.md\nSummary Field\nContent Field\nAlias One Alias Two",
            )
        ]
        assert first_index_call["corpus_tokens"] == [
            [
                "docs",
                "path",
                "field",
                "md",
                "alias",
                "one",
                "alias",
                "two",
                "title",
                "field",
                "summary",
                "field",
                "content",
                "field",
            ]
        ]
        assert results[0].matched_terms == (
            "docs",
            "path",
            "field",
            "md",
            "alias",
            "one",
            "two",
        )

    def test_document_token_texts_delegate_to_canonical_searchable_texts(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        document = SearchDocument(
            id="doc1",
            path="docs/path-field.md",
            kind="summary",
            title="Title Field",
            content="Content Field",
            summary="Summary Field",
            aliases=("Alias One", "Alias Two"),
            metadata={"hidden": "Metadata Field"},
        )

        assert BM25SearchIndex._document_token_texts(document) == document.searchable_texts()

    def test_kiwi_candidate_mode_changes_index_and_query_tokens(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 처리",
                content="자연어 처리는 재미있는 분야입니다.",
            )
        ]

        morphology_index = BM25SearchIndex(
            docs,
            kiwi_lexical_candidate_mode="morphology",
        )
        nouns_index = BM25SearchIndex(
            docs,
            kiwi_lexical_candidate_mode="nouns",
        )

        morphology_results = morphology_index.search("재미있다")
        nouns_results = nouns_index.search("재미있다")

        first_index_call = cast(dict[str, Any], fake_bm25_backend["index"][0])
        second_index_call = cast(dict[str, Any], fake_bm25_backend["index"][1])
        first_retrieve_call = cast(dict[str, Any], fake_bm25_backend["retrieve"][0])

        assert first_index_call["corpus_tokens"][0] == ["자연어", "처리", "재미있"]
        assert second_index_call["corpus_tokens"][0] == ["자연어"]
        assert first_retrieve_call["query_tokens"] == [["재미있"]]
        assert len(fake_bm25_backend["retrieve"]) == 1
        assert morphology_results[0].matched_terms == ("재미있",)
        assert nouns_results == []

    def test_save_and_load_preserve_kiwi_candidate_mode(
        self,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 처리",
                content="자연어 처리는 재미있는 분야입니다.",
            )
        ]
        path = tmp_path / "bm25-index"

        index = BM25SearchIndex(docs, kiwi_lexical_candidate_mode="nouns")
        index.save(str(path))
        loaded = BM25SearchIndex.load(str(path), docs)
        metadata = json.loads(
            path.with_name(f"{path.name}.snowiki_meta.json").read_text()
        )

        assert fake_bm25_backend["save"] == [{"path": str(path)}]
        assert fake_bm25_backend["load"] == [{"path": str(path), "load_corpus": True}]
        assert metadata["tokenizer_name"] == "kiwi_nouns_v1"
        assert loaded.use_kiwi_tokenizer is True
        assert loaded.kiwi_lexical_candidate_mode == "nouns"
        assert loaded.tokenizer_name == "kiwi_nouns_v1"
        assert loaded.tokenizer is not None
        assert loaded.tokenizer.tokenize("자연어 재미있다") == ("자연어",)

    def test_init_accepts_canonical_tokenizer_name(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 처리",
                content="자연어 처리는 재미있는 분야입니다.",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="kiwi_nouns_v1")

        assert index.tokenizer_name == "kiwi_nouns_v1"
        assert index.use_kiwi_tokenizer is True
        assert index.kiwi_lexical_candidate_mode == "nouns"

    def test_init_legacy_false_flag_still_selects_regex(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Test",
                content="Test content.",
            )
        ]

        index = BM25SearchIndex(docs, use_kiwi_tokenizer=False)

        assert index.tokenizer_name == "regex_v1"
        assert index.use_kiwi_tokenizer is False
        assert index.kiwi_lexical_candidate_mode == "morphology"
        assert {"create": "regex_v1"} in fake_bm25_backend["registry"]

    def test_load_accepts_legacy_metadata_without_canonical_tokenizer_name(
        self,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 처리",
                content="자연어 처리는 재미있는 분야입니다.",
            )
        ]
        path = tmp_path / "bm25-index"
        path.with_name(f"{path.name}.snowiki_meta.json").write_text(
            json.dumps(
                {
                    "method": "lucene",
                    "use_kiwi_tokenizer": True,
                    "kiwi_lexical_candidate_mode": "nouns",
                }
            ),
            encoding="utf-8",
        )

        loaded = BM25SearchIndex.load(str(path), docs)

        assert loaded.tokenizer_name == "kiwi_nouns_v1"
        assert loaded.use_kiwi_tokenizer is True
        assert loaded.kiwi_lexical_candidate_mode == "nouns"
        assert fake_bm25_backend["load"] == [{"path": str(path), "load_corpus": True}]

    def test_load_maps_legacy_false_metadata_to_regex_identity(
        self,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Test",
                content="Test content.",
            )
        ]
        path = tmp_path / "bm25-index"
        path.with_name(f"{path.name}.snowiki_meta.json").write_text(
            json.dumps({"method": "lucene", "use_kiwi_tokenizer": False}),
            encoding="utf-8",
        )

        loaded = BM25SearchIndex.load(str(path), docs)

        assert loaded.tokenizer_name == "regex_v1"
        assert loaded.use_kiwi_tokenizer is False
        assert loaded.kiwi_lexical_candidate_mode == "morphology"
        assert fake_bm25_backend["load"] == [{"path": str(path), "load_corpus": True}]

    def test_load_fails_when_legacy_false_metadata_expected_as_current_kiwi(
        self,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Test",
                content="Test content.",
            )
        ]
        path = tmp_path / "bm25-index"
        metadata_path = path.with_name(f"{path.name}.snowiki_meta.json")
        metadata_path.write_text(
            json.dumps({"method": "lucene", "use_kiwi_tokenizer": False}),
            encoding="utf-8",
        )

        with pytest.raises(
            StaleTokenizerArtifactError, match="rebuild required"
        ) as excinfo:
            BM25SearchIndex.load(
                str(path),
                docs,
                expected_tokenizer_name="kiwi_morphology_v1",
            )

        assert excinfo.value.details == {
            "artifact_path": metadata_path.as_posix(),
            "requested_tokenizer_name": "kiwi_morphology_v1",
            "stored_tokenizer_name": "regex_v1",
            "rebuild_required": True,
            "reason": "tokenizer identity mismatch",
        }
        assert fake_bm25_backend["load"] == []

    def test_load_fails_closed_when_metadata_tokenizer_identity_missing(
        self,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Test",
                content="Test content.",
            )
        ]
        path = tmp_path / "bm25-index"
        metadata_path = path.with_name(f"{path.name}.snowiki_meta.json")
        metadata_path.write_text(json.dumps({"method": "lucene"}), encoding="utf-8")

        with pytest.raises(
            StaleTokenizerArtifactError, match="rebuild required"
        ) as excinfo:
            BM25SearchIndex.load(str(path), docs)

        assert excinfo.value.details == {
            "artifact_path": metadata_path.as_posix(),
            "requested_tokenizer_name": "kiwi_morphology_v1",
            "stored_tokenizer_name": None,
            "rebuild_required": True,
            "reason": "missing tokenizer identity",
        }
        assert fake_bm25_backend["load"] == []

    def test_load_fails_closed_when_expected_tokenizer_mismatches_stored_identity(
        self,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 처리",
                content="자연어 처리는 재미있는 분야입니다.",
            )
        ]
        path = tmp_path / "bm25-index"

        index = BM25SearchIndex(docs, tokenizer_name="kiwi_nouns_v1")
        index.save(str(path))

        with pytest.raises(
            StaleTokenizerArtifactError, match="rebuild required"
        ) as excinfo:
            BM25SearchIndex.load(
                str(path),
                docs,
                expected_tokenizer_name="kiwi_morphology_v1",
            )

        assert excinfo.value.details == {
            "artifact_path": path.with_name(
                f"{path.name}.snowiki_meta.json"
            ).as_posix(),
            "requested_tokenizer_name": "kiwi_morphology_v1",
            "stored_tokenizer_name": "kiwi_nouns_v1",
            "rebuild_required": True,
            "reason": "tokenizer identity mismatch",
        }
        assert fake_bm25_backend["load"] == []

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError, match="Invalid method"):
            BM25SearchIndex([], method="invalid")

    def test_invalid_kiwi_candidate_mode(self) -> None:
        with pytest.raises(ValueError, match="Invalid Kiwi lexical candidate mode"):
            BM25SearchIndex([], kiwi_lexical_candidate_mode=cast(Any, "verbs"))

    @pytest.mark.parametrize(
        "method", ["robertson", "atire", "bm25l", "bm25+", "lucene"]
    )
    def test_different_methods(
        self,
        method: str,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python Test",
                content="Python content.",
            ),
        ]

        index = BM25SearchIndex(docs, method=method, tokenizer_name="regex_v1")
        assert index.method == method
        results = index.search("Python")
        assert isinstance(results, list)
        assert any(
            call.get("create") == "regex_v1" for call in fake_bm25_backend["registry"]
        )

    def test_search_with_limit(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id=f"doc{i}",
                path=f"test/doc{i}.md",
                kind="summary",
                title=f"Document {i}",
                content=f"Content about Python {i}.",
            )
            for i in range(10)
        ]
        index = BM25SearchIndex(docs, tokenizer_name="regex_v1")
        results = index.search("Python", limit=5)
        assert len(results) <= 5
        assert fake_bm25_backend["retrieve"][0]["k"] == 5

    def test_bm25s_calls_disable_progress_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        index_calls: list[dict[str, object]] = []
        retrieve_calls: list[dict[str, object]] = []

        class FakeRegexTokenizer:
            def tokenize(self, text: str) -> tuple[str, ...]:
                return ("python",)

            def normalize(self, text: str) -> str:
                return text.lower()

        class FakeBM25:
            def __init__(self, **kwargs) -> None:
                del kwargs

            def index(self, corpus_tokens, **kwargs) -> None:
                index_calls.append({"corpus_tokens": corpus_tokens, **kwargs})

            def retrieve(self, query_tokens, **kwargs):
                retrieve_calls.append({"query_tokens": query_tokens, **kwargs})
                return (
                    SimpleNamespace(flatten=lambda: [0]),
                    SimpleNamespace(flatten=lambda: [1.0]),
                )

        monkeypatch.setattr(
            "snowiki.search.bm25_index.bm25s",
            SimpleNamespace(BM25=FakeBM25),
        )
        monkeypatch.setattr(
            "snowiki.search.bm25_index.create",
            lambda name: FakeRegexTokenizer(),
        )

        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python Programming",
                content="Python is a great language for programming.",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="regex_v1")
        results = index.search("Python")

        assert len(results) == 1
        assert index_calls == [
            {
                "corpus_tokens": [["python"]],
                "show_progress": False,
                "leave_progress": False,
            }
        ]
        assert retrieve_calls == [
            {
                "query_tokens": [["python"]],
                "k": 1,
                "show_progress": False,
                "leave_progress": False,
            }
        ]

    def test_init_accepts_subword_tokenizer_name(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python README",
                content="README.md path",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="hf_wordpiece_v1")

        assert index.tokenizer_name == "hf_wordpiece_v1"
        assert index.use_kiwi_tokenizer is True

    def test_save_load_preserves_subword_tokenizer_artifact(
        self,
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python README",
                content="README.md path Snowiki personal wiki qmd search",
            )
        ]
        path = tmp_path / "bm25-index"

        index = BM25SearchIndex(docs, tokenizer_name="hf_wordpiece_v1")
        expected = (
            index.tokenizer.tokenize("Python README.md") if index.tokenizer else ()
        )
        index.save(str(path))
        loaded = BM25SearchIndex.load(str(path), docs)

        metadata = json.loads(
            path.with_name(f"{path.name}.snowiki_meta.json").read_text(encoding="utf-8")
        )
        artifact = cast(dict[str, object], metadata["tokenizer_artifact"])
        assert artifact["type"] == "bert_wordpiece_vocab"
        assert (tmp_path / cast(str, artifact["path"])).is_file()
        assert loaded.tokenizer_name == "hf_wordpiece_v1"
        assert loaded.tokenizer is not None
        assert loaded.tokenizer.tokenize("Python README.md") == expected

    def test_cache_artifact_preserves_subword_tokenizer_artifact(
        self,
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python README",
                content="README.md path Snowiki personal wiki qmd search",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="hf_wordpiece_v1")
        expected = (
            index.tokenizer.tokenize("Python README.md") if index.tokenizer else ()
        )
        artifact_path = tmp_path / "index.bm25cache"
        artifact_path.write_bytes(index.to_cache_bytes())

        loaded = BM25SearchIndex.load_cache_artifact(
            artifact_path,
            docs,
            expected_tokenizer_name="hf_wordpiece_v1",
        )

        assert loaded.tokenizer_name == "hf_wordpiece_v1"
        assert loaded.tokenizer is not None
        assert loaded.tokenizer.tokenize("Python README.md") == expected

    def test_load_rejects_missing_subword_tokenizer_artifact(
        self,
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python README",
                content="README.md path Snowiki personal wiki qmd search",
            )
        ]
        path = tmp_path / "bm25-index"
        index = BM25SearchIndex(docs, tokenizer_name="hf_wordpiece_v1")
        index.save(str(path))
        artifact_path = path.with_name("index.wordpiece-vocab.txt")
        artifact_path.unlink()

        with pytest.raises(ValueError, match="Missing BM25 tokenizer artifact"):
            BM25SearchIndex.load(
                str(path),
                docs,
                expected_tokenizer_name="hf_wordpiece_v1",
            )

    def test_load_rejects_unsafe_subword_tokenizer_artifact_path(
        self,
        tmp_path: Path,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python README",
                content="README.md path Snowiki personal wiki qmd search",
            )
        ]
        path = tmp_path / "bm25-index"
        index = BM25SearchIndex(docs, tokenizer_name="hf_wordpiece_v1")
        index.save(str(path))
        metadata_path = path.with_name(f"{path.name}.snowiki_meta.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        tokenizer_artifact = cast(dict[str, object], metadata["tokenizer_artifact"])
        tokenizer_artifact["path"] = "../outside-vocab.txt"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        with pytest.raises(ValueError, match="Unsafe BM25 tokenizer artifact path"):
            BM25SearchIndex.load(
                str(path),
                docs,
                expected_tokenizer_name="hf_wordpiece_v1",
            )

    def test_init_accepts_mecab_tokenizer_name(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="안녕하세요 Snowiki",
                content="README.md path",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="mecab_morphology_v1")

        assert index.tokenizer_name == "mecab_morphology_v1"
        assert index.use_kiwi_tokenizer is True

    def test_regex_v1_uses_snowiki_tokenizer_not_bm25s_tokenize(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        bm25s_tokenize_calls: list[dict[str, object]] = []

        def capturing_tokenize(
            texts: str | list[str], **kwargs: object
        ) -> list[list[str]]:
            bm25s_tokenize_calls.append({"texts": texts, **kwargs})
            return [["dummy"]]

        class FakeBM25:
            def __init__(self, **kwargs: object) -> None:
                del kwargs

            def index(self, corpus_tokens: list[list[str]], **kwargs: object) -> None:
                del corpus_tokens, kwargs

            def retrieve(
                self, query_tokens: list[list[str]], **kwargs: object
            ) -> tuple[SimpleNamespace, SimpleNamespace]:
                del query_tokens, kwargs
                return (
                    SimpleNamespace(flatten=lambda: []),
                    SimpleNamespace(flatten=lambda: []),
                )

        monkeypatch.setattr(
            "snowiki.search.bm25_index.bm25s",
            SimpleNamespace(BM25=FakeBM25, tokenize=capturing_tokenize),
        )

        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="The quick brown fox",
                content="is jumping over the lazy dog",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="regex_v1")
        _ = index.search("the fox")

        assert bm25s_tokenize_calls == []
        assert index.tokenizer is not None
        assert index.tokenizer_name == "regex_v1"

    def test_regex_v1_preserves_english_stopwords(self) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="The cat and the dog",
                content="",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="regex_v1")

        assert "the" in index.corpus_tokens[0]
        assert "and" in index.corpus_tokens[0]

    def test_regex_v1_query_tokenization_matches_index(self) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="The quick brown fox",
                content="is jumping over the lazy dog",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="regex_v1")
        results = index.search("the fox")

        assert len(results) == 1
        assert "the" in results[0].matched_terms
        assert "fox" in results[0].matched_terms

    def test_regex_v1_query_tokenization_matches_index_for_punctuation_case_and_unicode(
        self,
    ) -> None:
        docs = [
            SearchDocument(
                id="doc1",
                path="docs/README.md",
                kind="summary",
                title="README.md: Snowiki 자연어-처리",
                content="Mixed CASE tokens, API_v2, and 한글 punctuation!",
            )
        ]

        index = BM25SearchIndex(docs, tokenizer_name="regex_v1")
        results = index.search("readme MD snowiki 자연어 처리 api V2")

        assert len(results) == 1
        normalized_query_terms = {
            "readme",
            "md",
            "snowiki",
            "api",
            "v2",
            "자연어",
            "자연",
            "연어",
            "처리",
        }
        assert normalized_query_terms.issubset(set(results[0].matched_terms))
        assert normalized_query_terms.issubset(set(index.corpus_tokens[0]))
        assert results[0].matched_terms == (
            "readme",
            "md",
            "snowiki",
            "자연어",
            "자연",
            "연어",
            "처리",
            "api",
            "v2",
        )
