from __future__ import annotations

import snowiki.fileback as fileback


def test_fileback_facade_exposes_only_cli_entrypoints() -> None:
    assert fileback.__all__ == [
        "apply_fileback_proposal",
        "apply_queued_fileback_proposal",
        "auto_apply_fileback_proposal",
        "build_fileback_proposal",
        "list_queued_fileback_proposals",
        "prune_queued_fileback_proposals",
        "queue_fileback_proposal",
        "reject_queued_fileback_proposal",
        "resolve_preview_root",
        "show_queued_fileback_proposal",
    ]
    assert callable(fileback.apply_fileback_proposal)
    assert callable(fileback.apply_queued_fileback_proposal)
    assert callable(fileback.auto_apply_fileback_proposal)
    assert callable(fileback.build_fileback_proposal)
    assert callable(fileback.list_queued_fileback_proposals)
    assert callable(fileback.prune_queued_fileback_proposals)
    assert callable(fileback.queue_fileback_proposal)
    assert callable(fileback.reject_queued_fileback_proposal)
    assert callable(fileback.resolve_preview_root)
    assert callable(fileback.show_queued_fileback_proposal)
    assert not hasattr(fileback, "build_proposed_write_set")
