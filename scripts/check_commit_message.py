#!/usr/bin/env python3
"""Validate a commit message against Snowiki governance conventions.

Enforces locally via commit-msg hook:
- Subject format: type(scope): short imperative subject
- Max 72 characters
- No trailing period
- Banned AI/agent co-work markers anywhere in the message

Does NOT hard-enforce commit body structure.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence

VALID_TYPES = {"feat", "fix", "refactor", "docs", "test", "ci", "deps"}
VALID_SCOPES = {"cli", "search", "storage", "skill", "test", "ci", "deps"}
TYPES_REQUIRING_SCOPE = {"feat", "fix"}
MAX_SUBJECT_LENGTH = 72

BANNED_MARKERS = (
    "co-authored-by:",
    "ultraworked with",
    "coworker",
)


class ValidationError(Exception):
    """Raised when commit message validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a commit message against Snowiki conventions.",
    )
    parser.add_argument(
        "message_file",
        help="path to the file containing the commit message",
    )
    return parser.parse_args(argv)


def _read_message(path: str) -> str:
    """Read the commit message from file."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_subject(message: str) -> str:
    """Return the first non-empty line of the message."""
    for line in message.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _validate_subject(subject: str) -> None:
    """Validate the commit message subject line.

    Rules:
    - Must match: type(scope): subject or type: subject
    - Valid types: feat, fix, refactor, docs, test, ci, deps
    - feat and fix require a scope.
    - docs, test, ci, deps, refactor may omit scope.
    - Max 72 characters.
    - No trailing period.
    """
    if not subject:
        raise ValidationError("Commit subject is empty.")

    if len(subject) > MAX_SUBJECT_LENGTH:
        raise ValidationError(
            f"Commit subject exceeds {MAX_SUBJECT_LENGTH} characters "
            f"({len(subject)} chars)."
        )

    if subject.endswith("."):
        raise ValidationError("Commit subject must not end with a period.")

    match = re.match(r"^([a-z]+)(?:\(([a-z-]+)\))?: ?(.*)$", subject)
    if not match:
        raise ValidationError(
            "Commit subject must follow 'type(scope): subject' or 'type: subject'."
        )

    commit_type = match.group(1)
    scope = match.group(2)
    rest = match.group(3)

    if commit_type not in VALID_TYPES:
        raise ValidationError(
            f"Invalid type '{commit_type}'. Valid types: {', '.join(sorted(VALID_TYPES))}."
        )

    if scope is not None and scope not in VALID_SCOPES:
        raise ValidationError(
            f"Invalid scope '{scope}'. Valid scopes: {', '.join(sorted(VALID_SCOPES))}."
        )

    if commit_type in TYPES_REQUIRING_SCOPE and scope is None:
        raise ValidationError(
            f"Type '{commit_type}' requires a scope. "
            f"Valid scopes: {', '.join(sorted(VALID_SCOPES))}."
        )

    if not rest.strip():
        raise ValidationError("Commit subject is empty after type/scope prefix.")


def _validate_banned_markers(message: str) -> None:
    """Reject messages containing banned AI/agent co-work markers."""
    lower_message = message.lower()
    for marker in BANNED_MARKERS:
        if marker in lower_message:
            raise ValidationError(
                f"Commit message contains banned marker: '{marker}'."
            )


def validate(message: str) -> list[str]:
    """Validate a commit message.

    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []

    try:
        _validate_subject(_extract_subject(message))
    except ValidationError as exc:
        errors.append(exc.message)

    try:
        _validate_banned_markers(message)
    except ValidationError as exc:
        errors.append(exc.message)

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    message = _read_message(args.message_file)
    errors = validate(message)

    if errors:
        print("Commit message validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Commit message validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
