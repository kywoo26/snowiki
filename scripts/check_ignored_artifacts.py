#!/usr/bin/env python3
"""Block commits that stage ignored internal artifacts via force-add."""

from __future__ import annotations

import subprocess
import sys

ALLOWED_PREFIXES = (
    '.sisyphus/rules/',
)


def _staged_paths() -> list[str]:
    output = subprocess.check_output(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _is_allowed(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _is_ignored_by_policy(path: str) -> bool:
    result = subprocess.run(
        ['git', 'check-ignore', '--no-index', '-q', path],
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    offenders = [
        path
        for path in _staged_paths()
        if _is_ignored_by_policy(path) and not _is_allowed(path)
    ]
    if not offenders:
        return 0

    print('Ignored internal artifacts must not be committed.', file=sys.stderr)
    print('The following staged paths are ignored by repo policy:', file=sys.stderr)
    for path in offenders:
        print(f'  - {path}', file=sys.stderr)
    print(
        'Remove them from the index or whitelist them explicitly in repo policy before committing.',
        file=sys.stderr,
    )
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
