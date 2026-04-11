from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class Zone(StrEnum):
    RAW = "raw"
    NORMALIZED = "normalized"
    COMPILED = "compiled"
    INDEX = "index"


@dataclass(frozen=True)
class StoragePaths:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).expanduser())

    @property
    def raw(self) -> Path:
        return self.zone(Zone.RAW)

    @property
    def normalized(self) -> Path:
        return self.zone(Zone.NORMALIZED)

    @property
    def compiled(self) -> Path:
        return self.zone(Zone.COMPILED)

    @property
    def index(self) -> Path:
        return self.zone(Zone.INDEX)

    @property
    def quarantine(self) -> Path:
        return self.root / "quarantine"

    def zone(self, zone: Zone | str) -> Path:
        zone_value = zone.value if isinstance(zone, Zone) else str(zone)
        return self.root / zone_value

    def ensure_all(self) -> None:
        for zone in Zone:
            self.zone(zone).mkdir(parents=True, exist_ok=True)
        self.quarantine.mkdir(parents=True, exist_ok=True)


def sanitize_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip(".-")
    return cleaned or "unknown"


def ensure_utc_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(tz=UTC)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        value = datetime.fromisoformat(normalized)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def isoformat_utc(value: datetime | str | None) -> str:
    return ensure_utc_datetime(value).isoformat().replace("+00:00", "Z")


def relative_to_root(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_bytes(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    temp_path: Path | None = None

    try:
        handle, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temp_path = Path(temp_name)
        with os.fdopen(handle, "wb") as stream:
            handle = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        return path
    except Exception:
        if handle is not None:
            os.close(handle)
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        raise


def atomic_write_json(path: Path, data: Any) -> Path:
    rendered = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    return atomic_write_bytes(path, f"{rendered}\n".encode())
