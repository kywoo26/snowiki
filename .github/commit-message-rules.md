# Commit Message Guidelines

Write commit messages so the title alone tells a reviewer what changed and why. Use conventional commit style where it helps clarity.

Recommended forms:
- `feat(scope): short imperative summary`
- `fix(scope): short imperative summary`
- `docs: short imperative summary`
- `test: short imperative summary`
- `refactor: short imperative summary`
- `ci: short imperative summary`

Guidance:
- make the subject specific enough that the change intent is obvious without opening the diff
- prefer strong verbs such as `add`, `fix`, `remove`, `refactor`, `harden`, `simplify`, or `restore`
- keep the subject under ~72 characters when possible
- avoid a trailing period
- use a scope for `feat` and `fix` when it improves clarity
- add a body when the title alone cannot capture the key motivation, constraints, or rollout notes
- use short bullet points in the body when multiple important outcomes need to be called out
- prefer clarity over ritual

Examples:
- `feat(search): add benchmark-only hf wordpiece tokenizer lane`
- `refactor(governance): remove blocking PR governance checks`
- `fix(bench): harden no-answer evaluation slices`

Suggested body structure when needed:
- why this change was necessary
- the main implementation choices
- verification performed or follow-up concerns
