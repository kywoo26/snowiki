# Sub-step M: Mecab Feasibility Blocker

## Purpose

Record the blocked-with-artifact closeout for the bounded Mecab reopening lane before any Mecab-specific code was added.

## Blocking question

> Can the canonical Mecab representative `python-mecab-ko` be installed and imported in Snowiki's Python 3.14 `uv` environment without unbounded native bootstrap or system package work?

## Command executed

```bash
uv add python-mecab-ko
```

## Observed result

The bounded install path failed.

Observed failure excerpt:

```text
× Failed to build `python-mecab-ko==1.3.7`
RuntimeError: mecab-config not found
```

The package did not resolve through a prebuilt wheel path for this Python 3.14 environment. Instead it fell back to a native build that requires `mecab-config` and a system Mecab installation path.

## Why this is a blocker

The Mecab reopening plan explicitly froze these constraints:

- no manual native bootstrap script
- no system package installation for Mecab
- no unbounded source-build/toolchain dependency path

Because the representative package immediately crossed into native build requirements, the lane fails the bounded feasibility gate before any tokenizer implementation work can begin.

## Closeout outcome

- **Outcome**: `blocked-with-artifact`
- **Tokenizer implemented**: no
- **Benchmark run**: no
- **Runtime promotion**: no
- **Step 4 unblocked**: no

## Smallest future reopening condition

The Mecab lane may be reopened later only if one of the following becomes true:

1. `python-mecab-ko` provides a bounded Python 3.14-compatible wheel/install path under `uv`, or
2. a different Mecab-family representative is canonically approved and demonstrated to satisfy the same bounded install/import gate without manual native bootstrap.

Until then, the Mecab reopening lane remains closed as blocked-with-artifact.
