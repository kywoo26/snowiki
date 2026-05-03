from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from click.testing import CliRunner, Result

from snowiki.cli.main import app


def _invoke(args: list[str], *, root: Path) -> Result:
    runner = CliRunner()
    return runner.invoke(app, args, env={"SNOWIKI_ROOT": root.as_posix()})


def _payload(result: Result) -> dict[str, Any]:
    data = json.loads(result.output)
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def _write_markdown(path: Path, *, title: str, summary: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        f"---\ntitle: {title}\nsummary: {summary}\n---\n# {title}\n\n{body}\n",
        encoding="utf-8",
    )


def _workspace_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix())
        if path.is_file()
    }


def _prepare_rebuilt_workspace(tmp_path: Path) -> tuple[Path, Path]:
    snowiki_root = tmp_path / "snowiki"
    source = tmp_path / "vault" / "evidence.md"
    _write_markdown(
        source,
        title="Phase 6 Evidence",
        summary="Evidence for external mutation contracts.",
        body="Snowiki preserves mutation behavior through CLI-visible contracts.",
    )

    ingest = _invoke(["ingest", source.as_posix(), "--rebuild", "--output", "json"], root=snowiki_root)
    assert ingest.exit_code == 0, ingest.output
    evidence_path = sorted((snowiki_root / "compiled" / "summaries").glob("*.md"))[0]
    return snowiki_root, evidence_path.relative_to(snowiki_root)


def test_ingest_json_contract_and_rebuild_option(tmp_path: Path) -> None:
    snowiki_root = tmp_path / "snowiki"
    source = tmp_path / "vault" / "note.md"
    _write_markdown(
        source,
        title="Phase 6 Ingest",
        summary="Ingest contract fixture.",
        body="Ingest accepts Markdown and records raw plus normalized state.",
    )

    ingest = _invoke(["ingest", source.as_posix(), "--output", "json"], root=snowiki_root)

    assert ingest.exit_code == 0, ingest.output
    payload = _payload(ingest)
    assert payload["ok"] is True
    assert payload["command"] == "ingest"
    result = payload["result"]
    assert result["documents_seen"] == 1
    assert result["documents_inserted"] == 1
    assert result["rebuild_required"] is True
    assert "rebuild" not in result
    document = result["documents"][0]
    assert document["relative_path"] == "note.md"
    assert (snowiki_root / document["raw_path"]).exists()
    assert (snowiki_root / document["normalized_path"]).exists()

    rebuilt = _invoke(["ingest", source.parent.as_posix(), "--rebuild", "--output", "json"], root=snowiki_root)

    assert rebuilt.exit_code == 0, rebuilt.output
    rebuilt_payload = _payload(rebuilt)
    rebuilt_result = rebuilt_payload["result"]
    assert rebuilt_payload["ok"] is True
    assert rebuilt_payload["command"] == "ingest"
    assert rebuilt_result["documents_seen"] == 1
    assert rebuilt_result["rebuild_required"] is False
    assert rebuilt_result["rebuild"]["compiled_count"] >= 1
    assert (snowiki_root / "compiled" / "index.md").exists()
    assert (snowiki_root / "index" / "manifest.json").exists()


def test_fileback_preview_and_apply_review_gate_contract(tmp_path: Path) -> None:
    snowiki_root, evidence_path = _prepare_rebuilt_workspace(tmp_path)
    before_preview = _workspace_snapshot(snowiki_root)

    preview = _invoke(
        [
            "fileback",
            "preview",
            "What external contract is preserved?",
            "--answer-markdown",
            "Fileback remains reviewable before it writes durable memory.",
            "--summary",
            "Reviewable fileback contract.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--output",
            "json",
        ],
        root=snowiki_root,
    )

    assert preview.exit_code == 0, preview.output
    assert _workspace_snapshot(snowiki_root) == before_preview
    preview_payload = _payload(preview)
    assert preview_payload["ok"] is True
    assert preview_payload["command"] == "fileback preview"
    proposal = preview_payload["result"]["proposal"]
    apply_plan = proposal["apply_plan"]
    assert proposal["proposal_version"] == 1
    assert proposal["draft"]["question"] == "What external contract is preserved?"
    assert apply_plan["rebuild_required"] is True
    assert apply_plan["raw_note_path"].startswith("raw/manual/questions/")
    assert apply_plan["normalized_path"].startswith("normalized/manual-question/")
    assert "proposed_raw_note_body" in apply_plan
    assert "proposed_normalized_record_payload" in apply_plan
    assert not (snowiki_root / apply_plan["raw_note_path"]).exists()
    assert not (snowiki_root / apply_plan["normalized_path"]).exists()

    before_queue = _workspace_snapshot(snowiki_root)
    queued_preview = _invoke(
        [
            "fileback",
            "preview",
            "What queued contract is preserved?",
            "--answer-markdown",
            "Queued preview writes only pending proposal state.",
            "--summary",
            "Queued preview contract.",
            "--evidence-path",
            evidence_path.as_posix(),
            "--queue",
            "--output",
            "json",
        ],
        root=snowiki_root,
    )

    assert queued_preview.exit_code == 0, queued_preview.output
    queued_payload = _payload(queued_preview)
    assert queued_payload["ok"] is True
    assert queued_payload["command"] == "fileback preview"
    queue_result = queued_payload["result"]["queue"]
    queued_proposal = queued_payload["result"]["proposal"]
    queued_apply_plan = queued_proposal["apply_plan"]
    assert queue_result["status"] == "pending"
    assert queue_result["proposal_path"].startswith("queue/proposals/pending/")
    queued_snapshot = _workspace_snapshot(snowiki_root)
    expected_snapshot = dict(before_queue)
    expected_snapshot[queue_result["proposal_path"]] = queued_snapshot[
        queue_result["proposal_path"]
    ]
    assert queued_snapshot == expected_snapshot
    assert not (snowiki_root / queued_apply_plan["raw_note_path"]).exists()
    assert not (snowiki_root / queued_apply_plan["normalized_path"]).exists()

    malformed_payload = dict(preview_payload)
    malformed_payload["result"] = dict(preview_payload["result"])
    del malformed_payload["result"]["proposal"]
    malformed_file = tmp_path / "malformed-fileback.json"
    malformed_file.write_text(json.dumps(malformed_payload), encoding="utf-8")
    rejected = _invoke(
        ["fileback", "apply", "--proposal-file", malformed_file.as_posix(), "--output", "json"],
        root=snowiki_root,
    )

    assert rejected.exit_code != 0
    rejected_payload = _payload(rejected)
    assert rejected_payload["ok"] is False
    assert rejected_payload["error"]["code"] == "fileback_apply_failed"
    assert not (snowiki_root / apply_plan["raw_note_path"]).exists()
    assert not (snowiki_root / apply_plan["normalized_path"]).exists()

    reviewed_file = tmp_path / "reviewed-fileback.json"
    reviewed_file.write_text(json.dumps(preview_payload), encoding="utf-8")
    applied = _invoke(
        ["fileback", "apply", "--proposal-file", reviewed_file.as_posix(), "--output", "json"],
        root=snowiki_root,
    )

    assert applied.exit_code == 0, applied.output
    applied_payload = _payload(applied)
    assert applied_payload["ok"] is True
    assert applied_payload["command"] == "fileback apply"
    applied_result = applied_payload["result"]
    assert (snowiki_root / applied_result["raw_ref"]["path"]).exists()
    assert (snowiki_root / applied_result["normalized_path"]).exists()
    assert (snowiki_root / applied_result["compiled_path"]).exists()
    assert (snowiki_root / "index" / "manifest.json").exists()


def test_prune_sources_dry_run_and_delete_confirmation_contract(tmp_path: Path) -> None:
    snowiki_root = tmp_path / "snowiki"
    source = tmp_path / "vault" / "stale.md"
    _write_markdown(
        source,
        title="Phase 6 Prune",
        summary="Prune contract fixture.",
        body="This source will go missing after ingest.",
    )
    ingest = _invoke(["ingest", source.as_posix(), "--output", "json"], root=snowiki_root)
    assert ingest.exit_code == 0, ingest.output
    document = _payload(ingest)["result"]["documents"][0]
    source.unlink()

    dry_run = _invoke(["prune", "sources", "--dry-run", "--output", "json"], root=snowiki_root)

    assert dry_run.exit_code == 0, dry_run.output
    dry_run_payload = _payload(dry_run)
    assert dry_run_payload["ok"] is True
    assert dry_run_payload["command"] == "prune sources"
    dry_run_result = dry_run_payload["result"]
    assert dry_run_result["dry_run"] is True
    assert dry_run_result["candidate_count"] == 2
    assert dry_run_result["deleted_count"] == 0
    assert dry_run_result["tombstone_path"] is None
    assert (snowiki_root / document["normalized_path"]).exists()
    assert (snowiki_root / document["raw_path"]).exists()

    missing_yes = _invoke(
        ["prune", "sources", "--delete", "--all-candidates", "--output", "json"],
        root=snowiki_root,
    )
    missing_all_candidates = _invoke(
        ["prune", "sources", "--delete", "--yes", "--output", "json"],
        root=snowiki_root,
    )

    for failed in (missing_yes, missing_all_candidates):
        assert failed.exit_code != 0
        payload = _payload(failed)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "prune_confirmation_required"
    assert (snowiki_root / document["normalized_path"]).exists()
    assert (snowiki_root / document["raw_path"]).exists()
    assert not (snowiki_root / "index" / "source-prune-tombstones.json").exists()

    deleted = _invoke(
        [
            "prune",
            "sources",
            "--delete",
            "--yes",
            "--all-candidates",
            "--output",
            "json",
        ],
        root=snowiki_root,
    )

    assert deleted.exit_code == 0, deleted.output
    deleted_payload = _payload(deleted)
    assert deleted_payload["ok"] is True
    assert deleted_payload["command"] == "prune sources"
    deleted_result = deleted_payload["result"]
    assert deleted_result["dry_run"] is False
    assert deleted_result["deleted_count"] == 2
    assert document["normalized_path"] in deleted_result["deleted"]
    assert document["raw_path"] in deleted_result["deleted"]
    assert deleted_result["tombstone_path"] == "index/source-prune-tombstones.json"
    assert deleted_result["rebuild"]["compiled_count"] >= 1
    assert not (snowiki_root / document["normalized_path"]).exists()
    assert not (snowiki_root / document["raw_path"]).exists()
    assert (snowiki_root / "index" / "source-prune-tombstones.json").exists()
    assert (snowiki_root / "compiled" / "index.md").exists()


def test_rebuild_manifest_and_runtime_visible_state_contract(tmp_path: Path) -> None:
    snowiki_root = tmp_path / "snowiki"
    source = tmp_path / "vault" / "cache-visible.md"
    _write_markdown(
        source,
        title="Phase 6 Alpha State",
        summary="Alpha rebuild state.",
        body="The first rebuild-visible state contains alpha content.",
    )
    first_ingest = _invoke(["ingest", source.as_posix(), "--rebuild", "--output", "json"], root=snowiki_root)
    assert first_ingest.exit_code == 0, first_ingest.output

    warm_query = _invoke(
        ["query", "alpha content", "--mode", "lexical", "--top-k", "5", "--output", "json"],
        root=snowiki_root,
    )
    assert warm_query.exit_code == 0, warm_query.output
    assert _payload(warm_query)["result"]["hits"]

    _write_markdown(
        source,
        title="Phase 6 Beta State",
        summary="Beta rebuild state.",
        body="The second rebuild-visible state contains beta content.",
    )
    second_ingest = _invoke(["ingest", source.as_posix(), "--rebuild", "--output", "json"], root=snowiki_root)
    assert second_ingest.exit_code == 0, second_ingest.output

    rebuild = _invoke(["rebuild", "--output", "json"], root=snowiki_root)

    assert rebuild.exit_code == 0, rebuild.output
    rebuild_payload = _payload(rebuild)
    assert rebuild_payload["ok"] is True
    assert rebuild_payload["command"] == "rebuild"
    rebuild_result = rebuild_payload["result"]
    assert rebuild_result["index_manifest"] == "index/manifest.json"
    assert rebuild_result["content_identity"] == rebuild_result["current_content_identity"]
    manifest = json.loads((snowiki_root / "index" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity"]["normalized"] == rebuild_result["content_identity"]["normalized"]
    assert manifest["identity"]["compiled"] == rebuild_result["content_identity"]["compiled"]

    fresh_query = _invoke(
        ["query", "beta content", "--mode", "lexical", "--top-k", "5", "--output", "json"],
        root=snowiki_root,
    )
    assert fresh_query.exit_code == 0, fresh_query.output
    hits = _payload(fresh_query)["result"]["hits"]
    assert any(hit["title"] == "Phase 6 Beta State" for hit in hits)
