#!/usr/bin/env python3
"""Validate PR title and body against Snowiki governance conventions.

This script is designed to run in GitHub Actions or locally.
It validates:
- PR title follows conventional commit format.
- PR body contains required sections from the PR template.
- No placeholder-only required sections.
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


class ValidationError(Exception):
    """Raised when PR governance validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PR title and body against Snowiki governance rules.",
    )
    parser.add_argument("--title", required=True, help="PR title")
    parser.add_argument("--body", required=True, help="PR body")
    return parser.parse_args(argv)


def _extract_subject(title: str) -> str:
    """Return the title stripped of any leading/trailing whitespace."""
    return title.strip()


def _validate_title(title: str) -> None:
    """Validate PR title against conventional commit format.

    Rules:
    - Must match: type(scope): subject or type: subject
    - Valid types: feat, fix, refactor, docs, test, ci, deps
    - feat and fix require a scope.
    - docs, test, ci, deps, refactor may omit scope.
    - Max 72 characters total.
    - No trailing period.
    """
    subject = _extract_subject(title)

    if not subject:
        raise ValidationError("PR title is empty.")

    if len(subject) > MAX_SUBJECT_LENGTH:
        raise ValidationError(
            f"PR title exceeds {MAX_SUBJECT_LENGTH} characters "
            f"({len(subject)} chars)."
        )

    if subject.endswith("."):
        raise ValidationError("PR title must not end with a period.")

    # Pattern: type(scope): subject or type: subject
    match = re.match(r"^([a-z]+)(?:\(([a-z-]+)\))?: ?(.*)$", subject)
    if not match:
        raise ValidationError(
            "PR title must follow 'type(scope): subject' or 'type: subject'."
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
        raise ValidationError("PR title subject is empty after type/scope prefix.")


def _has_checked_item(section_text: str) -> bool:
    """Return True if the section contains at least one checked checkbox."""
    return bool(re.search(r"^- \[x\]", section_text, re.MULTILINE | re.IGNORECASE))


def _is_placeholder_only(section_text: str) -> bool:
    """Return True if section appears to contain only placeholders or boilerplate."""
    if _has_checked_item(section_text):
        return False

    cleaned = re.sub(r"<!--.*?-->", "", section_text, flags=re.DOTALL)
    cleaned = re.sub(r"^\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    if not cleaned:
        return True

    # Common skip phrases indicate the section is intentionally empty
    skip_phrases = (
        "skip for trivial changes",
        "skip if none",
        "skip if no surface change",
    )
    lower = cleaned.lower()
    if any(phrase in lower for phrase in skip_phrases):
        if len(cleaned) < 60:
            return True

    return False


def _extract_section(body: str, heading: str) -> str | None:
    """Extract the text under a markdown heading from the body.

    Returns None if the heading is not found.
    """
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s+|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(body)
    if match:
        return match.group(1)
    return None


def _validate_body(body: str) -> None:
    """Validate PR body against the PR template requirements.

    Required sections:
    - Problem / Motivation
    - Proposed Change
    - Surfaces Touched (at least one checked item)
    - Verification (at least one checked item)
    - Contract Sync (at least one checked item)
    """
    if not body or not body.strip():
        raise ValidationError("PR body is empty.")

    required_sections = [
        "Problem / Motivation",
        "Proposed Change",
        "Surfaces Touched",
        "Verification",
        "Contract Sync",
    ]

    for section_name in required_sections:
        section_text = _extract_section(body, section_name)
        if section_text is None:
            raise ValidationError(
                f"PR body is missing required section: '{section_name}'."
            )

        if _is_placeholder_only(section_text):
            raise ValidationError(
                f"Required section '{section_name}' appears to be empty or placeholder-only."
            )

    # Checkbox sections: require at least one checked item
    checkbox_sections = ["Surfaces Touched", "Verification", "Contract Sync"]
    for section_name in checkbox_sections:
        section_text = _extract_section(body, section_name)
        # section_text is guaranteed non-None here because we checked above
        assert section_text is not None
        if not _has_checked_item(section_text):
            raise ValidationError(
                f"Section '{section_name}' must have at least one checked item."
            )


def validate(title: str, body: str) -> list[str]:
    """Validate PR title and body.

    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []

    try:
        _validate_title(title)
    except ValidationError as exc:
        errors.append(exc.message)

    try:
        _validate_body(body)
    except ValidationError as exc:
        errors.append(exc.message)

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    errors = validate(args.title, args.body)

    if errors:
        print("PR governance validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("PR governance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
