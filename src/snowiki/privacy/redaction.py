from __future__ import annotations

import re
from typing import Any

REDACTED_VALUE = "[REDACTED]"

_SENSITIVE_KEY_NAMES = (
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "password",
    "passwd",
    "secret",
    "token",
)

_ASSIGNMENT_PATTERNS = (
    re.compile(
        r'(?P<prefix>(?i:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret)\b\s*[:=]\s*["\']?))(?P<value>[^"\'\s,;]+)',
    ),
    re.compile(
        r'(?P<prefix>(?i:\bauthorization\b\s*[:=]\s*["\']?Bearer\s+))(?P<value>[A-Za-z0-9._-]{8,})',
    ),
)

_INLINE_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|pk|rk)_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{12,}\b"),
)


def _redact_string(value: str) -> str:
    redacted = value
    for pattern in _ASSIGNMENT_PATTERNS:
        redacted = pattern.sub(
            lambda match: f"{match.group('prefix')}{REDACTED_VALUE}", redacted
        )
    for pattern in _INLINE_SECRET_PATTERNS:
        redacted = pattern.sub(REDACTED_VALUE, redacted)
    return redacted


def _is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.strip().lower().replace("-", "_")
    return any(name in normalized for name in _SENSITIVE_KEY_NAMES)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_string(value)

    if isinstance(value, list):
        return [redact_secrets(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)

    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(key):
                if isinstance(item, (dict, list, tuple)):
                    redacted[key] = redact_secrets(item)
                elif item is None:
                    redacted[key] = None
                else:
                    redacted[key] = REDACTED_VALUE
                continue
            redacted[key] = redact_secrets(item)
        return redacted

    return value
