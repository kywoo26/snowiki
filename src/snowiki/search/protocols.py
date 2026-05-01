from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import SearchHit
from .registry import SearchTokenizer
from .requests import (  # pyright: ignore[reportMissingImports]
    RuntimeSearchRequest,  # pyright: ignore[reportUnknownVariableType]
)


class RuntimeSearchIndex(Protocol):
    """Primary runtime search interface used by query and recall policies."""

    @property
    def size(self) -> int: ...

    @property
    def tokenizer(self) -> SearchTokenizer: ...

    def search(
        self,
        request: RuntimeSearchRequest,  # pyright: ignore[reportUnknownParameterType]
    ) -> Sequence[SearchHit]: ...
