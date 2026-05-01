from __future__ import annotations

from snowiki.search.registry import get as get_tokenizer_spec
from snowiki.storage.index_manifest import RetrievalIdentity


def retrieval_identity_for_tokenizer(tokenizer_name: str) -> RetrievalIdentity:
    spec = get_tokenizer_spec(tokenizer_name)
    return RetrievalIdentity(name=spec.name, family=spec.family, version=str(spec.version))
