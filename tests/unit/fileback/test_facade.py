from __future__ import annotations

import snowiki.fileback as fileback


def test_fileback_facade_exposes_only_cli_entrypoints() -> None:
    assert fileback.__all__ == [
        "apply_fileback_proposal",
        "build_fileback_proposal",
        "resolve_preview_root",
    ]
    assert callable(fileback.apply_fileback_proposal)
    assert callable(fileback.build_fileback_proposal)
    assert callable(fileback.resolve_preview_root)
    assert not hasattr(fileback, "build_proposed_write_set")
