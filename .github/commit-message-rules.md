# Commit Message Rules

```
type(scope): short imperative subject under 72 chars

Body: why this change is needed, what contract or behavior changed.

Refs: #123
BREAKING CHANGE: migration steps here (if any)
```

Types: feat, fix, refactor, docs, test, ci, deps
Scopes: cli, search, storage, skill, test, ci, deps

- `feat` and `fix` require a scope.
- `docs`, `test`, `ci`, `deps`, `refactor` may omit scope.
- Imperative mood, no trailing period, max 72 chars.
- Body required for `feat`, `fix`, `refactor`; explain why.
- Footer: `Refs: #N`, `Fixes: #N`, `BREAKING CHANGE:`.
