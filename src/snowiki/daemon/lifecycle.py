from __future__ import annotations

import os
from pathlib import Path
from threading import Thread
from typing import Any

from snowiki.storage.zones import atomic_write_json, isoformat_utc

from .cache import TTLQueryCache
from .warm_index import WarmIndexManager


class DaemonLifecycle:
    def __init__(
        self,
        *,
        server: Any,
        warm_indexes: WarmIndexManager,
        cache: TTLQueryCache,
        host: str,
        port: int,
        state_file: str | Path,
    ) -> None:
        self.server = server
        self.warm_indexes = warm_indexes
        self.cache = cache
        self.host = host
        self.port = port
        self.state_file = Path(state_file)

    def mark_started(self) -> dict[str, Any]:
        payload = self.status_payload()
        atomic_write_json(self.state_file, payload)
        return payload

    def mark_stopped(self) -> None:
        if self.state_file.exists():
            self.state_file.unlink()

    def health_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "pid": os.getpid(),
            "host": self.host,
            "port": self.port,
            "cache": self.cache.stats(),
            "indexes": self.warm_indexes.health(),
        }

    def status_payload(self) -> dict[str, Any]:
        return {
            **self.health_payload(),
            "started_at": isoformat_utc(None),
            "url": f"http://{self.host}:{self.port}",
        }

    def stop_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "stopping": True,
            "pid": os.getpid(),
        }

    def begin_shutdown(self) -> None:
        Thread(target=self.server.shutdown, daemon=True).start()
