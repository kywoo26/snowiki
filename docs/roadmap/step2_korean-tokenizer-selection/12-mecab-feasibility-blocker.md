# Sub-step M: Mecab Representative Feasibility Note

## Purpose

Record the failure of the first Mecab representative attempt and the evidence that led to a corrected bounded representative path.

## Blocking question

> Can the initially chosen Mecab representative `python-mecab-ko` be installed and imported in Snowiki's Python 3.14 `uv` environment without unbounded native bootstrap or system package work?

## Command executed

```bash
uv add python-mecab-ko
```

## Observed result

The first bounded install path failed.

Observed failure excerpt:

```text
× Failed to build `python-mecab-ko==1.3.7`
RuntimeError: mecab-config not found
```

`python-mecab-ko` did not resolve through a prebuilt wheel path for this Python 3.14 environment. Instead it fell back to a native build that requires `mecab-config` and a system Mecab installation path.

## Deeper search result

Further package and runtime search showed that the Mecab **family** is not blocked on Python 3.14.

The corrected bounded representative path is:

- `mecab-python3` for the Python 3.14 wheel-backed MeCab wrapper
- `python-mecab-ko-dic` for packaged Korean dictionary assets (`dicrc`, `sys.dic`, `unk.dic`)

Verified bounded runtime probe:

```bash
uv run --with mecab-python3 --with python-mecab-ko-dic python - <<'PY'
import MeCab
import mecab_ko_dic
args = f'-r {mecab_ko_dic.dictionary_path}/dicrc -d {mecab_ko_dic.dictionary_path}'
tagger = MeCab.Tagger(args)
print(tagger.parse('안녕하세요 Snowiki 입니다 README.md /foo/bar.py'))
PY
```

That probe succeeded and produced Korean morphological output while preserving English/code/path spans in the parse stream.

## What was actually blocked

The original Mecab reopening attempt explicitly froze these constraints:

- no manual native bootstrap script
- no system package installation for Mecab
- no unbounded source-build/toolchain dependency path

Because that first representative package immediately crossed into native build requirements, the first representative attempt failed the bounded feasibility gate.

## Corrected conclusion

- **Blocked thing**: the `python-mecab-ko` representative choice
- **Not blocked**: the Mecab family itself
- **Corrected next move**: reopen the Mecab lane using `mecab-python3` + `python-mecab-ko-dic`

## Active next condition

The active condition is now whether the corrected representative pair can be integrated cleanly into Snowiki's benchmark-only tokenizer path.

If that corrected pair later fails Snowiki-specific integration or benchmark gates, the Mecab lane should then close on those new grounds instead of on the old `python-mecab-ko` packaging failure.

## What happened next

The corrected representative pair was integrated successfully:

- `mecab-python3` installed via Python 3.14 wheel
- `python-mecab-ko-dic` supplied packaged Korean dictionary assets
- `mecab_morphology_v1` became benchmarkable on the blocking `retrieval` preset

However, the lane still failed the retrieval quality gate and therefore closed as a rejected benchmark-only comparison rather than as a packaging blocker.
