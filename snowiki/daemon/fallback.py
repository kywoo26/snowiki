from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib import error, request


class DaemonUnavailableError(RuntimeError):
    pass


def daemon_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 1.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    target = f"{base_url.rstrip('/')}{path}"
    http_request = request.Request(target, data=body, method=method, headers=headers)

    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
    except (error.HTTPError, error.URLError, OSError, TimeoutError) as exc:
        raise DaemonUnavailableError(str(exc)) from exc

    try:
        decoded = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise DaemonUnavailableError("daemon returned invalid JSON") from exc

    if not isinstance(decoded, dict):
        raise DaemonUnavailableError("daemon returned unsupported payload")
    return decoded


def execute_with_fallback(
    daemon_call: Callable[[], Any],
    fallback_call: Callable[[], Any],
) -> dict[str, Any]:
    try:
        return {
            "mode": "daemon",
            "result": daemon_call(),
        }
    except DaemonUnavailableError:
        return {
            "mode": "fallback",
            "result": fallback_call(),
        }
