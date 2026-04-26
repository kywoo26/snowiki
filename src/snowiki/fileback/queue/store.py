from __future__ import annotations

from pathlib import Path

from snowiki.storage.zones import StoragePaths, relative_to_root

from ..models import FILEBACK_PROPOSAL_ID_PATTERN
from .types import PENDING_QUEUE_STATUS, QueueStatus


def queue_status_dir(root: Path, status: QueueStatus) -> Path:
    return _validated_queue_status_dir(root, status)


def pending_proposals_dir(root: Path) -> Path:
    return queue_status_dir(root, PENDING_QUEUE_STATUS)


def queue_proposal_path(root: Path, proposal_id: str, status: QueueStatus) -> Path:
    validate_queue_proposal_id(proposal_id)
    return queue_status_dir(root, status) / f"{proposal_id}.json"


def pending_proposal_path(root: Path, proposal_id: str) -> Path:
    return queue_proposal_path(root, proposal_id, PENDING_QUEUE_STATUS)


def find_existing_queue_state_paths(root: Path, proposal_id: str) -> list[Path]:
    validate_queue_proposal_id(proposal_id)
    path = pending_proposal_path(root, proposal_id)
    if path.exists() or path.is_symlink():
        return [path]
    return []


def iter_pending_queue_paths(root: Path) -> list[Path]:
    queue_dir = pending_proposals_dir(root)
    if not queue_dir.exists():
        return []
    return sorted(queue_dir.glob("*.json"), key=lambda candidate: candidate.as_posix())


def validate_queue_proposal_id(proposal_id: str) -> None:
    if FILEBACK_PROPOSAL_ID_PATTERN.fullmatch(proposal_id) is None:
        raise ValueError("proposal_id must match fileback-proposal-<16 lowercase hex chars>")


def is_inside_root(root: Path, path: Path) -> bool:
    try:
        _ = path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_queue_file_path(root: Path, path: Path, expected_status: QueueStatus) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("queue proposal path must be a non-symlink regular file")
    validate_queue_proposal_id(path.stem)
    resolved_path = path.resolve(strict=True)
    expected_dir = queue_status_dir(root, expected_status).resolve(strict=True)
    if not is_inside_root(root, resolved_path):
        raise ValueError("queue proposal path must stay inside the Snowiki root")
    try:
        _ = resolved_path.relative_to(expected_dir)
    except ValueError as exc:
        raise ValueError("queue proposal path must match the expected status directory") from exc


def _validated_queue_status_dir(root: Path, status: QueueStatus) -> Path:
    resolved_root = root.expanduser().resolve()
    storage_paths = StoragePaths(resolved_root)
    status_dir = storage_paths.queue_proposals / status
    for path in (storage_paths.queue, storage_paths.queue_proposals, status_dir):
        if path.is_symlink():
            raise ValueError(
                f"queue path must not be a symlink: {relative_to_root(resolved_root, path)}"
            )
        if path.exists():
            resolved_path = path.resolve(strict=True)
            if not is_inside_root(resolved_root, resolved_path):
                raise ValueError("queue path must stay inside the Snowiki root")
            if not path.is_dir():
                raise ValueError(
                    f"queue path must be a directory: {relative_to_root(resolved_root, path)}"
                )
    return status_dir
