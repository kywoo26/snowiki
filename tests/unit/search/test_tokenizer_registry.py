from __future__ import annotations

from types import SimpleNamespace

import pytest

from snowiki.search import (
    DEFAULT_TOKENIZER_NAME,
    all_candidates,
    create,
    default,
    get,
    is_tokenizer_compatible,
)

CANONICAL_NAMES = {spec.name for spec in all_candidates()}
ENGINE_LABELS = {"lexical", "bm25s"}


def _token(form: str, tag: str) -> SimpleNamespace:
    return SimpleNamespace(form=form, tag=tag)


@pytest.fixture
def fake_kiwi(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    class FakeKiwi:
        def __init__(self, num_workers: int | None = None) -> None:
            calls.append({"init_num_workers": num_workers})

        def tokenize(self, text: str, **kwargs: object) -> list[SimpleNamespace]:
            calls.append({"text": text, **kwargs})
            fixtures: dict[str, list[SimpleNamespace]] = {
                "자연어 처리는 재미있습니다": [
                    _token("자연어", "NNG"),
                    _token("처리", "NNG"),
                    _token("재미있", "VA"),
                ],
                "자연어 Python 처리 README.md /src/app.py": [
                    _token("자연어", "NNG"),
                    _token("처리", "NNG"),
                ]
            }
            return fixtures.get(text, [])

    monkeypatch.setattr("snowiki.search.kiwi_tokenizer.Kiwi", FakeKiwi)
    return calls


def test_canonical_names_contract() -> None:
    assert "regex_v1" in CANONICAL_NAMES
    assert "kiwi_morphology_v1" in CANONICAL_NAMES
    assert "kiwi_nouns_v1" in CANONICAL_NAMES
    assert "mecab_morphology_v1" in CANONICAL_NAMES
    assert "hf_wordpiece_v1" in CANONICAL_NAMES
    assert len(CANONICAL_NAMES) == 5


def test_default_runtime_tokenizer_contract() -> None:
    spec = default()

    assert spec.name == DEFAULT_TOKENIZER_NAME
    assert spec.runtime_supported is True


def test_candidate_listing_returns_all_registered_specs() -> None:
    assert {spec.name for spec in all_candidates()} == {
        "regex_v1",
        "kiwi_morphology_v1",
        "kiwi_nouns_v1",
        "mecab_morphology_v1",
        "hf_wordpiece_v1",
    }


def test_lookup_returns_immutable_spec() -> None:
    spec = get("kiwi_morphology_v1")

    assert spec.family == "kiwi"
    assert spec.version == 1
    assert spec.runtime_supported is False


def test_create_returns_fresh_regex_instances() -> None:
    first = create("regex_v1")
    second = create("regex_v1")

    assert first is not second
    assert first.tokenize("Hello/세계") == ("hello", "세계")
    assert first.normalize(" Hello\tWorld ") == "hello world"


def test_create_uses_kiwi_modes_with_fresh_instances(
    fake_kiwi: list[dict[str, object]],
) -> None:
    morphology = create("kiwi_morphology_v1")
    nouns = create("kiwi_nouns_v1")

    assert morphology is not nouns
    assert morphology.tokenize("자연어 처리는 재미있습니다") == (
        "자연어",
        "처리",
        "재미있",
    )
    assert nouns.tokenize("자연어 처리는 재미있습니다") == ("자연어", "처리")
    assert [call["text"] for call in fake_kiwi if "text" in call] == [
        "자연어 처리는 재미있습니다",
        "자연어 처리는 재미있습니다",
    ]


def test_kiwi_registry_candidates_preserve_mixed_language_signal(
    fake_kiwi: list[dict[str, object]],
) -> None:
    morphology = create("kiwi_morphology_v1")

    assert morphology.tokenize("자연어 Python 처리 README.md /src/app.py") == (
        "python",
        "readme",
        "md",
        "src",
        "app",
        "py",
        "자연어",
        "처리",
    )
def test_engine_labels_are_not_tokenizer_identities() -> None:
    for label in ENGINE_LABELS:
        assert label not in CANONICAL_NAMES


def test_missing_identity_fail_closed() -> None:
    assert is_tokenizer_compatible(None, "regex_v1") is False
    assert is_tokenizer_compatible(None, "kiwi_morphology_v1") is False

    assert is_tokenizer_compatible("regex_v1", "kiwi_morphology_v1") is False

    assert is_tokenizer_compatible("regex_v1", "regex_v1") is True


def test_create_uses_wordpiece_tokenizer_for_benchmark_candidate() -> None:
    tokenizer = create("hf_wordpiece_v1")

    assert tokenizer.tokenize("Python README.md")


def test_create_uses_mecab_tokenizer_for_benchmark_candidate() -> None:
    tokenizer = create("mecab_morphology_v1")

    tokens = tokenizer.tokenize("안녕하세요 Snowiki 입니다")

    assert "snowiki" in tokens
    assert any(token in {"안녕", "하", "세요", "입니다"} for token in tokens)
