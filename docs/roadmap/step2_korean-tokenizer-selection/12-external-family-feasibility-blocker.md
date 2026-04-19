# Sub-step M: External Family Feasibility Blocker

## Purpose

Record the exact reason the next bounded external-family comparison lane cannot proceed yet.

## Decision question

> Can one external tokenizer family be compared next without violating the current dependency-governance rule?

## Current answer

### 1. No bounded external family lane can proceed yet

The next external-family comparison lane is **blocked-with-artifact**.

This is because every admitted-in-principle external family representative currently requires new runtime dependencies that are not present in the repository dependency closure.

## Evidence

### 2. Current runtime dependency closure

Current runtime dependencies in `pyproject.toml` are limited to:
- `click`
- `pydantic`
- `kiwipiepy`
- `bm25s`
- `numpy`

There is no currently available dependency in the runtime closure for:
- `python-mecab-ko`
- `huggingface/tokenizers`
- `BertWordPieceTokenizer`

### 3. Family-specific conclusion

| Family | Representative | Current dependency state | Feasibility |
| :--- | :--- | :--- | :--- |
| Mecab | `python-mecab-ko` | not present in runtime dependencies | blocked |
| HF / subword | `huggingface/tokenizers` via `BertWordPieceTokenizer` | not present in runtime dependencies | blocked |

## Governance reason

### 4. Dependency additions are still not autonomous

The current productionization program explicitly allows benchmark asset strengthening, but it does **not** allow autonomous dependency additions.

So the external-family lane cannot proceed unless a later explicit approval authorizes the dependency change.

## Minimum approval surface

### 5. What must be approved to reopen this lane

To continue with one external-family comparison lane, the smallest approval surface is:

- permission to add **one** new runtime dependency for **one** admitted-in-principle family representative
- followed by a bounded adapter/registry/benchmark integration PR for that one family only

Examples:
- `python-mecab-ko`
- `huggingface/tokenizers`

## What this does not mean

### 6. The broader lexical productionization program is not invalidated

The benchmark substrate hardening and benchmark asset strengthening work still stand.
The current-roster rerun still stands.
Only the **next external-family implementation lane** is blocked.

## Acceptance criteria

- the note explicitly states that the external-family lane is blocked
- the note names the exact dependency reason
- the note names the smallest approval surface needed to reopen the lane
